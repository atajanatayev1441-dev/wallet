import os
import time
import json
from telegram_api import send_message, get_updates, api_call

ADMIN_ID = 8283258905  # ID админа

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Set it in environment variables.")

offset = 0

user_currency = {}  # chat_id -> currency

# Стикеры для валют (примерные, замените на свои, если есть)
STICKERS = {
    "RUB": "CAACAgIAAxkBAAIBHmHqg6R7_R8US-V7C1d27gU8RxFwAAKdBAACGhTgSvhN14Xw45bsLwQ",
    "USD": "CAACAgIAAxkBAAIBIGHqg67DxFjkDTr6ZAmvsk2yk-6WAAJhBAACGhTgSn1DrRzknzxVvLwQ",
    "TMT": "CAACAgIAAxkBAAIBIWHqg6eX6aHYo2ycbVjL8DkQwFtuAAJfBAACGhTgSnESevjE6ivF4LwQ"
}

import json

def build_inline_keyboard(buttons):
    """
    Формируем JSON инлайн-клавиатуру.
    buttons - список списков кнопок: [[{"text": "Текст", "callback_data": "data"}], [...]]
    """
    keyboard = {
        "inline_keyboard": buttons
    }
    return json.dumps(keyboard)

def send_sticker(token, chat_id, sticker_id):
    params = {
        "chat_id": chat_id,
        "sticker": sticker_id
    }
    return api_call(token, "sendSticker", params)

def start_message(chat_id):
    text = (
        "👋 <b>Привет! Выберите валюту для учёта доходов и расходов:</b>"
    )
    buttons = [
        [{"text": "🇷🇺 RUB", "callback_data": "currency_RUB"},
         {"text": "🇺🇸 USD", "callback_data": "currency_USD"},
         {"text": "🇹🇲 TMT", "callback_data": "currency_TMT"}]
    ]
    reply_markup = build_inline_keyboard(buttons)
    send_message(TOKEN, chat_id, text, reply_markup)

def main():
    global offset
    global user_currency

    print("Bot started")
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
                text = message.get("text", "")

                # Если юзер еще не выбрал валюту — просим выбрать
                if chat_id not in user_currency and text == "/start":
                    start_message(chat_id)
                    continue

                # Если валюта выбрана, обрабатываем команды и кнопки
                if chat_id in user_currency:
                    # Здесь вызов твоей функции handle_message, передав валюту при необходимости
                    handle_message(message, user_currency[chat_id])
                else:
                    # Если пользователь пишет не /start и не выбрал валюту
                    send_message(TOKEN, chat_id, "Пожалуйста, выберите валюту командой /start.")

            elif "callback_query" in update:
                callback = update["callback_query"]
                data = callback["data"]
                chat_id = callback["message"]["chat"]["id"]

                if data.startswith("currency_"):
                    currency = data.split("_")[1]
                    user_currency[chat_id] = currency
                    send_message(TOKEN, chat_id, f"✅ Валюта установлена: {currency}")

                    # Отправляем стикер в зависимости от валюты
                    sticker_id = STICKERS.get(currency)
                    if sticker_id:
                        send_sticker(TOKEN, chat_id, sticker_id)

                    # Отправляем главное меню
                    text, reply_markup = start_message_text_and_keyboard()
                    send_message(TOKEN, chat_id, text, reply_markup)

def start_message_text_and_keyboard():
    text = (
        "👋 <b>Привет! Я твой трекер кошелька.</b>\n\n"
        "Выбери действие ниже или используй команды:\n"
        "/add_income — Добавить доход\n"
        "/add_expense — Добавить расход\n"
        "/balance — Показать баланс\n"
        "/report — Показать отчёт\n"
        "/categories — Расходы по категориям\n"
        "/support — Связь с админом"
    )
    buttons = [
        [{"text": "➕ Добавить доход"}, {"text": "➖ Добавить расход"}],
        [{"text": "💰 Баланс"}, {"text": "📊 Отчёт"}],
        [{"text": "📂 Категории"}, {"text": "📩 Связь с админом"}],
    ]
    reply_markup = json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": False
    })
    return text, reply_markup

def handle_message(message, currency):
    # Твой существующий handle_message с учетом валюты
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # Пример: добавим валюту в ответ
    if text == "/start":
        text, reply_markup = start_message_text_and_keyboard()
        send_message(TOKEN, chat_id, text, reply_markup)
        return

    # Остальная обработка с учетом currency...
    send_message(TOKEN, chat_id, f"Выбранная валюта: {currency}\nКоманда: {text}\n(Логика обработки здесь)")

if __name__ == "__main__":
    main()




