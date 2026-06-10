import json
from supabase import create_client

SUPABASE_URL = "https://zfrftlcmkjhweoabvaok.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpmcmZ0bGNta2pod2VvYWJ2YW9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc3OTAwMzQsImV4cCI6MjA5MzM2NjAzNH0.YmPlwONp8qfvIHymaHtQ8rNFtmpAWy3ob6qiRykBmYw"

db = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_text(text_field):
    """Извлекаем чистый текст из поста"""
    if isinstance(text_field, str):
        return text_field
    elif isinstance(text_field, list):
        result = ""
        for part in text_field:
            if isinstance(part, str):
                result += part
            elif isinstance(part, dict) and "text" in part:
                result += part["text"]
        return result
    return ""

# Читаем JSON
with open("result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

posts = []
for msg in data["messages"]:
    if msg.get("type") == "message":
        text = extract_text(msg.get("text", ""))
        if text and len(text) > 50:  # только нормальные посты
            posts.append({
                "text": text,
                "date": msg.get("date", "")
            })

# Загружаем в Supabase
if posts:
    db.table("channel_posts").insert(posts).execute()
    print(f"Загружено {len(posts)} постов в базу")
else:
    print("Постов не найдено")