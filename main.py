# main.py
import os
import time

from telegram_api import get_updates, send_message
from storage import ensure_storage, load, save, USERS, STATES, add_transaction
from wallet import get_balance, report_by_category

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

MAIN_MENU = {
    "keyboard": [
        ["➕ Доход", "➖ Расход"],
        ["📊 Отчёт", "💰 Баланс"],
        ["📩 Админу"]
    ],
    "resize_keyboard": True
}

CANCEL_MENU = {
    "keyboard": [["❌ Отменить"]],
    "resize_keyboard": True
}

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN not set")

    ensure_storage()
    offset = 0

    while True:
        updates = get_updates(TOKEN, offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" not in update:
                continue

            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            users = load(USERS)
            states = load(STATES)

            if str(chat_id) not in users:
                users[str(chat_id)] = {
                    "currency": None,
                    "temp_amount": None
                }
                save(USERS, users)

            state = states.get(str(chat_id))

            if text == "/start":
                send_message(
                    TOKEN,
                    chat_id,
                    "Выберите валюту:",
                    {"keyboard": [["RUB", "USD", "TMT"]], "resize_keyboard": True}
                )
                states[str(chat_id)] = "currency"
                save(STATES, states)
                continue

            if state == "currency":
                users[str(chat_id)]["currency"] = text
                save(USERS, users)
                states.pop(str(chat_id))
                save(STATES, states)
                send_message(TOKEN, chat_id, "Готово! Главное меню:", MAIN_MENU)
                continue

            if text == "➕ Доход":
                states[str(chat_id)] = "income_amount"
                save(STATES, states)
                send_message(TOKEN, chat_id, "Введите сумму дохода:", CANCEL_MENU)
                continue

            if text == "➖ Расход":
                states[str(chat_id)] = "expense_amount"
                save(STATES, states)
                send_message(TOKEN, chat_id, "Введите сумму расхода:", CANCEL_MENU)
                continue

            if text == "❌ Отменить":
                states.pop(str(chat_id), None)
                save(STATES, states)
                send_message(TOKEN, chat_id, "Действие отменено.", MAIN_MENU)
                continue

            if state in ("income_amount", "expense_amount"):
                try:
                    amount = float(text)
                except:
                    send_message(TOKEN, chat_id, "Введите число")
                    continue

                users[str(chat_id)]["temp_amount"] = amount
                save(USERS, users)
                states[str(chat_id)] = "category_" + state.split("_")[0]
                save(STATES, states)
                send_message(TOKEN, chat_id, "Введите категорию:")
                continue

            if state in ("category_income", "category_expense"):
                kind = "income" if "income" in state else "expense"
                amount = users[str(chat_id)].pop("temp_amount")
                add_transaction(chat_id, kind, amount, text)
                save(USERS, users)
                states.pop(str(chat_id))
                save(STATES, states)
                send_message(TOKEN, chat_id, "Готово ✅", MAIN_MENU)
                continue

            if text == "💰 Баланс":
                inc, exp, bal = get_balance(chat_id)
                cur = users[str(chat_id)]["currency"]
                send_message(
                    TOKEN,
                    chat_id,
                    f"Доход: {inc}\nРасход: {exp}\nБаланс: {bal} {cur}",
                    MAIN_MENU
                )
                continue

            if text == "📊 Отчёт":
                data = report_by_category(chat_id, "expense")
                if not data:
                    send_message(TOKEN, chat_id, "Нет данных", MAIN_MENU)
                else:
                    msg = "Расходы по категориям:\n"
                    for k, v in data.items():
                        msg += f"• {k}: {v}\n"
                    send_message(TOKEN, chat_id, msg, MAIN_MENU)
                continue

            if text == "📩 Админу":
                states[str(chat_id)] = "to_admin"
                save(STATES, states)
                send_message(TOKEN, chat_id, "Напишите сообщение администратору:", CANCEL_MENU)
                continue

            if state == "to_admin" and ADMIN_ID:
                send_message(TOKEN, ADMIN_ID, f"Сообщение от {chat_id}:\n{text}")
                states.pop(str(chat_id))
                save(STATES, states)
                send_message(TOKEN, chat_id, "Сообщение отправлено", MAIN_MENU)

        time.sleep(0.3)

if __name__ == "__main__":
    main()
