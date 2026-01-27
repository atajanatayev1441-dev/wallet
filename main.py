import json
import os
import time
from telegram_api import get_updates, send_message, send_sticker

TOKEN = os.getenv("BOT_TOKEN")

STATE_NONE = 0
STATE_ADD_INCOME_AMOUNT = 1
STATE_ADD_INCOME_CATEGORY = 2
STATE_ADD_EXPENSE_AMOUNT = 3
STATE_ADD_EXPENSE_CATEGORY = 4
STATE_ADMIN_BROADCAST = 5
STATE_CONTACT_ADMIN = 6
STATE_SELECT_CURRENCY = 7

ADMIN_ID = 123456789  # <- Впиши сюда свой Telegram ID

CURRENCIES = {
    "RUB": "₽",
    "USD": "$",
    "TMT": "T"
}

CURRENCY_STICKERS = {
    "RUB": "CAACAgIAAxkBAAEBHk1g5fRJPhGzWZ8d8mHYqYTtW8sGnAACFQADVp29CqaKWpG8qZOHgQ",
    "USD": "CAACAgIAAxkBAAEBHk9g5fSGQVkE-8dN7tj5yQBoD0xh4AACFgADVp29Cr8D45TfNYVTGgQ",
    "TMT": "CAACAgIAAxkBAAEBHlFg5fSLFxUwIS8CGzCJkAfN9HlLAQACFgADVp29CufvJ5-bQcXIGAQ"
}

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()

user_states = {}
temp_data = {}
currency_user = {}

def keyboard_main(is_admin=False):
    kb = {
        "keyboard": [
            ["➕ Добавить доход", "➖ Добавить расход"],
            ["📊 Отчет", "💰 Баланс"],
            ["✉️ Связь с админом"]
        ],
        "resize_keyboard": True
    }
    if is_admin:
        kb["keyboard"].append(["📣 Рассылка"])
    return kb

def keyboard_cancel():
    return {"keyboard": [["❌ Отмена"]], "resize_keyboard": True}

def keyboard_categories(categories):
    return {
        "keyboard": [[cat] for cat in categories] + [["❌ Отмена"]],
        "resize_keyboard": True
    }

