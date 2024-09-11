# Twitter Scraper API Kullanım Kılavuzu

## Genel Bakış

Bu API, Twitter kullanıcılarının tweetlerini kazımak ve yönetmek için tasarlanmıştır. Belirli bir kullanıcının tweetlerini kazıyabilir, kazıma işleminin ilerlemesini gerçek zamanlı olarak takip edebilir ve kazınmış tweetleri alabilirsiniz.

## Endpoint'ler

### 1. Tweet Kazıma İşlemini Başlatma

POST /scrape

**Parametreler:**
- `username`: Kazınacak Twitter kullanıcı adı
- `tweet_count`: Kazınacak tweet sayısı

**Yanıt:**
- Bir task ID döndürür

### 2. Kazıma İlerlemesini İzleme

WebSocket /ws/scrape/{task_id}

**Parametreler:**
- `task_id`: İzlenecek kazıma görevinin kimliği

**Yanıt:**
- Gerçek zamanlı ilerleme güncellemeleri

### 3. Belirli Bir Kullanıcının Tweetlerini Alma

GET /tweets/{username}

**Parametreler:**
- `username`: Tweetleri getirilecek kullanıcı adı

**Yanıt:**
- Kullanıcının tüm kazınmış tweetlerini içeren bir liste

### 4. Tüm Kazınmış Tweetleri Alma

GET /all_tweets

**Yanıt:**
- Tüm kullanıcıların kazınmış tweetlerini içeren bir sözlük

## Kullanım Örneği

1. Önce bir kazıma işlemi başlatın:
   ```
   POST /scrape
   {
     "username": "elonmusk",
     "tweet_count": 100
   }
   ```

2. Dönen task ID ile WebSocket bağlantısı kurun ve ilerlemeyi izleyin:
   ```
   WebSocket /ws/scrape/{task_id}
   ```

3. Kazıma tamamlandıktan sonra, tweetleri alın:
   ```
   GET /tweets/elonmusk
   ```

4. Tüm kazınmış tweetleri görmek için:
   ```
   GET /all_tweets
   ```
