import os
import time
import json
import csv
import urllib.request

from telegram_api import send_message, get_updates, api_call

ADMIN_ID = 8283258905  # Ваш ID администратора, замените на свой

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Set it in environment variables.")

USERS_FILE = "users.json"

offset = 0
user_currency = {}
user_states = {}

STICKERS = {
    "RUB": "CAACAgIAAxkBAAIBHmHqg6R7_R8US-V7C1d27gU8RxFwAAKdBAACGhTgSvhN14Xw45bsLwQ",
    "USD": "CAACAgIAAxkBAAIBIGHqg67DxFjkDTr6ZAmvsk2yk-6WAAJhBAACGhTgSn1DrRzknzxVvLwQ",
    "TMT": "CAACAgIAAxkBAAIBIWHqg6eX6aHYo2ycbVjL8DkQwFtuAAJfBAACGhTgSnESevjE6ivF4LwQ"
}

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

users = load_users()

def reset_state(chat_id):
    if chat_id in user_states:
        del user_states[chat_id]

def build_inline_keyboard(buttons):
    keyboard = {"inline_keyboard": buttons}
    return json.dumps(keyboard)

def send_sticker(token, chat_id, sticker_id):
    params = {"chat_id": chat_id, "sticker": sticker_id}
    return api_call(token, "sendSticker", params)

def start_message(chat_id):
    text = (
        "👋 <b>Привет! Выбери валюту для учёта доходов и расходов:</b>"
    )
    buttons = [
        [
            {"text": "🇷🇺 RUB", "callback_data": "currency_RUB"},
            {"text": "🇺🇸 USD", "callback_data": "currency_USD"},
            {"text": "🇹🇲 TMT", "callback_data": "currency_TMT"},
        ]
    ]
    reply_markup = build_inline_keyboard(buttons)
    send_message(TOKEN, chat_id, text, reply_markup)

def main_menu_text_and_keyboard(chat_id):
    text = (
        "👋 <b>Привет! Я твой трекер кошелька.</b>\n\n"
        "Выбери действие или воспользуйся командами:\n"
        "/add_income — Добавить доход\n"
        "/add_expense — Добавить расход\n"
        "/balance — Показать баланс\n"
        "/report — Показать отчёт\n"
        "/categories — Категории расходов\n"
        "/support — Связь с админом"
    )
    buttons = [
        [{"text": "➕ Добавить доход"}, {"text": "➖ Добавить расход"}],
        [{"text": "💰 Баланс"}, {"text": "📊 Отчёт"}],
        [{"text": "📂 Категории"}, {"text": "📩 Связь с админом"}],
    ]
    # Добавляем кнопку "Количество пользователей" только если админ
    if chat_id == ADMIN_ID:
        buttons.append([{"text": "👥 Количество пользователей"}])

    reply_markup = json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": False
    })
    return text, reply_markup

def send_users_file(token, chat_id, users):
    filename = "users.csv"
    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User Chat ID"])
        for user_id in users:
            writer.writerow([user_id])

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    data_list = []

    # chat_id field
    data_list.append(f'--{boundary}')
    data_list.append('Content-Disposition: form-data; name="chat_id"\r\n')
    data_list.append(str(chat_id))

    # document field
    data_list.append(f'--{boundary}')
    data_list.append('Content-Disposition: form-data; name="document"; filename="users.csv"')
    data_list.append('Content-Type: text/csv\r\n')

    with open(filename, "rb") as f:
        file_content = f.read()
    data_list.append(file_content)

    data_list.append(f'--{boundary}--\r\n')

    body = b"\r\n".join(
        item.encode() if isinstance(item, str) else item
        for item in data_list
    )

    url = f"https://api.telegram.org/bot{token}/sendDocument"

    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    try:
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print("Ошибка отправки файла:", e)
        return None

def handle_message(message, currency):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    state = user_states.get(chat_id)

    # Добавляем пользователя если новый
    if chat_id not in users:
        users.add(chat_id)
        save_users(users)

    # Обработка команды показа пользователей (только админ)
    if text == "/users" or text == "👥 Количество пользователей":
        if chat_id == ADMIN_ID:
            send_users_file(TOKEN, chat_id, users)
        else:
            send_message(TOKEN, chat_id, "❌ Эта команда доступна только администратору.")
        return

    if text == "/start" or text == "🔄 Главное меню":
        reset_state(chat_id)
        if chat_id not in user_currency or user_currency[chat_id] is None:
            start_message(chat_id)
            user_currency[chat_id] = None
        else:
            text, reply_markup = main_menu_text_and_keyboard(chat_id)
            send_message(TOKEN, chat_id, text, reply_markup)
        return

    # -- Добавляй сюда остальную обработку состояний, команд, диалогов --
    # Например: добавление дохода/расхода, поддержка и пр.
    # ...
    # Для краткости не дублирую весь код сюда — могу помочь отдельно.

    send_message(TOKEN, chat_id, "❓ Неизвестная команда. Напишите /start для начала.")

def main():
    global offset
    global user_currency

    print("Бот запущен")
    while True:
        updates = get_updates(TOKEN, offset)
        if not updates:
            time.sleep(1)
            continue

        for update in updates:
            offset = update["update_id"] + 1

            if "message" in update:
                message = update["message"]
                chat_id = message["chat"]["id"]

                if chat_id not in user_currency or user_currency[chat_id] is None:
                    start_message(chat_id)
                    user_currency[chat_id] = None
                    continue

                handle_message(message, user_currency[chat_id])

            elif "callback_query" in update:
                callback = update["callback_query"]
                data = callback["data"]
                chat_id = callback["message"]["chat"]["id"]

                if data.startswith("currency_"):
                    currency = data.split("_")[1]
                    user_currency[chat_id] = currency
                    send_message(TOKEN, chat_id, f"✅ Валюта установлена: {currency}")

                    sticker_id = STICKERS.get(currency)
                    if sticker_id:
                        send_sticker(TOKEN, chat_id, sticker_id)

                    text, reply_markup = main_menu_text_and_keyboard(chat_id)
                    send_message(TOKEN, chat_id, text, reply_markup)


if __name__ == "__main__":
    main()
