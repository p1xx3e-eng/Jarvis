import asyncio
import datetime
from telegram import Bot

TELEGRAM_TOKEN = "8594449700:AAG1ZMcqgbE8ZOG9WOM3JT9KrIToJAAAHnI"
YOUR_CHAT_ID = "1019675122"  # Замените на ваш chat_id

bot = Bot(token=TELEGRAM_TOKEN)

async def check_notifications():
    while True:
        now = datetime.datetime.now()
        
        # Каждый день в 21:00 — отчёты менти
        if now.hour == 19 and now.minute == 0:
            await bot.send_message(
                chat_id=YOUR_CHAT_ID,
                text="⚡ Сэр, время отчётов от менти.\n\nМатвей, Никита, Игорь, Артём З. — все сдали?"
            )
        
        # Напоминание про билет — 12 мая (за 3 дня до 15го)
        if now.day == 12 and now.month == 5 and now.hour == 10 and now.minute == 0:
            await bot.send_message(
                chat_id=YOUR_CHAT_ID,
                text="🛫 Сэр, через 3 дня — 15 мая. Билет в Тбилиси куплен?"
            )
        
        # Проверяем каждую минуту
        await asyncio.sleep(60)

async def main():
    print("Планировщик запущен...")
    await check_notifications()

if __name__ == "__main__":
    asyncio.run(main())