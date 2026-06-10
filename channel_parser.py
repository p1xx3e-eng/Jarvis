import asyncio
from telegram import Bot
from supabase import create_client

TELEGRAM_TOKEN = "8594449700:AAG1ZMcqgbE8ZOG9WOM3JT9KrIToJAAAHnI"
CHANNEL = "@skibo_titan"
SUPABASE_URL = "https://zfrftlcmkjhweoabvaok.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmcmZ0bGNta2pod2VvYWJ2YW9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc3OTAwMzQsImV4cCI6MjA5MzM2NjAzNH0.YmPlwONp8qfvIHymaHtQ8rNFtmpAWy3ob6qiRykBmYw"

db = create_client(SUPABASE_URL, SUPABASE_KEY)

async def parse_channel():
    print("Читаю канал...")
    
    async with Bot(token=TELEGRAM_TOKEN) as bot:
        posts = []
        
        # Получаем историю канала
        updates = await bot.get_updates(limit=100)
        
        for update in updates:
            if update.channel_post and update.channel_post.text:
                posts.append({
                    "text": update.channel_post.text,
                    "date": str(update.channel_post.date)
                })
        
        if posts:
            db.table("channel_posts").insert(posts).execute()
            print(f"Сохранено {len(posts)} постов")
        else:
            print("Постов не найдено")

asyncio.run(parse_channel())