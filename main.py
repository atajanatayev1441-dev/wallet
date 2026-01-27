import os
import time
import json
import traceback
from datetime import datetime, timedelta
from collections import defaultdict

from telegram_api import send_message, get_updates, answer_callback_query

TOKEN = os.getenv("BOT_TOKEN")  # Твой токен бота
ADMIN_ID = int(os.getenv("ADMIN_ID", "8283258905"))  # Админ ID

USERS_FILE = "users.json"
DATA_FILE = "user_data.json"

users = set()
user_data = {}
user_states = {}
user_currency = {}

# Состояния
STATE_NONE = 0
STATE_ADD_INCOME_AMOUNT = 1
STATE_ADD_INCOME_CATEGORY = 2
STATE_ADD_EXPENSE_AMOUNT = 3
STATE_ADD_EXPENSE_CATEGORY = 4
STATE_REPORT_CHOOSE_TYPE = 5
STATE_REPORT_CHOOSE_PERIOD = 6
STATE_ADMIN_FEEDBACK = 7

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения файла {filename}: {e}")

def load_users():
    return set(load_json(USERS_FILE, []))

def save_users():
    save_json(USERS_FILE, list(users))

def load_user_data():
    return load_json(DATA_FILE, {})

def save_user_data():
    save_json(DATA_FILE, user_data)

def reset_state(chat_id):
    user_states[chat_id] = STATE_NONE

def build_inline_keyboard(buttons):
    import json
    return json.dumps({"inline_keyboard": buttons})

def build_reply_keyboard(buttons):
    import json
    return json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": True
    })

def start_message(chat_id):
    text = "👋 <b>Привет! Выбери валюту для учета доходов и расходов:</b>"
    buttons = [[
        {"text": "🇷🇺 RUB", "callback_data": "currency_RUB"},
        {"text": "🇺🇸 USD", "callback_data": "currency_USD"},
        {"text": "🇹🇲 TMT", "callback_data": "currency_TMT"},
    ]]
    reply_markup = build_inline_keyboard(buttons)
    send_message(TOKEN, chat_id, text, reply_markup)

def main_menu(chat_id):
    buttons = [
        [{"text": "➕ Добавить доход"}, {"text": "➖ Добавить расход"}],
        [{"text": "📊 Отчёты"}, {"text": "📈 Баланс"}],
        [{"text": "✉️ Связь с админом"}]
    ]
    if chat_id == ADMIN_ID:
        buttons.append([{"text": "👥 Пользователи"}, {"text": "📢 Рассылка"}])
    reply_markup = build_reply_keyboard(buttons)
    send_message(TOKEN, chat_id, "Выбери действие:", reply_markup)

def is_valid_amount(text):
    try:
        val = float(text)
        return val > 0
    except:
        return False

