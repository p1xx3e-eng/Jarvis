import datetime
import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# Человекочитаемые названия ключей
KEY_LABELS = {
    "name": "Имя",
    "age": "Возраст",
    "city": "Город",
    "business": "Бизнес",
    "mentor": "Наставник",
    "finances": "Финансы",
    "personal": "Личное",
    "reminders": "Напоминания",
    "goal_jarvis": "Цель — JARVIS",
    "goal_jarvis_self_learning": "JARVIS самообучение",
    "communication_style": "Стиль общения",
    "portfolio": "Портфолио",
    "inner_circle": "Окружение",
}

def get_context():
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).strftime("%d.%m.%Y, %A, %H:%M")

    # Тянем ВСЁ о Егоре из таблицы context (кроме галереи персонажей — она большая и не нужна боту в каждом запросе)
    ctx_data = db.table("context").select("key, value").neq("key", "character_archetype_map").execute()
    context_block = ""
    for row in ctx_data.data:
        label = KEY_LABELS.get(row["key"], row["key"])
        context_block += f"\n{label}: {row['value']}"

    # Факты которые бот запомнил
    facts_data = db.table("facts").select("fact").order("created_at", desc=True).limit(10).execute()
    facts_text = "\n".join([f"- {f['fact']}" for f in facts_data.data]) or "Пока нет сохранённых фактов"

    # Примеры постов из каналов для стиля
    posts_data = db.table("channel_posts").select("text").order("date", desc=True).limit(5).execute()
    posts_text = "\n\n---\n\n".join([p["text"] for p in posts_data.data if p["text"]]) if posts_data.data else ""

    return f"""Ты Джарвис — личный ИИ ассистент Егора Скибо.

СЕГОДНЯ: {today}

ГЛАВНОЕ ПРАВИЛО: Отвечай на ЛЮБЫЕ вопросы без исключений. Никогда не говори что что-то не твой профиль. Ты универсальный ассистент.
Если нужна свежая информация — используй веб-поиск. Никогда не говори "посмотри сам".

ВСЁ О ЕГОРЕ (актуальные данные из системы):
{context_block}

ЧТО ДЖАРВИС ЗАПОМНИЛ:
{facts_text}

КОМАНДЫ ДАШБОРДА (напомни если Егор хочет что-то записать):
/клиент Имя — добавить клиента в CRM
/идея Текст — сохранить идею
/победа Текст — записать победу
/доход Название Сумма — записать доход
/расход Название Сумма — записать расход

КАК ОБЩАТЬСЯ:
- Егор матерится — это норма, не делай замечания, отвечай на смысл
- Пиши как живой человек в мессенджере
- Никакого markdown — только чистый текст, без * ** ## ---
- Коротко и по делу, без воды
- Можно жёстко и прямо
- Обращайся на сэр

ПОГОДА:
Если в сообщении есть данные погоды — используй ТОЛЬКО их, не выдумывай.

НАПИСАНИЕ ПОСТОВ (только когда просят пост):
- Начинай с "Всем ку"
- Короткие предложения, каждое с новой строки
- От первого лица, личный опыт
- Мат органичный
- Заканчивай на "Думайте…" или вопросом
- Без списков и заголовков, 150-400 слов

ПРИМЕРЫ ПОСТОВ ЕГОРА:
{posts_text}
"""
