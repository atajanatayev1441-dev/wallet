import os
import time
import threading
from telegram_api import send_message, get_updates
from wallet import WalletManager

ADMIN_ID = 8283258905  # Telegram ID админа, чтобы пересылать сообщения поддержки

TOKEN = os.getenv("8263345320:AAFr3_tHDhX_x0eNywQkq-SCXBTQG7avYvk")
if not TOKEN:
    raise RuntimeError("8263345320:AAFr3_tHDhX_x0eNywQkq-SCXBTQG7avYvk is not set. Set it in Railway Variables or environment.")

wallet = WalletManager("data.json")
offset = 0

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    if not text:
        return

    if text.startswith("/start"):
        send_message(TOKEN, chat_id,
                     "👋 Привет! Я твой личный трекер кошелька.\n\n"
                     "💰 Команды:\n"
                     "/add_income сумма источник\n"
                     "/add_expense сумма категория комментарий\n"
                     "/balance\n"
                     "/report\n"
                     "/categories\n"
                     "/help\n"
                     "/support текст_сообщения - отправить сообщение админу")
        return

    if text.startswith("/help"):
        send_message(TOKEN, chat_id,
                     "📋 Команды:\n"
                     "/add_income сумма источник - добавить доход\n"
                     "/add_expense сумма категория комментарий - добавить расход\n"
                     "/balance - показать баланс\n"
                     "/report - показать отчёт\n"
                     "/categories - показать расходы по категориям\n"
                     "/support текст - написать админу")
        return

    if text.startswith("/add_income"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(TOKEN, chat_id, "❗ Формат: /add_income сумма источник")
            return
        try:
            amount = float(parts[1])
            source = parts[2]
        except ValueError:
            send_message(TOKEN, chat_id, "❗ Сумма должна быть числом")
            return
        wallet.add_income(amount, source)
        send_message(TOKEN, chat_id, f"💰 Доход +{amount} руб. добавлен.\nИсточник: {source}")
        return

    if text.startswith("/add_expense"):
        parts = text.split(maxsplit=3)
        if len(parts) < 4:
            send_message(TOKEN, chat_id, "❗ Формат: /add_expense сумма категория комментарий")
            return
        try:
            amount = float(parts[1])
            category = parts[2]
            comment = parts[3]
        except ValueError:
            send_message(TOKEN, chat_id, "❗ Сумма должна быть числом")
            return
        wallet.add_expense(amount, category, comment)
        send_message(TOKEN, chat_id, f"🛒 Расход -{amount} руб. добавлен.\nКатегория: {category}\nКомментарий: {comment}")
        return

    if text.startswith("/balance"):
        balance, total_income, total_expense = wallet.get_balance()
        send_message(TOKEN, chat_id,
                     f"🏦 Текущий баланс: {balance:.2f} руб.\n"
                     f"Доходы: {total_income:.2f} руб.\n"
                     f"Расходы: {total_expense:.2f} руб.")
        return

    if text.startswith("/report"):
        report = wallet.get_report()
        send_message(TOKEN, chat_id, report)
        return

    if text.startswith("/categories"):
        categories_report = wallet.get_categories_report()
        send_message(TOKEN, chat_id, categories_report)
        return

    if text.startswith("/support"):
        support_msg = text[len("/support"):].strip()
        if not support_msg:
            send_message(TOKEN, chat_id, "❗ Напишите сообщение после команды /support")
            return
        send_message(TOKEN, ADMIN_ID, f"📩 Сообщение от пользователя {chat_id}:\n{support_msg}")
        send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.")
        return

    send_message(TOKEN, chat_id, "❓ Неизвестная команда. Напишите /help для списка команд.")

def main_loop():
    global offset
    while True:
        updates = get_updates(TOKEN, offset)
        if not updates:
            time.sleep(1)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                handle_message(update["message"])

def main():
    print("Bot started")
    main_loop()

if __name__ == "__main__":
    main()


