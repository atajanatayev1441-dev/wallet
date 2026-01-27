import time
import json
from telegram_api import get_updates, send_message, answer_callback_query

TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"  # Поставьте свой токен
ADMIN_ID = 123456789  # Замените на свой Telegram ID администратора

# Файлы для хранения данных
USERS_FILE = "users.json"
DATA_FILE = "data.json"

# Состояния пользователей — что они сейчас делают
user_states = {}

# Загружаем/сохраняем данные
def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Хранилище пользователей и данных
users = load_json(USERS_FILE)
data = load_json(DATA_FILE)

# --- Клавиатуры ---
def main_keyboard(chat_id):
    kb = [
        [{"text": "➕ Добавить доход", "callback_data": "add_income"}],
        [{"text": "➖ Добавить расход", "callback_data": "add_expense"}],
        [{"text": "📊 Отчёты и анализ", "callback_data": "reports"}],
        [{"text": "✉️ Связь с админом", "callback_data": "contact_admin"}],
    ]
    if chat_id == ADMIN_ID:
        kb.append([{"text": "👥 Пользователи", "callback_data": "users_list"}])
    return {"inline_keyboard": kb}

def cancel_keyboard():
    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "cancel"}]]}

def back_to_menu_keyboard():
    return {"inline_keyboard": [[{"text": "⬅️ Вернуться в меню", "callback_data": "back_to_menu"}]]}

def category_keyboard(categories):
    kb = [[{"text": c, "callback_data": f"cat_{c}"}] for c in categories]
    kb.append([{"text": "➕ Добавить категорию", "callback_data": "add_category"}])
    kb.append([{"text": "❌ Отмена", "callback_data": "cancel"}])
    return {"inline_keyboard": kb}

# --- Логика работы с категориями ---
def get_categories(cat_type, chat_id):
    key = f"{chat_id}_{cat_type}"
    return data.get("categories", {}).get(key, ["Общее"])

def add_category(cat_type, chat_id, category):
    if "categories" not in data:
        data["categories"] = {}
    key = f"{chat_id}_{cat_type}"
    if key not in data["categories"]:
        data["categories"][key] = []
    if category not in data["categories"][key]:
        data["categories"][key].append(category)
        save_json(DATA_FILE, data)

# --- Добавление доходов и расходов ---
def add_record(chat_id, rec_type, amount, category, comment=""):
    if "records" not in data:
        data["records"] = {}
    if str(chat_id) not in data["records"]:
        data["records"][str(chat_id)] = []
    data["records"][str(chat_id)].append({
        "type": rec_type,  # income или expense
        "amount": amount,
        "category": category,
        "comment": comment,
        "timestamp": int(time.time())
    })
    save_json(DATA_FILE, data)

# --- Отчеты ---
import datetime

