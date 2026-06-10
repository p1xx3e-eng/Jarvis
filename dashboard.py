import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
db = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_morning_briefing():
    try:
        projects = db.table("projects").select("name, next_action").eq("status", "active").execute()
        clients = db.table("clients").select("name, status, next_action").neq("status", "done").execute()
        
        import datetime
        month = datetime.datetime.now().strftime("%Y-%m")
        tracker = db.table("tracker").select("type, amount").like("date", f"{month}%").execute()
        income = sum(e["amount"] for e in tracker.data if e["type"] == "income")
        expense = sum(e["amount"] for e in tracker.data if e["type"] == "expense")

        result = []

        if projects.data:
            result.append("АКТИВНЫЕ ПРОЕКТЫ:")
            for p in projects.data:
                line = f"- {p['name']}"
                if p.get("next_action"):
                    line += f" → {p['next_action']}"
                result.append(line)

        if clients.data:
            result.append("\nАКТИВНЫЕ КЛИЕНТЫ:")
            for c in clients.data:
                line = f"- {c['name']} ({c['status']})"
                if c.get("next_action"):
                    line += f" → {c['next_action']}"
                result.append(line)

        result.append(f"\nФИНАНСЫ МЕСЯЦА:")
        result.append(f"- Доход: {income:,.0f} ₽")
        result.append(f"- Расход: {expense:,.0f} ₽")
        result.append(f"- Баланс: {income - expense:,.0f} ₽")

        return "\n".join(result)
    except Exception as e:
        print(f"Ошибка dashboard: {e}")
        return ""

def save_to_dashboard(table, data):
    try:
        db.table(table).insert(data).execute()
        return True
    except Exception as e:
        print(f"Ошибка записи в {table}: {e}")
        return False

def add_client(name, service=None, next_action=None, notes=None):
    return save_to_dashboard("clients", {
        "name": name,
        "service": service,
        "status": "lead",
        "next_action": next_action,
        "notes": notes
    })

def add_idea(text):
    return save_to_dashboard("ideas", {"text": text})

def add_win(text):
    return save_to_dashboard("wins", {"text": text})

def add_income(label, amount):
    import datetime
    return save_to_dashboard("tracker", {
        "type": "income",
        "label": label,
        "amount": amount,
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    })

def add_expense(label, amount):
    import datetime
    return save_to_dashboard("tracker", {
        "type": "expense",
        "label": label,
        "amount": amount,
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    })
