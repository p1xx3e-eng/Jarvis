import httpx
import os
import base64
import io
from supabase import create_client
from telegram import Update
from telegram.ext import ContextTypes
from groq import Groq
from google import genai
from google.genai import types
from dashboard import add_client, add_idea, add_win, add_income, add_expense

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OWM_KEY = os.environ.get("OWM_KEY")
GROQ_KEY = os.environ.get("GROQ_KEY")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
YOUR_ID = 1019675122

groq_client = Groq(api_key=GROQ_KEY)
gemini = genai.Client(api_key=GEMINI_KEY)
db = create_client(SUPABASE_URL, SUPABASE_KEY)

MODEL = "gemini-2.5-flash"

def load_history():
    result = db.table("memory").select("role, content").order("created_at", desc=True).limit(10).execute()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(result.data)]

def save_message(role, content):
    db.table("memory").insert({"role": role, "content": content}).execute()

def get_weather():
    try:
        current = httpx.get(
            f"https://api.openweathermap.org/data/2.5/weather?q=Krasnoyarsk,RU&appid={OWM_KEY}&units=metric&lang=ru",
            timeout=10
        ).json()
        forecast = httpx.get(
            f"https://api.openweathermap.org/data/2.5/forecast?q=Krasnoyarsk,RU&appid={OWM_KEY}&units=metric&lang=ru&cnt=16",
            timeout=10
        ).json()
        temp_now = round(current["main"]["temp"])
        feels_now = round(current["main"]["feels_like"])
        desc_now = current["weather"][0]["description"]
        humidity = current["main"]["humidity"]
        wind = round(current["wind"]["speed"])
        tomorrow_data = forecast["list"][8]
        temp_tom = round(tomorrow_data["main"]["temp"])
        feels_tom = round(tomorrow_data["main"]["feels_like"])
        desc_tom = tomorrow_data["weather"][0]["description"]
        forecast_str = ""
        for item in forecast["list"][:8]:
            t = round(item["main"]["temp"])
            d = item["weather"][0]["description"]
            time_str = item["dt_txt"][11:16]
            forecast_str += f"\n{time_str}: {t}°C, {d}"
        return (
            f"\n\nПогода в Красноярске:"
            f"\nСейчас: {temp_now}°C, ощущается {feels_now}°C, {desc_now}, влажность {humidity}%, ветер {wind} м/с"
            f"\nПрогноз на сегодня по часам:{forecast_str}"
            f"\nЗавтра: {temp_tom}°C, ощущается {feels_tom}°C, {desc_tom}"
        )
    except Exception as e:
        print(f"Ошибка погоды: {e}")
        return ""