def format_date(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

def get_report(chat_id, period="all", rec_type=None):
    recs = data.get("records", {}).get(str(chat_id), [])
    now = int(time.time())
    start_ts = 0
    if period == "day":
        start_ts = now - 86400
    elif period == "week":
        start_ts = now - 7*86400
    elif period == "month":
        start_ts = now - 30*86400

    filtered = [r for r in recs if r["timestamp"] >= start_ts]
    if rec_type:
        filtered = [r for r in filtered if r["type"] == rec_type]

    if not filtered:
        return "Нет данных за этот период."

    # Группировка по категориям
    sums = {}
    total = 0
    for r in filtered:
        cat = r["category"]
        sums[cat] = sums.get(cat, 0) + float(r["amount"])
        total += float(r["amount"])

    lines = [f"<b>Отчёт за {period}:</b>"]
    for cat, amount in sums.items():
        lines.append(f"{cat}: {amount:.2f}")
    lines.append(f"\n<b>Итого:</b> {total:.2f}")

    return "\n".join(lines)

# --- Отправка сообщения админу ---
def send_to_admin(text):
    send_message(TOKEN, ADMIN_ID, text)

# --- Обработка обновлений ---
def handle_message(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Регистрация пользователя
    if str(chat_id) not in users:
        users[str(chat_id)] = {
            "id": chat_id,
            "username": message["from"].get("username", ""),
            "first_name": message["from"].get("first_name", ""),
        }
        save_json(USERS_FILE, users)

    state = user_states.get(str(chat_id), {})

    # Обработка состояний
    if state.get("action") == "adding_income_amount":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление дохода отменено.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        try:
            amount = float(text)
            user_states[str(chat_id)] = {"action": "adding_income_category", "amount": amount}
            cats = get_categories("income", chat_id)
            send_message(TOKEN, chat_id, "Выберите категорию дохода:", reply_markup=category_keyboard(cats))
        except:
            send_message(TOKEN, chat_id, "Введите корректное число или нажмите ❌ Отмена.")
        return

    if state.get("action") == "adding_income_category":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление дохода отменено.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        # Тут категоря приходит через callback, не через текст, но на всякий случай
        # Временно заглушка
        return

    if state.get("action") == "adding_expense_amount":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление расхода отменено.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        try:
            amount = float(text)
            user_states[str(chat_id)] = {"action": "adding_expense_category", "amount": amount}
            cats = get_categories("expense", chat_id)
            send_message(TOKEN, chat_id, "Выберите категорию расхода:", reply_markup=category_keyboard(cats))
        except:
            send_message(TOKEN, chat_id, "Введите корректное число или нажмите ❌ Отмена.")
        return

    if state.get("action") == "adding_expense_category":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление расхода отменено.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        # Аналогично, обработка callback

    if state.get("action") == "admin_broadcast":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Отправка сообщений отменена.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        # Рассылаем текст всем пользователям
        for uid in users.keys():
            send_message(TOKEN, int(uid), f"📢 <b>Сообщение от Админа:</b>\n\n{text}")
        send_message(TOKEN, chat_id, "Сообщение отправлено всем пользователям.", reply_markup=main_keyboard(chat_id))
        user_states.pop(str(chat_id), None)
        return

    # Обработка команд и старт
    if text == "/start":
        send_message(TOKEN, chat_id, "Привет! Я бот для учёта доходов и расходов.\nВыберите действие:", reply_markup=main_keyboard(chat_id))
        return

    send_message(TOKEN, chat_id, "Нажмите кнопку ниже для действий:", reply_markup=main_keyboard(chat_id))

def handle_callback(update):
    callback = update.get("callback_query")
    if not callback:
        return
    data_cb = callback["data"]
    chat_id = callback["message"]["chat"]["id"]
    callback_id = callback["id"]

    if data_cb == "cancel":
        user_states.pop(str(chat_id), None)
        send_message(TOKEN, chat_id, "Действие отменено.", reply_markup=main_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id, "Отменено")
        return

    if data_cb == "back_to_menu":
        user_states.pop(str(chat_id), None)
        send_message(TOKEN, chat_id, "Возвращаемся в меню.", reply_markup=main_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "add_income":
        user_states[str(chat_id)] = {"action": "adding_income_amount"}
        send_message(TOKEN, chat_id, "Введите сумму дохода:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "add_expense":
        user_states[str(chat_id)] = {"action": "adding_expense_amount"}
        send_message(TOKEN, chat_id, "Введите сумму расхода:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb.startswith("cat_"):
        category = data_cb[4:]
        state = user_states.get(str(chat_id), {})
        if not state:
            send_message(TOKEN, chat_id, "Ошибка, начните заново.", reply_markup=main_keyboard(chat_id))
            answer_callback_query(TOKEN, callback_id)
            return
        action = state.get("action")
        amount = state.get("amount")
        if action == "adding_income_category":
            add_record(chat_id, "income", amount, category)
            send_message(TOKEN, chat_id, f"✅ Доход {amount} в категории «{category}» добавлен.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
        elif action == "adding_expense_category":
            add_record(chat_id, "expense", amount, category)
            send_message(TOKEN, chat_id, f"✅ Расход {amount} в категории «{category}» добавлен.", reply_markup=main_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
        else:
            send_message(TOKEN, chat_id, "Ошибка, начните заново.", reply_markup=main_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "reports":
        text = "Выберите отчёт:\n" \
               "📅 /report_day - За день\n" \
               "📅 /report_week - За неделю\n" \
               "📅 /report_month - За месяц\n" \
               "🧾 /report_all - За всё время\n" \
               "Введите команду."
        send_message(TOKEN, chat_id, text, reply_markup=back_to_menu_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "contact_admin":
        user_states[str(chat_id)] = {"action": "contact_admin"}
        send_message(TOKEN, chat_id, "Напишите сообщение для администратора:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "users_list" and chat_id == ADMIN_ID:
        users_count = len(users)
        send_message(TOKEN, chat_id, f"Всего пользователей: {users_count}", reply_markup=back_to_menu_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "add_category":
        state = user_states.get(str(chat_id), {})
        if not state:
            send_message(TOKEN, chat_id, "Ошибка. Начните заново.", reply_markup=main_keyboard(chat_id))
            answer_callback_query(TOKEN, callback_id)
            return
        user_states[str(chat_id)] = {"action": "adding_category", "cat_type": "income" if "income" in state.get("action", "") else "expense"}
        send_message(TOKEN, chat_id, "Введите название новой категории:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

def main():
    offset = 0
    print("Бот запущен...")
    while True:
        updates = get_updates(TOKEN, offset, timeout=20)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"].get("text", "")
                    # Обработка команд для отчетов
                    if text.startswith("/report_"):
                        period = text[8:]
                        if period in ["day", "week", "month", "all"]:
                            rep_text = get_report(chat_id, period)
                            send_message(TOKEN, chat_id, rep_text, reply_markup=back_to_menu_keyboard())
                        else:
                            send_message(TOKEN, chat_id, "Неверная команда отчёта.", reply_markup=back_to_menu_keyboard())
                    else:
                        handle_message(update)
                elif "callback_query" in update:
                    handle_callback(update)
            except Exception as e:
                print(f"Ошибка в основном цикле: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
