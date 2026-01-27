import os
import time
import json
from telegram_api import send_message, get_updates, api_call

ADMIN_ID = 8283258905  # Замените на свой ID админа

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Set it in environment variables.")

offset = 0

user_currency = {}  # chat_id -> валюта (RUB/USD/TMT)
user_states = {}    # chat_id -> состояние диалога (словарь)

STICKERS = {
    "RUB": "CAACAgIAAxkBAAIBHmHqg6R7_R8US-V7C1d27gU8RxFwAAKdBAACGhTgSvhN14Xw45bsLwQ",
    "USD": "CAACAgIAAxkBAAIBIGHqg67DxFjkDTr6ZAmvsk2yk-6WAAJhBAACGhTgSn1DrRzknzxVvLwQ",
    "TMT": "CAACAgIAAxkBAAIBIWHqg6eX6aHYo2ycbVjL8DkQwFtuAAJfBAACGhTgSnESevjE6ivF4LwQ"
}

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

def main_menu_text_and_keyboard():
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
    reply_markup = json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": False
    })
    return text, reply_markup

def handle_message(message, currency):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    state = user_states.get(chat_id)

    if text == "/start":
        reset_state(chat_id)
        if chat_id not in user_currency:
            start_message(chat_id)
        else:
            text, reply_markup = main_menu_text_and_keyboard()
            send_message(TOKEN, chat_id, text, reply_markup)
        return

    if state:
        if state['action'] == 'add_income':
            if state['step'] == 1:
                try:
                    amount = float(text.replace(",", "."))
                    if amount <= 0:
                        raise ValueError
                    user_states[chat_id]['amount'] = amount
                    user_states[chat_id]['step'] = 2
                    send_message(TOKEN, chat_id, "Введите источник дохода (например, зарплата, подарок):")
                except ValueError:
                    send_message(TOKEN, chat_id, "❗ Введите корректную положительную сумму.")
                return
            elif state['step'] == 2:
                source = text
                amount = user_states[chat_id]['amount']
                from wallet import WalletManager
                wallet = WalletManager("data.json")
                wallet.add_income(amount, source)
                send_message(TOKEN, chat_id, f"💰 Доход +{amount} {currency} добавлен.\nИсточник: {source}")
                reset_state(chat_id)
                return

        elif state['action'] == 'add_expense':
            if state['step'] == 1:
                try:
                    amount = float(text.replace(",", "."))
                    if amount <= 0:
                        raise ValueError
                    user_states[chat_id]['amount'] = amount
                    user_states[chat_id]['step'] = 2
                    send_message(TOKEN, chat_id, "Введите категорию расхода (например, еда, транспорт):")
                except ValueError:
                    send_message(TOKEN, chat_id, "❗ Введите корректную положительную сумму.")
                return
            elif state['step'] == 2:
                category = text
                user_states[chat_id]['category'] = category
                user_states[chat_id]['step'] = 3
                send_message(TOKEN, chat_id, "Введите комментарий к расходу (можно оставить пустым):")
                return
            elif state['step'] == 3:
                comment = text
                amount = user_states[chat_id]['amount']
                category = user_states[chat_id]['category']
                from wallet import WalletManager
                wallet = WalletManager("data.json")
                wallet.add_expense(amount, category, comment)
                send_message(TOKEN, chat_id, f"🛒 Расход -{amount} {currency} добавлен.\nКатегория: {category}\nКомментарий: {comment if comment else '-'}")
                reset_state(chat_id)
                return

        elif state['action'] == 'support':
            support_msg = text
            send_message(TOKEN, ADMIN_ID, f"📩 Сообщение от пользователя {chat_id}:\n{support_msg}")
            send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.")
            reset_state(chat_id)
            return

    # Если пользователь не в диалоге - реагируем на команды и кнопки
    if text in ("➕ Добавить доход", "/add_income"):
        user_states[chat_id] = {'action': 'add_income', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму дохода:")
        return

    if text in ("➖ Добавить расход", "/add_expense"):
        user_states[chat_id] = {'action': 'add_expense', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму расхода:")
        return

    if text in ("💰 Баланс", "/balance"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        balance, total_income, total_expense = wallet.get_balance()
        send_message(TOKEN, chat_id,
                     f"🏦 Текущий баланс: <b>{balance:.2f} {currency}</b>\n"
                     f"Доходы: {total_income:.2f} {currency}\n"
                     f"Расходы: {total_expense:.2f} {currency}")
        return

    if text in ("📊 Отчёт", "/report"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        report = wallet.get_report()
        send_message(TOKEN, chat_id, report)
        return

    if text in ("📂 Категории", "/categories"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        categories_report = wallet.get_categories_report()
        send_message(TOKEN, chat_id, categories_report)
        return

    if text in ("📩 Связь с админом", "/support"):
        user_states[chat_id] = {'action': 'support'}
        send_message(TOKEN, chat_id, "📝 Напишите ваше сообщение для администратора:")
        return

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

                if chat_id not in user_currency:
                    # Предлагаем выбрать валюту при первом запуске
                    start_message(chat_id)
                    user_currency[chat_id] = None  # Ждем выбора валюты
                    continue

                if user_currency[chat_id] is None:
                    send_message(TOKEN, chat_id, "Пожалуйста, выберите валюту через /start.")
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

                    text, reply_markup = main_menu_text_and_keyboard()
                    send_message(TOKEN, chat_id, text, reply_markup)

if __name__ == "__main__":
    main()
