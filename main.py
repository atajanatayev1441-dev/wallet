import time
import json
import datetime
from telegram_api import get_updates, send_message, answer_callback_query

TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
ADMIN_ID = 123456789  # Ваш ID

USERS_FILE = "users.json"
DATA_FILE = "data.json"

user_states = {}
users = {}
data = {}

def load_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

def init_data():
    global users, data
    users = load_json(USERS_FILE)
    data = load_json(DATA_FILE)
    if "currencies" not in data:
        data["currencies"] = {}
    if "categories" not in data:
        data["categories"] = {}
    if "records" not in data:
        data["records"] = {}

def save_all():
    save_json(USERS_FILE, users)
    save_json(DATA_FILE, data)

def keyboard_inline(buttons):
    return {"inline_keyboard": buttons}

def main_menu_keyboard(chat_id):
    kb = [
        [{"text": "➕ Добавить доход", "callback_data": "add_income"}],
        [{"text": "➖ Добавить расход", "callback_data": "add_expense"}],
        [{"text": "📊 Отчёты и анализ", "callback_data": "reports"}],
        [{"text": "✉️ Связь с админом", "callback_data": "contact_admin"}]
    ]
    if chat_id == ADMIN_ID:
        kb.append([{"text": "👥 Пользователи", "callback_data": "users_list"}])
    return keyboard_inline(kb)

def cancel_keyboard():
    return keyboard_inline([[{"text": "❌ Отмена", "callback_data": "cancel"}]])

def back_to_menu_keyboard():
    return keyboard_inline([[{"text": "⬅️ Вернуться в меню", "callback_data": "back_to_menu"}]])

def categories_keyboard(cat_list):
    kb = [[{"text": c, "callback_data": f"cat_{c}"}] for c in cat_list]
    kb.append([{"text": "➕ Добавить категорию", "callback_data": "add_category"}])
    kb.append([{"text": "❌ Отмена", "callback_data": "cancel"}])
    return keyboard_inline(kb)

def currency_keyboard():
    kb = [[{"text": cur, "callback_data": f"currency_{cur}"}] for cur in ["RUB", "TMT", "USD"]]
    return keyboard_inline(kb)

def save_user_currency(chat_id, currency):
    data["currencies"][str(chat_id)] = currency
    save_json(DATA_FILE, data)

def get_user_currency(chat_id):
    return data["currencies"].get(str(chat_id), "RUB")

def get_user_categories(chat_id, cat_type):
    key = f"{chat_id}_{cat_type}"
    if key not in data["categories"]:
        data["categories"][key] = ["Общее"]
        save_json(DATA_FILE, data)
    return data["categories"][key]

def add_user_category(chat_id, cat_type, category_name):
    key = f"{chat_id}_{cat_type}"
    if key not in data["categories"]:
        data["categories"][key] = []
    if category_name not in data["categories"][key]:
        data["categories"][key].append(category_name)
        save_json(DATA_FILE, data)

def add_record(chat_id, rec_type, amount, category, comment=""):
    if str(chat_id) not in data["records"]:
        data["records"][str(chat_id)] = []
    data["records"][str(chat_id)].append({
        "type": rec_type,
        "amount": amount,
        "category": category,
        "comment": comment,
        "timestamp": int(time.time())
    })
    save_json(DATA_FILE, data)

def format_report(chat_id, period="all", rec_type=None):
    now = int(time.time())
    start_ts = 0
    if period == "day":
        start_ts = now - 86400
    elif period == "week":
        start_ts = now - 7 * 86400
    elif period == "month":
        start_ts = now - 30 * 86400
    records = data.get("records", {}).get(str(chat_id), [])
    filtered = [r for r in records if r["timestamp"] >= start_ts]
    if rec_type:
        filtered = [r for r in filtered if r["type"] == rec_type]
    if not filtered:
        return "Нет данных для выбранного периода."

    sums = {}
    total = 0
    for r in filtered:
        cat = r["category"]
        sums[cat] = sums.get(cat, 0) + float(r["amount"])
        total += float(r["amount"])

    lines = [f"<b>Отчёт за {period} ({'доходы' if rec_type=='income' else 'расходы' if rec_type=='expense' else 'все записи'}):</b>"]
    for cat, amount in sorted(sums.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"{cat}: {amount:.2f} {get_user_currency(chat_id)}")
    lines.append(f"\n<b>Итого:</b> {total:.2f} {get_user_currency(chat_id)}")
    return "\n".join(lines)