def parse_command(text):
    t = text.strip().lower()
    if t.startswith("/клиент ") or t.startswith("/client "):
        return ("client", text.split(" ", 1)[1].strip())
    if t.startswith("/идея ") or t.startswith("/idea "):
        return ("idea", text.split(" ", 1)[1].strip())
    if t.startswith("/победа ") or t.startswith("/win "):
        return ("win", text.split(" ", 1)[1].strip())
    if t.startswith("/доход "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            return ("income", {"label": parts[1], "amount": parts[2]})
    if t.startswith("/расход "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            return ("expense", {"label": parts[1], "amount": parts[2]})
    return None

def gemini_chat(history, system, use_search=True):
    """Чат через Gemini с веб-поиском"""
    # Конвертируем историю в формат Gemini
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=2048,
        tools=[types.Tool(google_search=types.GoogleSearch())] if use_search else None,
    )
    response = gemini.models.generate_content(model=MODEL, contents=contents, config=config)
    return response.text

def gemini_simple(prompt, system="", use_search=False):
    config = types.GenerateContentConfig(
        system_instruction=system if system else None,
        max_output_tokens=512,
        tools=[types.Tool(google_search=types.GoogleSearch())] if use_search else None,
    )
    response = gemini.models.generate_content(model=MODEL, contents=prompt, config=config)
    return response.text

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from prompts import get_context
    if update.effective_user.id != YOUR_ID:
        await update.message.reply_text("Ты не Егор Александрович, забудь сюда дорогу, бродяга")
        return

    user_input = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    cmd = parse_command(user_input)
    if cmd:
        action, data = cmd
        if action == "client":
            add_client(name=data)
            await update.message.reply_text(f"Клиент {data} добавлен в CRM, сэр")
        elif action == "idea":
            add_idea(data)
            await update.message.reply_text("Идея сохранена, сэр")
        elif action == "win":
            add_win(data)
            await update.message.reply_text("Победа записана, сэр 🔥")
        elif action == "income":
            try:
                add_income(data["label"], float(data["amount"]))
                await update.message.reply_text(f"Доход {data['amount']} ₽ — {data['label']} записан, сэр")
            except:
                await update.message.reply_text("Формат: /доход Название Сумма")
        elif action == "expense":
            try:
                add_expense(data["label"], float(data["amount"]))
                await update.message.reply_text(f"Расход {data['amount']} ₽ — {data['label']} записан, сэр")
            except:
                await update.message.reply_text("Формат: /расход Название Сумма")
        return

    history = load_history()
    weather_ctx = get_weather() if "погода" in user_input.lower() or "прогноз" in user_input.lower() else ""

    full_input = user_input + weather_ctx
    save_message("user", user_input)
    history.append({"role": "user", "content": full_input})

    try:
        answer = gemini_chat(history, get_context(), use_search=True)
        if not answer or not answer.strip():
            raise ValueError("Gemini вернул пусто")
    except Exception as e:
        print(f"Gemini ошибка: {e}, фоллбэк на Groq")
        # Фоллбэк на Groq если Gemini не отвечает
        msgs = [{"role": "system", "content": get_context()}] + history
        answer = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=msgs, max_tokens=1024).choices[0].message.content

    if not answer or not answer.strip():
        answer = "Что-то пошло не так с ответом, сэр. Повторите вопрос"

    # Сохраняем факт
    try:
        fact = gemini_simple(
            f"Извлеки важный факт о Егоре ТОЛЬКО если это сделка, деньги, решение по бизнесу, изменение планов, новый клиент. НЕ сохраняй бытовое. Если нет — ответь НЕТ. Если есть — одно предложение.\n\nЕгор: {user_input}\nДжарвис: {answer}"
        )
        if fact.strip() != "НЕТ" and len(fact.strip()) > 5:
            db.table("facts").insert({"fact": fact.strip()}).execute()
    except:
        pass

    save_message("assistant", answer)
    await update.message.reply_text(answer)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from prompts import get_context
    if update.effective_user.id != YOUR_ID:
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_data = bytes(await file.download_as_bytearray())
    caption = update.message.caption or "Что на этом фото? Опиши подробно."

    try:
        response = gemini.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                caption,
            ],
            config=types.GenerateContentConfig(system_instruction=get_context(), max_output_tokens=1024),
        )
        answer = response.text
    except Exception as e:
        print(f"Gemini vision ошибка: {e}")
        answer = "Не могу разобрать фото, сэр. Попробуйте ещё раз"

    save_message("assistant", answer)
    await update.message.reply_text(answer)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from prompts import get_context
    if update.effective_user.id != YOUR_ID:
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    voice_bytes = bytes(await file.download_as_bytearray())
    # Whisper через Groq (бесплатно и быстро)
    audio_file = io.BytesIO(voice_bytes)
    audio_file.name = "voice.ogg"
    transcript = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ru")
    user_input = transcript.text

    history = load_history()
    save_message("user", user_input)
    history.append({"role": "user", "content": user_input})

    try:
        answer = gemini_chat(history, get_context(), use_search=True)
        if not answer or not answer.strip():
            raise ValueError("пусто")
    except Exception as e:
        print(f"Gemini ошибка: {e}")
        msgs = [{"role": "system", "content": get_context()}] + history
        answer = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=msgs, max_tokens=512).choices[0].message.content

    if not answer or not answer.strip():
        answer = "Не расслышал толком, сэр. Повторите"

    save_message("assistant", answer)
    await update.message.reply_text(answer)
