import os
import time
import json
import csv
import urllib.parse
import traceback

from telegram_api import send_message, get_updates, answer_callback_query, send_sticker

ADMIN_ID = int(os.getenv("ADMIN_ID", "8283258905"))
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Set it in environment variables.")

USERS_FILE = "users.json"
DATA_FILE = "user_data.json"

offset = 0
users = set()
user_currency = {}
user_states = {}

STICKERS = {
    "RUB": "CAACAgIAAxkBAAIBHmHqg6R7_R8US-V7C1d27gU8RxFwAAKdBAACGhTgSvhN14Xw45bsLwQ",
    "USD": "CAACAgIAAxkBAAIBIGHqg67DxFjkDTr6ZAmvsk2yk-6WAAJhBAACGhTgSn1DrRzknzxVvLwQ",
    "TMT": "CAACAgIAAxkBAAIBIWHqg6eX6aHYo2ycbVjL8DkQwFtuAAJfBAACGhTgSnESevjE6ivF4LwQ"
}

def load_json_file(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения файла {filename}: {e}")

def load_users():
    return set(load_json_file(USERS_FILE, []))

def save_users(users_set):
    save_json_file(USERS_FILE, list(users_set))

def load_user_data():
    return load_json_file(DATA_FILE, {})

def save_user_data(data):
    save_json_file(DATA_FILE, data)

def reset_state(chat_id):
    if chat_id in user_states:
        del user_states[chat_id]

def build_inline_keyboard(buttons):
    keyboard = {"inline_keyboard": buttons}
    return json.dumps(keyboard)

def build_cancel_keyboard():
    buttons = [[{"text": "❌ Отмена"}]]
    keyboard = {
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

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

# ... здесь остальной основной код main.py такой же, как я отправлял ранее, включая main() функцию ...

# main функция запускается только если скрипт запускается напрямую
if __name__ == "__main__":
    users.update(load_users())
    main()
