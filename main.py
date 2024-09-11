from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from twitter_scraper import Twitter_Scraper
from pydantic import BaseModel, Field
from pymongo import MongoClient
from bson import json_util
import json
import asyncio
import uuid

app = FastAPI(
    title="Twitter Scraper API",
    description="Twitter kullanıcılarının tweetlerini kazıma ve yönetme API'si",
    version="1.0.0"
)
MONGO_URI = "mongodb://root:p2f9FXGxhdmPtEp8rmOv6ykKm0v8i1FNTmBWUqcDk9O0BiDsAzlDdQCLYQKuFc4R@95.217.39.116:5424/?directConnection=true"

# In-memory storage for scraping tasks
scraping_tasks = {}
websocket_connections = {}

class ScrapeRequest(BaseModel):
    username: str = Field(..., description="Scrape edilecek kullanıcının username'i")
    tweet_count: int = Field(..., gt=0, description="Scrape edilecek tweet sayısı")

async def update_progress(task_id: str, scraped_tweets: int, total_tweets: int):
    scraping_tasks[task_id]['scraped_tweets'] = scraped_tweets
    scraping_tasks[task_id]['total_tweets'] = total_tweets
    await notify_clients(task_id)

async def notify_clients(task_id: str):
    if task_id in websocket_connections:
        task = scraping_tasks[task_id]
        message = {
            "status": task['status'],
            "username": task['username'],
            "progress": f"{task['scraped_tweets']}/{task['total_tweets']} tweets scraped",
            "percentage": f"{(task['scraped_tweets'] / task['total_tweets']) * 100:.2f}%"
        }
        for websocket in websocket_connections[task_id]:
            await websocket.send_json(message)

async def scrape_task(task_id: str, username: str, tweet_count: int):
    scraper = Twitter_Scraper()
    scraping_tasks[task_id]['status'] = 'In Progress'
    
    async def progress_callback(scraped, total):
        await update_progress(task_id, scraped, total)
        await asyncio.sleep(0)
    
    try:
        await scraper.scrape_tweets(
            tweet_count=tweet_count,
            scrape_username=username,
            progress_callback=progress_callback
        )
        
        await asyncio.to_thread(scraper.save_to_db)
        
        scraping_tasks[task_id]['status'] = 'Completed'
    except Exception as e:
        scraping_tasks[task_id]['status'] = 'Failed'
        scraping_tasks[task_id]['error'] = str(e)
    finally:
        await notify_clients(task_id)

@app.post("/scrape", tags=["Scraping"])
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Belirtilen kullanıcı için tweet kazıma işlemini başlatır.
    
    - **username**: Kazınacak Twitter kullanıcı adı
    - **tweet_count**: Kazınacak tweet sayısı
    
    Yanıt olarak bir task id döndürür.
    """


    task_id = str(uuid.uuid4())
    scraping_tasks[task_id] = {
        'status': 'Initiated',
        'username': request.username,
        'total_tweets': request.tweet_count,
        'scraped_tweets': 0
    }
    
    asyncio.create_task(scrape_task(task_id, request.username, request.tweet_count))
    
    return {"message": "Scraping task initiated", "task_id": task_id}

@app.websocket("/ws/scrape/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    Belirli bir kazıma görevi için WebSocket bağlantısı kurar.
    
    - **task_id**: İzlenecek kazıma görevinin kimliği
    
    Gerçek zamanlı ilerleme güncellemeleri sağlar.
    """


    await websocket.accept()
    if task_id not in websocket_connections:
        websocket_connections[task_id] = set()
    websocket_connections[task_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()  
    except WebSocketDisconnect:
        websocket_connections[task_id].remove(websocket)
        if not websocket_connections[task_id]:
            del websocket_connections[task_id]


@app.get("/tweets/{username}", tags=["Tweets"])
async def get_tweets(username: str):
    """
    Belirli bir kullanıcının kazınmış tweetlerini getirir.
    
    - **username**: Tweetleri getirilecek kullanıcı adı
    
    Kullanıcının tüm kazınmış tweetlerini içeren bir liste döndürür.
    """


    try:
        client = MongoClient(MONGO_URI)
        db = client["Tweets"]
        collection = db[username]
        
        tweets = list(collection.find())
        tweets_json = json.loads(json_util.dumps(tweets))
        
        return {"tweets": tweets_json}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tweets: {str(e)}")
    finally:
        client.close()

@app.get("/all_tweets", tags=["Tweets"])
async def get_all_tweets():
    """
    Tüm kazınmış tweetleri getirir.
    
    Tüm kullanıcıların kazınmış tweetlerini içeren bir sözlük döndürür.
    Her kullanıcı adı bir anahtar olarak kullanılır ve değeri tweet listesidir.
    """


    try:
        client = MongoClient(MONGO_URI)
        db = client["Tweets"]
        
        all_tweets = {}
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            tweets = list(collection.find())
            all_tweets[collection_name] = json.loads(json_util.dumps(tweets))
        
        return {"all_tweets": all_tweets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tüm tweetleri alırken hata oluştu: {str(e)}")
    finally:
        client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)