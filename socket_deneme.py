import asyncio
import websockets
import json

async def listen_for_updates(task_id):
    uri = f"ws://localhost:8000/ws/scrape/{task_id}"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connection established for task {task_id}.")
        
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print("Task status updated:")
                print(f"Status: {data['status']}")
                print(f"Username: {data['username']}")
                print(f"Progress: {data['progress']}")
                print(f"Percentage: {data['percentage']}")
                print("-------------------------")
                
                if data['status'] == 'Completed' or data['status'] == 'Failed':
                    print("Task completed or failed. Closing connection.")
                    break
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed.")

async def main():
    task_id = input("Please enter the task ID you want to track: ")
    await listen_for_updates(task_id)

if __name__ == "__main__":
    asyncio.run(main())