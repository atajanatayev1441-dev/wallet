import os
import time
import json
import traceback
import csv
from io import StringIO

from telegram_api import send_message, get_updates, send_sticker, answer_callback_query

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables.")

ADMIN_ID = int(os.getenv("ADMIN_ID", "8283258905"))

USERS_FILE = "users.json"
DATA_FILE = "user_data.json"

users = set()
user_currency = {}
user_states = {}
user_data = {}

# Состояния для добавления дохода/расхода
STATE_NONE = 0
STATE_ADD_INCOME_AMOUNT = 1
STATE_ADD_INCOME_CATEGORY = 2
STATE_ADD_EXPENSE_AMOUNT = 3
STATE_ADD_EXPENSE_CATEGORY = 4
STATE_ADMIN_BROADCAST = 5

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
    return json.dumps({"inline_keyboard": buttons})

def build_reply_keyboard(buttons):
    return json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": True
    })

def start_message(chat_id):
    text = "👋 <b>Привет! Выбери валюту для учёта доходов и расходов:</b>"
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
        [{"text": "📊 Показать баланс"}],
    ]
    if chat_id == ADMIN_ID:
        buttons.append([{"text": "👥 Пользователи"}, {"text": "📢 Рассылка"}])
    reply_markup = build_reply_keyboard(buttons)
    send_message(TOKEN, chat_id, "Выбери действие:", reply_markup)

def show_balance(chat_id):
    data = user_data.get(str(chat_id), {"income": [], "expense": []})
    currency = user_currency.get(chat_id, "RUB")
    income_sum = sum(item["amount"] for item in data.get("income", []))
    expense_sum = sum(item["amount"] for item in data.get("expense", []))
    balance = income_sum - expense_sum
    text = (
        f"💰 Баланс: {balance} {currency}\n"
        f"📈 Доходы: {income_sum} {currency}\n"
        f"📉 Расходы: {expense_sum} {currency}"
    )
    send_message(TOKEN, chat_id, text)

def add_income_start(chat_id):
    send_message(TOKEN, chat_id, "Введите сумму дохода или нажмите ❌ Отмена:", build_reply_keyboard([["❌ Отмена"]]))
    user_states[chat_id] = STATE_ADD_INCOME_AMOUNT

def add_expense_start(chat_id):
    send_message(TOKEN, chat_id, "Введите сумму расхода или нажмите ❌ Отмена:", build_reply_keyboard([["❌ Отмена"]]))
    user_states[chat_id] = STATE_ADD_EXPENSE_AMOUNT

def handle_income_amount(chat_id, text):
    if not text.replace(".", "", 1).isdigit():
        send_message(TOKEN, chat_id, "Некорректная сумма. Введите число или нажмите ❌ Отмена.")
        return
    user_data.setdefault(str(chat_id), {"income": [], "expense": []})
    user_states[chat_id] = STATE_ADD_INCOME_CATEGORY
    user_data[str(chat_id)]["temp_amount"] = float(text)
    send_message(TOKEN, chat_id, "Введите категорию дохода или нажмите ❌ Отмена:")

def handle_income_category(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление дохода отменено.")
        main_menu(chat_id)
        return
    amount = user_data[str(chat_id)].pop("temp_amount", 0)
    user_data[str(chat_id)]["income"].append({"amount": amount, "category": text})
    save_user_data()
    reset_state(chat_id)
    send_message(TOKEN, chat_id, f"✅ Доход {amount} добавлен в категорию '{text}'.")
    main_menu(chat_id)

def handle_expense_amount(chat_id, text):
    if not text.replace(".", "", 1).isdigit():
        send_message(TOKEN, chat_id, "Некорректная сумма. Введите число или нажмите ❌ Отмена.")
        return
    user_data.setdefault(str(chat_id), {"income": [], "expense": []})
    user_states[chat_id] = STATE_ADD_EXPENSE_CATEGORY
    user_data[str(chat_id)]["temp_amount"] = float(text)
    send_message(TOKEN, chat_id, "Введите категорию расхода или нажмите ❌ Отмена:")

def handle_expense_category(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Добавление расхода отменено.")
        main_menu(chat_id)
        return
    amount = user_data[str(chat_id)].pop("temp_amount", 0)
    user_data[str(chat_id)]["expense"].append({"amount": amount, "category": text})
    save_user_data()
    reset_state(chat_id)
    send_message(TOKEN, chat_id, f"✅ Расход {amount} добавлен в категорию '{text}'.")
    main_menu(chat_id)

def send_users_excel(chat_id):
    if chat_id != ADMIN_ID:
        send_message(TOKEN, chat_id, "У вас нет прав для этой команды.")
        return
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID"])
    for u in users:
        writer.writerow([u])
    output.seek(0)
    filename = "users.csv"
    with open(filename, "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())
    # Здесь нет простой возможности отправить файл без сторонних библиотек,
    # так что отправим просто список ID
    send_message(TOKEN, ADMIN_ID, "Пользователи (User IDs):\n" + "\n".join(str(u) for u in users))
    os.remove(filename)

def handle_admin_broadcast(chat_id, text):
    if text == "❌ Отмена":
        reset_state(chat_id)
        send_message(TOKEN, chat_id, "Рассылка отменена.")
        main_menu(chat_id)
        return
    for u in users:
        send_message(TOKEN, u, f"📢 Сообщение от администратора:\n\n{text}")
    reset_state(chat_id)
    send_message(TOKEN, chat_id, "✅ Рассылка отправлена всем пользователям.")
    main_menu(chat_id)

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
        if text == "❌ Отмена":
            reset_state(chat_id)
            send_message(TOKEN, chat_id, "Добавление дохода отменено.")
            main_menu(chat_id)
        else:
            handle_income_amount(chat_id, text)
        return

    if state == STATE_ADD_INCOME_CATEGORY:
        handle_income_category(chat_id, text)
        return

    if state == STATE_ADD_EXPENSE_AMOUNT:
        if text == "❌ Отмена":
            reset_state(chat_id)
            send_message(TOKEN, chat_id, "Добавление расхода отменено.")
            main_menu(chat_id)
        else:
            handle_expense_amount(chat_id, text)
        return

    if state == STATE_ADD_EXPENSE_CATEGORY:
        handle_expense_category(chat_id, text)
        return

    if state == STATE_ADMIN_BROADCAST:
        handle_admin_broadcast(chat_id, text)
        return

    if text == "➕ Добавить доход":
        add_income_start(chat_id)
    elif text == "➖ Добавить расход":
        add_expense_start(chat_id)
    elif text == "📊 Показать баланс":
        show_balance(chat_id)
    elif text == "👥 Пользователи" and chat_id == ADMIN_ID:
        send_users_excel(chat_id)
    elif text == "📢 Рассылка" and chat_id == ADMIN_ID:
        send_message(TOKEN, chat_id, "Введите сообщение для рассылки всем пользователям или ❌ Отмена.")
        user_states[chat_id] = STATE_ADMIN_BROADCAST
    else:
        send_message(TOKEN, chat_id, "Неизвестная команда. Пожалуйста, выберите действие из меню.")
        main_menu(chat_id)

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
    else:
        answer_callback_query(TOKEN, callback_id)

def main():
    global offset
    global users
    global user_data
    global user_currency
    global user_states

    offset = 0

    users = load_users()
    user_data = load_user_data()
    user_currency = {}
    user_states = {}

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
