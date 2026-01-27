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

# Состояния пользователя для диалогов
user_states = {}  # chat_id -> dict с текущим состоянием, например {'action': 'add_income', 'step': 1, ...}

def reset_state(chat_id):
    if chat_id in user_states:
        del user_states[chat_id]

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
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # Проверяем, в каком состоянии пользователь
    state = user_states.get(chat_id)

    if text == "/start":
        reset_state(chat_id)
        text, reply_markup = start_message_text_and_keyboard()
        send_message(TOKEN, chat_id, text, reply_markup)
        return

    if state:
        # Пользователь в процессе ввода дохода/расхода
        if state['action'] == 'add_income':
            if state['step'] == 1:
                # Получили сумму
                try:
                    amount = float(text.replace(",", "."))
                    if amount <= 0:
                        raise ValueError
                    user_states[chat_id]['amount'] = amount
                    user_states[chat_id]['step'] = 2
                    send_message(TOKEN, chat_id, "Введите источник дохода (например, зарплата, подарок):")
                except ValueError:
                    send_message(TOKEN, chat_id, "❗ Пожалуйста, введите корректную положительную сумму.")
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
                    send_message(TOKEN, chat_id, "❗ Пожалуйста, введите корректную положительную сумму.")
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

    # Если пользователь не в диалоге — обработка команд и кнопок
    if text == "➕ Добавить доход" or text.startswith("/add_income"):
        user_states[chat_id] = {'action': 'add_income', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму дохода:")
        return

    if text == "➖ Добавить расход" or text.startswith("/add_expense"):
        user_states[chat_id] = {'action': 'add_expense', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму расхода:")
        return

    if text == "💰 Баланс" or text.startswith("/balance"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        balance, total_income, total_expense = wallet.get_balance()
        send_message(TOKEN, chat_id,
                     f"🏦 Текущий баланс: <b>{balance:.2f} {currency}</b>\n"
                     f"Доходы: {total_income:.2f} {currency}\n"
                     f"Расходы: {total_expense:.2f} {currency}")
        return

    if text == "📊 Отчёт" or text.startswith("/report"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        report = wallet.get_report()
        send_message(TOKEN, chat_id, report)
        return

    if text == "📂 Категории" or text.startswith("/categories"):
        from wallet import WalletManager
        wallet = WalletManager("data.json")
        categories_report = wallet.get_categories_report()
        send_message(TOKEN, chat_id, categories_report)
        return

    if text == "📩 Связь с админом" or text.startswith("/support"):
        send_message(TOKEN, chat_id,
                     "Напишите сообщение после команды /support, и оно будет отправлено администратору.")
        return

    if text.startswith("/support"):
        support_msg = text[len("/support"):].strip()
        if not support_msg:
            send_message(TOKEN, chat_id, "❗ Напишите сообщение после команды /support")
            return
        send_message(TOKEN, ADMIN_ID, f"📩 Сообщение от пользователя {chat_id}:\n{support_msg}")
        send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.")
        return

    send_message(TOKEN, chat_id, "❓ Неизвестная команда. Напишите /start для начала.")

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

                # Проверяем валюту для пользователя
                if chat_id not in user_currency:
                    # Можно использовать дефолтную валюту, например RUB
                    user_currency[chat_id] = "RUB"

                handle_message(message, user_currency[chat_id])

            elif "callback_query" in update:
                # Обработка callback_query, если есть (например, для выбора валюты)
                pass

if __name__ == "__main__":
    main()