def handle_income_amount(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление дохода отменено.")
        main_menu(chat_id)
        return
    if not is_valid_amount(text):
        send_message(TOKEN, chat_id, "Неверная сумма. Введите положительное число или ❌ Отмена.")
        return
    user_data.setdefault(str(chat_id), {"income": [], "expense": []})
    user_states[chat_id] = STATE_ADD_INCOME_CATEGORY
    user_data[str(chat_id)]["temp_amount"] = float(text)
    send_message(TOKEN, chat_id, "Введите категорию дохода или ❌ Отмена:")

def handle_income_category(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление дохода отменено.")
        main_menu(chat_id)
        return
    amount = user_data[str(chat_id)].pop("temp_amount", 0)
    timestamp = int(time.time())
    user_data[str(chat_id)]["income"].append({"amount": amount, "category": text, "date": timestamp})
    save_user_data()
    reset_state(chat_id)
    send_message(TOKEN, chat_id, f"✅ Доход {amount} добавлен в категорию '{text}'.")
    main_menu(chat_id)

def handle_expense_amount(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление расхода отменено.")
        main_menu(chat_id)
        return
    if not is_valid_amount(text):
        send_message(TOKEN, chat_id, "Неверная сумма. Введите положительное число или ❌ Отмена.")
        return
    user_data.setdefault(str(chat_id), {"income": [], "expense": []})
    user_states[chat_id] = STATE_ADD_EXPENSE_CATEGORY
    user_data[str(chat_id)]["temp_amount"] = float(text)
    send_message(TOKEN, chat_id, "Введите категорию расхода или ❌ Отмена:")

def handle_expense_category(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление расхода отменено.")
        main_menu(chat_id)
        return
    amount = user_data[str(chat_id)].pop("temp_amount", 0)
    timestamp = int(time.time())
    user_data[str(chat_id)]["expense"].append({"amount": amount, "category": text, "date": timestamp})
    save_user_data()
    reset_state(chat_id)
    send_message(TOKEN, chat_id, f"✅ Расход {amount} добавлен в категорию '{text}'.")
    main_menu(chat_id)

def show_balance(chat_id):
    data = user_data.get(str(chat_id), {"income": [], "expense": []})
    currency = user_currency.get(chat_id, "RUB")
    income_sum = sum(item["amount"] for item in data.get("income", []))
    expense_sum = sum(item["amount"] for item in data.get("expense", []))
    balance = income_sum - expense_sum
    text = (
        f"💰 Баланс: {balance:.2f} {currency}\n"
        f"📈 Доходы: {income_sum:.2f} {currency}\n"
        f"📉 Расходы: {expense_sum:.2f} {currency}"
    )
    send_message(TOKEN, chat_id, text)

def parse_date(timestamp):
    return datetime.fromtimestamp(timestamp)

def filter_by_period(items, days):
    cutoff = datetime.now() - timedelta(days=days)
    return [item for item in items if parse_date(item["date"]) >= cutoff]

def report_income(chat_id, days):
    data = user_data.get(str(chat_id), {"income": []})
    filtered = filter_by_period(data.get("income", []), days)
    total = sum(item["amount"] for item in filtered)
    lines = [f"📈 Доходы за последние {days} дней: {total:.2f}"]
    categories = defaultdict(float)
    for item in filtered:
        categories[item["category"]] += item["amount"]
    for cat, val in categories.items():
        percent = val / total * 100 if total else 0
        lines.append(f"{cat}: {val:.2f} ({percent:.1f}%)")
    return "\n".join(lines)

def report_expense(chat_id, days):
    data = user_data.get(str(chat_id), {"expense": []})
    filtered = filter_by_period(data.get("expense", []), days)
    total = sum(item["amount"] for item in filtered)
    lines = [f"📉 Расходы за последние {days} дней: {total:.2f}"]
    categories = defaultdict(float)
    for item in filtered:
        categories[item["category"]] += item["amount"]
    for cat, val in categories.items():
        percent = val / total * 100 if total else 0
        lines.append(f"{cat}: {val:.2f} ({percent:.1f}%)")
    return "\n".join(lines)

def handle_report_type(chat_id, text):
    if text == "Доходы":
        user_states[chat_id] = (STATE_REPORT_CHOOSE_PERIOD, "income")
        send_message(TOKEN, chat_id, "Выберите период:", build_inline_keyboard([
            [{"text": "1 день", "callback_data": "report_income_1"}],
            [{"text": "7 дней", "callback_data": "report_income_7"}],
            [{"text": "30 дней", "callback_data": "report_income_30"}],
            [{"text": "Отмена", "callback_data": "cancel"}],
        ]))
    elif text == "Расходы":
        user_states[chat_id] = (STATE_REPORT_CHOOSE_PERIOD, "expense")
        send_message(TOKEN, chat_id, "Выберите период:", build_inline_keyboard([
            [{"text": "1 день", "callback_data": "report_expense_1"}],
            [{"text": "7 дней", "callback_data": "report_expense_7"}],
            [{"text": "30 дней", "callback_data": "report_expense_30"}],
            [{"text": "Отмена", "callback_data": "cancel"}],
        ]))
    else:
        send_message(TOKEN, chat_id, "Выберите 'Доходы' или 'Расходы'.")

def handle_callback(update):
    callback = update.get("callback_query")
    if not callback:
        return
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    callback_id = callback["id"]

    if data.startswith("currency_"):
        currency = data.split("_")[1]
        user_currency[chat_id] = currency
        answer_callback_query(TOKEN, callback_id)
        send_message(TOKEN, chat_id, f"Выбрана валюта: {currency} ✅")
        main_menu(chat_id)
        return

    if data.startswith("report_"):
        answer_callback_query(TOKEN, callback_id)
        parts = data.split("_")
        if parts[-1] == "cancel":
            reset_state(chat_id)
            send_message(TOKEN, chat_id, "Отмена.")
            main_menu(chat_id)
            return
        report_type = parts[1]
        days = int(parts[2])
        if report_type == "income":
            text = report_income(chat_id, days)
        else:
            text = report_expense(chat_id, days)
        send_message(TOKEN, chat_id, text)
        main_menu(chat_id)
        reset_state(chat_id)
        return

    if data == "cancel":
        answer_callback_query(TOKEN, callback_id)
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Отмена.")
        main_menu(chat_id)
        return

    answer_callback_query(TOKEN, callback_id)

def handle_message(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if chat_id not in users:
        users.add(chat_id)
        save_users()

    state = user_states.get(chat_id, STATE_NONE)

    if text == "/start":
        start_message(chat_id)
        reset_state(chat_id)
        return

    if state == STATE_ADD_INCOME_AMOUNT:
        handle_income_amount(chat_id, text)
        return

    if state == STATE_ADD_INCOME_CATEGORY:
        handle_income_category(chat_id, text)
        return

    if state == STATE_ADD_EXPENSE_AMOUNT:
        handle_expense_amount(chat_id, text)
        return

    if state == STATE_ADD_EXPENSE_CATEGORY:
        handle_expense_category(chat_id, text)
        return

    if state == STATE_ADMIN_FEEDBACK:
        if text == "❌ Отмена":
            reset_state(chat_id)
            send_message(TOKEN, chat_id, "Отмена отправки сообщения админу.")
            main_menu(chat_id)
        else:
            send_message(TOKEN, ADMIN_ID, f"Сообщение от пользователя {chat_id}:\n\n{text}")
            send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.")
            reset_state(chat_id)
            main_menu(chat_id)
        return

    if text == "➕ Добавить доход":
        add_income_start(chat_id)
    elif text == "➖ Добавить расход":
        add_expense_start(chat_id)
    elif text == "📈 Баланс":
        show_balance(chat_id)
    elif text == "📊 Отчёты":
        user_states[chat_id] = STATE_REPORT_CHOOSE_TYPE
        send_message(TOKEN, chat_id, "Выберите отчет:", build_reply_keyboard([["Доходы"], ["Расходы"], ["Отмена"]]))
    elif text == "Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Отмена.")
        main_menu(chat_id)
    elif text == "✉️ Связь с админом":
        user_states[chat_id] = STATE_ADMIN_FEEDBACK
        send_message(TOKEN, chat_id, "Введите сообщение для администратора или ❌ Отмена:")
    elif state == STATE_REPORT_CHOOSE_TYPE:
        handle_report_type(chat_id, text)
    else:
        main_menu(chat_id)

def add_income_start(chat_id):
    send_message(TOKEN, chat_id, "Введите сумму дохода или ❌ Отмена:", build_reply_keyboard([["❌ Отмена"]]))
    user_states[chat_id] = STATE_ADD_INCOME_AMOUNT

def add_expense_start(chat_id):
    send_message(TOKEN, chat_id, "Введите сумму расхода или ❌ Отмена:", build_reply_keyboard([["❌ Отмена"]]))
    user_states[chat_id] = STATE_ADD_EXPENSE_AMOUNT

def main():
    global users, user_data, user_states, user_currency

    users = load_users()
    user_data = load_user_data()
    user_states = {}
    user_currency = {}

    offset = 0
    while True:
        try:
            updates = get_updates(TOKEN, offset, timeout=20)
            if not updates:
                continue
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update)
                else:
                    handle_message(update)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