def main():
    print("Бот запущен...")
    offset = 0
    while True:
        try:
            updates = get_updates(TOKEN, offset, timeout=20)
            for update in updates:
                offset = update["update_id"] + 1
                if "message" not in update:
                    continue
                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                is_admin = chat_id == ADMIN_ID

                if chat_id not in data["users"]:
                    data["users"][chat_id] = {
                        "income": [],
                        "expense": [],
                        "income_categories": ["Зарплата", "Подарки", "Другое"],
                        "expense_categories": ["Еда", "Транспорт", "Развлечения", "Другое"],
                        "currency": "RUB"
                    }
                    save_data(data)
                    currency_user[chat_id] = "RUB"
                else:
                    currency_user[chat_id] = data["users"][chat_id].get("currency", "RUB")

                state = user_states.get(chat_id, STATE_NONE)

                if text == "/start":
                    send_message(TOKEN, chat_id,
                                 f"👋 Привет, {message['from'].get('first_name', '')}!\n"
                                 f"Выбери валюту:",
                                 keyboard={
                                     "keyboard": [["RUB ₽", "USD $", "TMT T"]],
                                     "resize_keyboard": True
                                 })
                    user_states[chat_id] = STATE_SELECT_CURRENCY
                    continue

                if state == STATE_SELECT_CURRENCY:
                    if text in ["RUB ₽", "USD $", "TMT T"]:
                        cur = text.split()[0]
                        data["users"][chat_id]["currency"] = cur
                        save_data(data)
                        currency_user[chat_id] = cur
                        send_sticker(TOKEN, chat_id, CURRENCY_STICKERS[cur])
                        send_message(TOKEN, chat_id,
                                     f"Валюта установлена: {cur} {CURRENCIES[cur]}",
                                     keyboard_main(is_admin))
                        user_states[chat_id] = STATE_NONE
                    elif text == "❌ Отмена":
                        send_message(TOKEN, chat_id, "Отмена выбора валюты.", keyboard_main(is_admin))
                        user_states[chat_id] = STATE_NONE
                    else:
                        send_message(TOKEN, chat_id, "Пожалуйста, выберите валюту кнопками.")
                    continue

                if text == "❌ Отмена":
                    send_message(TOKEN, chat_id, "Действие отменено.", keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    temp_data.pop(chat_id, None)
                    continue

                if text == "➕ Добавить доход" and state == STATE_NONE:
                    send_message(TOKEN, chat_id, "Введите сумму дохода:", keyboard_cancel())
                    user_states[chat_id] = STATE_ADD_INCOME_AMOUNT
                    continue

                if state == STATE_ADD_INCOME_AMOUNT:
                    try:
                        amount = float(text.replace(",", "."))
                        if amount <= 0:
                            raise ValueError
                        temp_data[chat_id] = {"amount": amount}
                        categories = data["users"][chat_id]["income_categories"]
                        send_message(TOKEN, chat_id, "Выберите категорию дохода или введите новую:", keyboard_categories(categories))
                        user_states[chat_id] = STATE_ADD_INCOME_CATEGORY
                    except ValueError:
                        send_message(TOKEN, chat_id, "Введите корректное положительное число.")
                    continue

                if state == STATE_ADD_INCOME_CATEGORY:
                    cat = text.strip()
                    if cat == "❌ Отмена":
                        send_message(TOKEN, chat_id, "Действие отменено.", keyboard_main(is_admin))
                        user_states[chat_id] = STATE_NONE
                        temp_data.pop(chat_id, None)
                        continue
                    if cat not in data["users"][chat_id]["income_categories"]:
                        data["users"][chat_id]["income_categories"].append(cat)
                        save_data(data)
                    amount = temp_data[chat_id]["amount"]
                    data["users"][chat_id]["income"].append({"amount": amount, "category": cat, "timestamp": int(time.time())})
                    save_data(data)
                    send_message(TOKEN, chat_id, f"✅ Доход {amount} {CURRENCIES[currency_user[chat_id]]} в категории '{cat}' добавлен.", keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    temp_data.pop(chat_id, None)
                    continue

                if text == "➖ Добавить расход" and state == STATE_NONE:
                    send_message(TOKEN, chat_id, "Введите сумму расхода:", keyboard_cancel())
                    user_states[chat_id] = STATE_ADD_EXPENSE_AMOUNT
                    continue

                if state == STATE_ADD_EXPENSE_AMOUNT:
                    try:
                        amount = float(text.replace(",", "."))
                        if amount <= 0:
                            raise ValueError
                        temp_data[chat_id] = {"amount": amount}
                        categories = data["users"][chat_id]["expense_categories"]
                        send_message(TOKEN, chat_id, "Выберите категорию расхода или введите новую:", keyboard_categories(categories))
                        user_states[chat_id] = STATE_ADD_EXPENSE_CATEGORY
                    except ValueError:
                        send_message(TOKEN, chat_id, "Введите корректное положительное число.")
                    continue

                if state == STATE_ADD_EXPENSE_CATEGORY:
                    cat = text.strip()
                    if cat == "❌ Отмена":
                        send_message(TOKEN, chat_id, "Действие отменено.", keyboard_main(is_admin))
                        user_states[chat_id] = STATE_NONE
                        temp_data.pop(chat_id, None)
                        continue
                    if cat not in data["users"][chat_id]["expense_categories"]:
                        data["users"][chat_id]["expense_categories"].append(cat)
                        save_data(data)
                    amount = temp_data[chat_id]["amount"]
                    data["users"][chat_id]["expense"].append({"amount": amount, "category": cat, "timestamp": int(time.time())})
                    save_data(data)
                    send_message(TOKEN, chat_id, f"✅ Расход {amount} {CURRENCIES[currency_user[chat_id]]} в категории '{cat}' добавлен.", keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    temp_data.pop(chat_id, None)
                    continue

                if text == "📊 Отчет":
                    user = data["users"][chat_id]
                    income_total = sum(i["amount"] for i in user["income"])
                    expense_total = sum(e["amount"] for e in user["expense"])
                    cur = currency_user[chat_id]
                    cur_sign = CURRENCIES[cur]
                    report = (f"📊 Отчет по финансам:\n\n"
                              f"💵 Доходы: {income_total:.2f} {cur_sign}\n"
                              f"💸 Расходы: {expense_total:.2f} {cur_sign}\n"
                              f"----------------------\n"
                              f"💰 Баланс: {(income_total - expense_total):.2f} {cur_sign}\n\n"
                              f"Категории доходов:\n" +
                              "\n".join(f"- {cat}" for cat in user["income_categories"]) + "\n\n" +
                              f"Категории расходов:\n" +
                              "\n".join(f"- {cat}" for cat in user["expense_categories"]))
                    send_message(TOKEN, chat_id, report, keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    continue

                if text == "💰 Баланс":
                    user = data["users"][chat_id]
                    income_total = sum(i["amount"] for i in user["income"])
                    expense_total = sum(e["amount"] for e in user["expense"])
                    cur = currency_user[chat_id]
                    cur_sign = CURRENCIES[cur]
                    balance = income_total - expense_total
                    balance_msg = (f"💰 Ваш текущий баланс:\n\n"
                                   f"Доходы: {income_total:.2f} {cur_sign}\n"
                                   f"Расходы: {expense_total:.2f} {cur_sign}\n"
                                   f"-------------------------\n"
                                   f"<b>Баланс: {balance:.2f} {cur_sign}</b>")
                    send_message(TOKEN, chat_id, balance_msg, keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    continue

                if text == "✉️ Связь с админом":
                    send_message(TOKEN, chat_id, "Напишите сообщение для администратора:", keyboard_cancel())
                    user_states[chat_id] = STATE_CONTACT_ADMIN
                    continue

                if state == STATE_CONTACT_ADMIN:
                    admin_message = (f"📩 Сообщение от пользователя <b>{message['from'].get('first_name', '')} "
                                     f"(@{message['from'].get('username', '')})</b>:\n\n{text}")
                    send_message(TOKEN, ADMIN_ID, admin_message)
                    send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.", keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    continue

                if is_admin and text == "📣 Рассылка":
                    send_message(TOKEN, chat_id, "Введите сообщение для рассылки всем пользователям:", keyboard_cancel())
                    user_states[chat_id] = STATE_ADMIN_BROADCAST
                    continue

                if state == STATE_ADMIN_BROADCAST and is_admin:
                    for user_id in data["users"].keys():
                        send_message(TOKEN, user_id, f"📢 Сообщение от администратора:\n\n{text}")
                    send_message(TOKEN, chat_id, "✅ Сообщение отправлено всем пользователям.", keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    continue

                if state == STATE_NONE:
                    send_message(TOKEN, chat_id, "Пожалуйста, выберите действие с помощью кнопок.", keyboard_main(is_admin))

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
