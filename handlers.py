import anthropic
import httpx
import os
import base64
import io
from supabase import create_client
from telegram import Update
from telegram.ext import ContextTypes
from groq import Groq
from jarvis.dashboard import add_client, add_idea, add_win, add_income, add_expense

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OWM_KEY = os.environ.get("OWM_KEY")
GROQ_KEY = os.environ.get("GROQ_KEY")
YOUR_ID = 1019675122

ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
db = create_client(SUPABASE_URL, SUPABASE_KEY)

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

async def get_search_context(user_input):
    try:
        search_response = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system="Найди актуальную информацию и дай подробный ответ на русском языке. Включи конкретные факты, даты, цифры, названия на русском.",
            messages=[{"role": "user", "content": user_input}]
        )
        result = ""
        for block in search_response.content:
            if hasattr(block, "text") and block.text:
                result += block.text
        return f"\n\nАктуальная информация из интернета:\n{result}" if result else ""
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return ""

def parse_command(text):
    """Парсит команды для дашборда"""
    t = text.strip().lower()

    if t.startswith("/клиент ") or t.startswith("/client "):
        name = text.split(" ", 1)[1].strip()
        return ("client", name)
    if t.startswith("/идея ") or t.startswith("/idea "):
        idea = text.split(" ", 1)[1].strip()
        return ("idea", idea)
    if t.startswith("/победа ") or t.startswith("/win "):
        win = text.split(" ", 1)[1].strip()
        return ("win", win)
    if t.startswith("/доход "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            return ("income", {"label": parts[1], "amount": parts[2]})
    if t.startswith("/расход "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            return ("expense", {"label": parts[1], "amount": parts[2]})
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from jarvis.prompts import get_context
    if update.effective_user.id != YOUR_ID:
        await update.message.reply_text("Ты не Егор Александрович, забудь сюда дорогу, бродяга")
        return

    user_input = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Проверяем команды дашборда
    cmd = parse_command(user_input)
    if cmd:
        action, data = cmd
        if action == "client":
            add_client(name=data)
            await update.message.reply_text(f"Клиент {data} добавлен в CRM, сэр")
            return
        elif action == "idea":
            add_idea(data)
            await update.message.reply_text(f"Идея сохранена, сэр")
            return
        elif action == "win":
            add_win(data)
            await update.message.reply_text(f"Победа записана, сэр 🔥")
            return
        elif action == "income":
            try:
                add_income(data["label"], float(data["amount"]))
                await update.message.reply_text(f"Доход {data['amount']} ₽ — {data['label']} записан, сэр")
            except:
                await update.message.reply_text("Формат: /доход Название Сумма")
            return
        elif action == "expense":
            try:
                add_expense(data["label"], float(data["amount"]))
                await update.message.reply_text(f"Расход {data['amount']} ₽ — {data['label']} записан, сэр")
            except:
                await update.message.reply_text("Формат: /расход Название Сумма")
            return

    history = load_history()
    search_context = ""

    if "погода" in user_input.lower() or "прогноз" in user_input.lower():
        search_context = get_weather()
    else:
        search_context = await get_search_context(user_input)

    full_input = user_input + search_context
    save_message("user", user_input)
    history.append({"role": "user", "content": full_input})

    needs_heavy = any(w in user_input.lower() for w in ["напиши пост", "пост", "сценарий", "анализ", "стратегия", "помоги придумать"])
    model = "claude-sonnet-4-6" if needs_heavy else "claude-haiku-4-5-20251001"

    response = ai.messages.create(
        model=model,
        max_tokens=1024,
        system=get_context(),
        messages=history
    )

    answer = response.content[0].text

    fact_response = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": f"Извлеки важный факт о Егоре ТОЛЬКО если это сделка, деньги, решение по бизнесу, изменение планов, новый клиент. НЕ сохраняй бытовое. Если нет — ответь НЕТ. Если есть — одно предложение.\n\nЕгор: {user_input}\nДжарвис: {answer}"}]
    )

    fact = fact_response.content[0].text.strip()
    if fact != "НЕТ" and len(fact) > 5:
        db.table("facts").insert({"fact": fact}).execute()

    save_message("assistant", answer)
    await update.message.reply_text(answer)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from jarvis.prompts import get_context
    if update.effective_user.id != YOUR_ID:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_data = bytes(await file.download_as_bytearray())
    image_base64 = base64.b64encode(image_data).decode("utf-8")
    caption = update.message.caption or "Что на этом фото? Опиши подробно."

    response = ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=get_context(),
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}},
            {"type": "text", "text": caption}
        ]}]
    )

    answer = response.content[0].text
    save_message("assistant", answer)
    await update.message.reply_text(answer)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from jarvis.prompts import get_context
    if update.effective_user.id != YOUR_ID:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    voice_bytes = bytes(await file.download_as_bytearray())

    groq_client = Groq(api_key=GROQ_KEY)
    audio_file = io.BytesIO(voice_bytes)
    audio_file.name = "voice.ogg"
    transcript = groq_client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-large-v3",
        language="ru"
    )
    user_input = transcript.text

    history = load_history()
    save_message("user", user_input)
    history.append({"role": "user", "content": user_input})

    response = ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=get_context(),
        messages=history
    )

    answer = response.content[0].text
    save_message("assistant", answer)
    await update.message.reply_text(answer)