def handle_start(chat_id):
    text = ("Привет! Добро пожаловать в бот учёта доходов и расходов.\n\n"
            "Пожалуйста, выберите валюту для работы:")
    send_message(TOKEN, chat_id, text, reply_markup=currency_keyboard())
    user_states[str(chat_id)] = {"action": "choosing_currency"}

def handle_callback(update):
    callback = update.get("callback_query")
    if not callback:
        return
    chat_id = callback["message"]["chat"]["id"]
    data_cb = callback["data"]
    callback_id = callback["id"]

    if data_cb == "cancel":
        user_states.pop(str(chat_id), None)
        send_message(TOKEN, chat_id, "Действие отменено.", reply_markup=main_menu_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id, "Отменено")
        return
    if data_cb == "back_to_menu":
        user_states.pop(str(chat_id), None)
        send_message(TOKEN, chat_id, "Возвращаемся в меню.", reply_markup=main_menu_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb.startswith("currency_"):
        currency = data_cb.split("_")[1]
        save_user_currency(chat_id, currency)
        send_message(TOKEN, chat_id, f"Валюта установлена: <b>{currency}</b>", reply_markup=main_menu_keyboard(chat_id))
        user_states.pop(str(chat_id), None)
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "add_income":
        user_states[str(chat_id)] = {"action": "input_income_amount"}
        send_message(TOKEN, chat_id, "Введите сумму дохода:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return
    if data_cb == "add_expense":
        user_states[str(chat_id)] = {"action": "input_expense_amount"}
        send_message(TOKEN, chat_id, "Введите сумму расхода:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return
    if data_cb == "reports":
        kb = keyboard_inline([
            [{"text": "📅 Доходы за день", "callback_data": "report_income_day"}],
            [{"text": "📅 Расходы за день", "callback_data": "report_expense_day"}],
            [{"text": "📅 Доходы за неделю", "callback_data": "report_income_week"}],
            [{"text": "📅 Расходы за неделю", "callback_data": "report_expense_week"}],
            [{"text": "📅 Доходы за месяц", "callback_data": "report_income_month"}],
            [{"text": "📅 Расходы за месяц", "callback_data": "report_expense_month"}],
            [{"text": "🧾 Все записи", "callback_data": "report_all"}],
            [{"text": "⬅️ Вернуться в меню", "callback_data": "back_to_menu"}],
        ])
        send_message(TOKEN, chat_id, "Выберите отчёт:", reply_markup=kb)
        answer_callback_query(TOKEN, callback_id)
        return
    if data_cb == "contact_admin":
        user_states[str(chat_id)] = {"action": "contact_admin"}
        send_message(TOKEN, chat_id, "Напишите сообщение для администратора:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return
    if data_cb == "users_list" and chat_id == ADMIN_ID:
        send_message(TOKEN, chat_id, f"Всего пользователей: {len(users)}", reply_markup=back_to_menu_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb.startswith("cat_"):
        category = data_cb[4:]
        state = user_states.get(str(chat_id), {})
        if not state:
            send_message(TOKEN, chat_id, "Ошибка. Начните заново.", reply_markup=main_menu_keyboard(chat_id))
            answer_callback_query(TOKEN, callback_id)
            return
        action = state.get("action")
        amount = state.get("amount")
        if action == "choose_income_category":
            add_record(chat_id, "income", amount, category)
            send_message(TOKEN, chat_id, f"✅ Доход {amount} {get_user_currency(chat_id)} в категории «{category}» добавлен.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
        elif action == "choose_expense_category":
            add_record(chat_id, "expense", amount, category)
            send_message(TOKEN, chat_id, f"✅ Расход {amount} {get_user_currency(chat_id)} в категории «{category}» добавлен.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
        else:
            send_message(TOKEN, chat_id, "Ошибка. Начните заново.", reply_markup=main_menu_keyboard(chat_id))
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb == "add_category":
        state = user_states.get(str(chat_id), {})
        if not state or "cat_type" not in state:
            send_message(TOKEN, chat_id, "Ошибка. Начните заново.", reply_markup=main_menu_keyboard(chat_id))
            answer_callback_query(TOKEN, callback_id)
            return
        user_states[str(chat_id)] = {"action": "adding_category", "cat_type": state["cat_type"]}
        send_message(TOKEN, chat_id, "Введите название новой категории:", reply_markup=cancel_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

    if data_cb.startswith("report_"):
        rep = data_cb.split("_")
        if len(rep) >= 2:
            if rep[1] == "all":
                text = format_report(chat_id, period="all")
            else:
                rec_type = "income" if rep[1] == "income" else "expense" if rep[1] == "expense" else None
                period = rep[2] if len(rep) > 2 else "all"
                text = format_report(chat_id, period=period, rec_type=rec_type)
            send_message(TOKEN, chat_id, text, reply_markup=back_to_menu_keyboard())
        else:
            send_message(TOKEN, chat_id, "Неверная команда отчёта.", reply_markup=back_to_menu_keyboard())
        answer_callback_query(TOKEN, callback_id)
        return

def handle_message(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if str(chat_id) not in users:
        users[str(chat_id)] = {
            "id": chat_id,
            "username": message["from"].get("username", ""),
            "first_name": message["from"].get("first_name", ""),
        }
        save_json(USERS_FILE, users)

    state = user_states.get(str(chat_id), {})

    if state.get("action") == "choosing_currency":
        send_message(TOKEN, chat_id, "Пожалуйста, выберите валюту с помощью кнопок ниже.", reply_markup=currency_keyboard())
        return

    if state.get("action") == "input_income_amount":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление дохода отменено.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        try:
            amount = float(text.replace(",", "."))
            cats = get_user_categories(chat_id, "income")
            user_states[str(chat_id)] = {"action": "choose_income_category", "amount": amount}
            send_message(TOKEN, chat_id, "Выберите категорию дохода или добавьте новую:", reply_markup=categories_keyboard(cats))
        except:
            send_message(TOKEN, chat_id, "Введите корректное число или нажмите ❌ Отмена.", reply_markup=cancel_keyboard())
        return

    if state.get("action") == "input_expense_amount":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление расхода отменено.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        try:
            amount = float(text.replace(",", "."))
            cats = get_user_categories(chat_id, "expense")
            user_states[str(chat_id)] = {"action": "choose_expense_category", "amount": amount}
            send_message(TOKEN, chat_id, "Выберите категорию расхода или добавьте новую:", reply_markup=categories_keyboard(cats))
        except:
            send_message(TOKEN, chat_id, "Введите корректное число или нажмите ❌ Отмена.", reply_markup=cancel_keyboard())
        return

    if state.get("action") == "adding_category":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Добавление категории отменено.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        cat_type = state.get("cat_type")
        category_name = text.strip()
        if not category_name:
            send_message(TOKEN, chat_id, "Название категории не может быть пустым. Попробуйте снова или нажмите ❌ Отмена.", reply_markup=cancel_keyboard())
            return
        add_user_category(chat_id, cat_type, category_name)
        send_message(TOKEN, chat_id, f"Категория «{category_name}» добавлена.", reply_markup=main_menu_keyboard(chat_id))
        user_states.pop(str(chat_id), None)
        return

    if state.get("action") == "contact_admin":
        if text == "❌ Отмена":
            send_message(TOKEN, chat_id, "Отправка сообщения администратору отменена.", reply_markup=main_menu_keyboard(chat_id))
            user_states.pop(str(chat_id), None)
            return
        admin_message = (
            f"Сообщение от пользователя <b>{users.get(str(chat_id), {}).get('first_name', '')} "
            f"(@{users.get(str(chat_id), {}).get('username', '')})</b>:\n\n{text}"
        )
        send_message(TOKEN, ADMIN_ID, admin_message)
        send_message(TOKEN, chat_id, "Ваше сообщение отправлено администратору.", reply_markup=main_menu_keyboard(chat_id))
        user_states.pop(str(chat_id), None)
        return

    # Команда /start
    if text == "/start":
        handle_start(chat_id)
        return

    # Если нет текущего действия — показать меню
    if not state:
        send_message(TOKEN, chat_id, "Выберите действие:", reply_markup=main_menu_keyboard(chat_id))

def main():
    init_data()
    offset = 0
    while True:
        updates = get_updates(TOKEN, offset)
        if not updates:
            time.sleep(1)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            if "callback_query" in update:
                handle_callback(update)
            elif "message" in update:
                handle_message(update)

if __name__ == "__main__":
    main()
