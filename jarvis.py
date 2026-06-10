import asyncio
import datetime
import httpx
import os
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters
from handlers import handle_message, handle_photo, handle_voice

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
OWM_KEY = os.environ.get("OWM_KEY")
YOUR_ID = 1019675122

import anthropic
ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

async def send_notifications():
    while True:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
        if now.hour == 9 and now.minute == 0:
            try:
                current = httpx.get(
                    f"https://api.openweathermap.org/data/2.5/weather?q=Krasnoyarsk,RU&appid={OWM_KEY}&units=metric&lang=ru",
                    timeout=10
                ).json()
                temp = round(current["main"]["temp"])
                feels = round(current["main"]["feels_like"])
                desc = current["weather"][0]["description"]

                from jarvis.dashboard import get_morning_briefing
                dashboard_data = get_morning_briefing()

                briefing = ai.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=400,
                    messages=[{"role": "user", "content": f"Напиши короткий утренний брифинг для Егора. Обращайся на сэр. Без markdown.\n\nПогода: {temp}°C, ощущается {feels}°C, {desc}. Рекомендация по одежде.\n\nДанные из системы:\n{dashboard_data}\n\nУпомяни активные проекты и следующие шаги. Коротко и по делу."}]
                )
                async with Bot(token=TELEGRAM_TOKEN) as bot:
                    await bot.send_message(chat_id=YOUR_ID, text=briefing.content[0].text)
            except Exception as e:
                print(f"Ошибка брифинга: {e}")
        await asyncio.sleep(60)

async def main():
    print("Джарвис запущен в Telegram...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    webhook_url = "https://jarvis-production-bea9.up.railway.app/webhook"
    async with app:
        await app.bot.set_webhook(url=webhook_url)
        await app.start()
        asyncio.create_task(send_notifications())

        from aiohttp import web
        async def handle_webhook(request):
            data = await request.json()
            update = Update.de_json(data, app.bot)
            await app.process_update(update)
            return web.Response(text="OK")

        server = web.Application()
        server.router.add_post("/webhook", handle_webhook)
        runner = web.AppRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("Webhook запущен на порту 8080")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
