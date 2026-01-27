import os
import time
import json
from telegram_api import get_updates, send_message

# ====== НАСТРОЙКИ ======
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8283258905  # <-- ТУТ ВПИШИ СВОЙ ID
DATA_FILE = "data.json"

# ====== СОСТОЯНИЯ ======
STATE_NONE = "none"
STATE_WAIT_INCOME_SUM = "wait_income_sum"
STATE_WAIT_INCOME_CAT = "wait_income_cat"
STATE_WAIT_EXPENSE_SUM = "wait_expense_sum"
STATE_WAIT_EXPENSE_CAT = "wait_expense_cat"
STATE_SUPPORT = "support"
STATE_BROADCAST = "broadcast"
STATE_ADD_CAT = "add_category"
STATE_CHOOSE_CURRENCY = "choose_currency"
STATE_REPORT_PERIOD = "report_period"

# ====== ГЛОБАЛЬНЫЕ ======
user_states = {}
user_temp = {}
users = set()
data = {}

# ====== ВАЛЮТЫ ======
CURRENCIES = {
    "RUB": "₽",
    "USD": "$",
    "TMT": "T"
}
currency_user = {}

# ====== ЗАГРУЗКА/СОХРАНЕНИЕ ДАННЫХ ======
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "users": {},
            "categories": {
                "income": ["Зарплата", "Подарок", "Другое"],
                "expense": ["Еда", "Транспорт", "Развлечения", "Другое"]
            }
        }

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ====== КНОПКИ ======
def keyboard_main(is_admin=False):
    kb = {
        "keyboard": [
            ["➕ Добавить доход", "➖ Добавить расход"],
            ["📊 Отчет", "✉️ Связь с админом"]
        ],
        "resize_keyboard": True
    }
    if is_admin:
        kb["keyboard"].append(["📣 Рассылка"])
    return kb

def keyboard_categories(cat_type):
    cats = data["categories"][cat_type]
    kb = {
        "keyboard": [[cat] for cat in cats] + [["➕ Добавить категорию"], ["⬅️ Вернуться в меню"]],
        "resize_keyboard": True
    }
    return kb

def keyboard_report_period():
    kb = {
        "keyboard": [
            ["Сегодня", "Неделя", "Месяц"],
            ["⬅️ Вернуться в меню"]
        ],
        "resize_keyboard": True
    }
    return kb

def get_currency_keyboard():
    kb = {
        "keyboard": [
            ["🇷🇺 RUB ₽"],
            ["🇺🇸 USD $"],
            ["🇹🇲 TMT T"]
        ],
        "resize_keyboard": True
    }
    return kb

# ====== ОСНОВНОЙ ЦИКЛ ======
def main():
    load_data()
    offset = 0

    while True:
        updates = get_updates(TOKEN, offset)
        for upd in updates:
            offset = upd["update_id"] + 1
            message = upd.get("message")
            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            users.add(chat_id)
            is_admin = chat_id == ADMIN_ID
            state = user_states.get(chat_id, STATE_NONE)

            # Установить валюту по умолчанию, если не выбрана
            if chat_id not in currency_user:
                currency_user[chat_id] = None

            # --- /start ---
            if text == "/start":
                user_states[chat_id] = STATE_CHOOSE_CURRENCY
                send_message(TOKEN, chat_id,
                             "👋 <b>Добро пожаловать!</b>\nВыберите валюту для учета:",
                             get_currency_keyboard())
                continue

            # --- Выбор валюты ---
            if state == STATE_CHOOSE_CURRENCY:
                selected = None
                for cur in CURRENCIES.keys():
                    if cur in text:
                        selected = cur
                        break
                if selected:
                    currency_user[chat_id] = selected
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id,
                                 f"Вы выбрали валюту <b>{selected} {CURRENCIES[selected]}</b>.\n\n"
                                 "Теперь вы можете добавлять доходы и расходы.",
                                 keyboard_main(is_admin))
                else:
                    send_message(TOKEN, chat_id,
                                 "Пожалуйста, выберите валюту с помощью кнопок ниже.",
                                 get_currency_keyboard())
                continue

            # --- Вернуться в меню ---
            if text == "⬅️ Вернуться в меню":
                user_states[chat_id] = STATE_NONE
                send_message(TOKEN, chat_id, "Главное меню:", keyboard_main(is_admin))
                continue

            # --- Добавить доход ---
            if text == "➕ Добавить доход":
                if currency_user.get(chat_id) is None:
                    send_message(TOKEN, chat_id, "Сначала выберите валюту командой /start.")
                    continue
                user_states[chat_id] = STATE_WAIT_INCOME_SUM
                send_message(TOKEN, chat_id,
                             f"Введите сумму дохода в {currency_user[chat_id]} {CURRENCIES[currency_user[chat_id]]} или '⬅️ Вернуться в меню':")
                continue

            if state == STATE_WAIT_INCOME_SUM:
                if text == "⬅️ Вернуться в меню":
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id, "Отмена. Главное меню:", keyboard_main(is_admin))
                    continue
                try:
                    sum_income = float(text.replace(',', '.'))
                    if sum_income <= 0:
                        raise ValueError
                    user_temp[chat_id] = {"sum": sum_income}
                    user_states[chat_id] = STATE_WAIT_INCOME_CAT
                    send_message(TOKEN, chat_id, "Выберите категорию дохода или добавьте новую:", keyboard_categories("income"))
                except ValueError:
                    send_message(TOKEN, chat_id, "Ошибка! Введите положительное число.")
                continue

            if state == STATE_WAIT_INCOME_CAT:
                if text == "⬅️ Вернуться в меню":
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id, "Отмена. Главное меню:", keyboard_main(is_admin))
                    continue
                if text == "➕ Добавить категорию":
                    user_states[chat_id] = STATE_ADD_CAT
                    user_temp[chat_id]["type"] = "income"
                    send_message(TOKEN, chat_id, "Введите название новой категории дохода:")
                    continue
                if text in data["categories"]["income"]:
                    sum_income = user_temp[chat_id]["sum"]
                    add_transaction(chat_id, sum_income, text, "income")
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id,
                                 f"✅ Добавлен доход: {sum_income} {CURRENCIES[currency_user[chat_id]]} в категорию <b>{text}</b>.",
                                 keyboard_main(is_admin))
                else:
                    send_message(TOKEN, chat_id, "Выберите категорию из списка или добавьте новую.")
                continue

            # --- Добавить расход ---
            if text == "➖ Добавить расход":
                if currency_user.get(chat_id) is None:
                    send_message(TOKEN, chat_id, "Сначала выберите валюту командой /start.")
                    continue
                user_states[chat_id] = STATE_WAIT_EXPENSE_SUM
                send_message(TOKEN, chat_id,
                             f"Введите сумму расхода в {currency_user[chat_id]} {CURRENCIES[currency_user[chat_id]]} или '⬅️ Вернуться в меню':")
                continue

            if state == STATE_WAIT_EXPENSE_SUM:
                if text == "⬅️ Вернуться в меню":
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id, "Отмена. Главное меню:", keyboard_main(is_admin))
                    continue
                try:
                    sum_expense = float(text.replace(',', '.'))
                    if sum_expense <= 0:
                        raise ValueError
                    user_temp[chat_id] = {"sum": sum_expense}
                    user_states[chat_id] = STATE_WAIT_EXPENSE_CAT
                    send_message(TOKEN, chat_id, "Выберите категорию расхода или добавьте новую:", keyboard_categories("expense"))
                except ValueError:
                    send_message(TOKEN, chat_id, "Ошибка! Введите положительное число.")
                continue

            if state == STATE_WAIT_EXPENSE_CAT:
                if text == "⬅️ Вернуться в меню":
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id, "Отмена. Главное меню:", keyboard_main(is_admin))
                    continue
                if text == "➕ Добавить категорию":
                    user_states[chat_id] = STATE_ADD_CAT
                    user_temp[chat_id]["type"] = "expense"
                    send_message(TOKEN, chat_id, "Введите название новой категории расхода:")
                    continue
                if text in data["categories"]["expense"]:
                    sum_expense = user_temp[chat_id]["sum"]
                    add_transaction(chat_id, sum_expense, text, "expense")
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id,
                                 f"✅ Добавлен расход: {sum_expense} {CURRENCIES[currency_user[chat_id]]} в категорию <b>{text}</b>.",
                                 keyboard_main(is_admin))
                else:
                    send_message(TOKEN, chat_id, "Выберите категорию из списка или добавьте новую.")
                continue

            # --- Добавление категории ---
            if state == STATE_ADD_CAT:
                new_cat = text.strip()
                cat_type = user_temp.get(chat_id, {}).get("type")
                if not cat_type:
                    send_message(TOKEN, chat_id, "Ошибка. Попробуйте снова.")
                    user_states[chat_id] = STATE_NONE
                    continue
                if new_cat == "" or new_cat in data["categories"][cat_type]:
                    send_message(TOKEN, chat_id, "Неверное или уже существующее название категории, попробуйте другое:")
                    continue
                data["categories"][cat_type].append(new_cat)
                save_data()
                send_message(TOKEN, chat_id, f"✅ Категория <b>{new_cat}</b> добавлена в {cat_type}. Выберите категорию из списка:", keyboard_categories(cat_type))
                if cat_type == "income":
                    user_states[chat_id] = STATE_WAIT_INCOME_CAT
                else:
                    user_states[chat_id] = STATE_WAIT_EXPENSE_CAT
                continue

            # --- Отчет ---
            if text == "📊 Отчет":
                user_states[chat_id] = STATE_REPORT_PERIOD
                send_message(TOKEN, chat_id, "Выберите период отчета:", keyboard_report_period())
                continue

            if state == STATE_REPORT_PERIOD:
                if text == "⬅️ Вернуться в меню":
                    user_states[chat_id] = STATE_NONE
                    send_message(TOKEN, chat_id, "Главное меню:", keyboard_main(is_admin))
                    continue
                if text in ["Сегодня", "Неделя", "Месяц"]:
                    report = generate_report(chat_id, text)
                    send_message(TOKEN, chat_id, report, keyboard_main(is_admin))
                    user_states[chat_id] = STATE_NONE
                    continue
                send_message(TOKEN, chat_id, "Выберите период из списка или вернитесь в меню.")
                continue

            # --- Связь с админом ---
            if text == "✉️ Связь с админом":
                user_states[chat_id] = STATE_SUPPORT
                send_message(TOKEN, chat_id, "Напишите сообщение админу:")
                continue

            if state == STATE_SUPPORT:
                send_message(TOKEN, ADMIN_ID,
                             f"📩 <b>Сообщение от пользователя</b> 🆔{chat_id}\n\n{text}")
                send_message(TOKEN, chat_id, "Сообщение отправлено администратору.", keyboard_main(is_admin))
                user_states[chat_id] = STATE_NONE
                continue

            # --- Рассылка (админ) ---
            if text == "📣 Рассылка" and is_admin:
                user_states[chat_id] = STATE_BROADCAST
                send_message(TOKEN, chat_id, "Введите текст для рассылки:")
                continue

            if state == STATE_BROADCAST and is_admin:
                for u in users:
                    send_message(TOKEN, u, f"📢 <b>Сообщение от администратора:</b>\n\n{text}")
                send_message(TOKEN, chat_id, "Рассылка отправлена.", keyboard_main(is_admin))
                user_states[chat_id] = STATE_NONE
                continue

            # --- Неизвестная команда ---
            send_message(TOKEN, chat_id, "Неизвестная команда или сообщение. Используйте меню ниже.", keyboard_main(is_admin))

        time.sleep(1)

# ====== ФУНКЦИИ ======
def add_transaction(user_id, amount, category, ttype):
    user_data = data["users"].setdefault(str(user_id), {"income": [], "expense": []})
    user_data[ttype].append({
        "amount": amount,
        "category": category,
        "timestamp": int(time.time())
    })
    save_data()

def generate_report(user_id, period):
    import datetime
    now = datetime.datetime.now()
    user_data = data["users"].get(str(user_id), {"income": [], "expense": []})
    incomes = user_data.get("income", [])
    expenses = user_data.get("expense", [])

    # Определяем границу времени
    if period == "Сегодня":
        start_ts = int(datetime.datetime(now.year, now.month, now.day).timestamp())
    elif period == "Неделя":
        start_ts = int((now - datetime.timedelta(days=7)).timestamp())
    elif period == "Месяц":
        start_ts = int((now - datetime.timedelta(days=30)).timestamp())
    else:
        return "Неизвестный период."

    filtered_inc = [i for i in incomes if i["timestamp"] >= start_ts]
    filtered_exp = [e for e in expenses if e["timestamp"] >= start_ts]

    # Суммируем по категориям
    def sum_by_category(items):
        result = {}
        for item in items:
            cat = item["category"]
            result[cat] = result.get(cat, 0) + item["amount"]
        return result

    inc_sum = sum_by_category(filtered_inc)
    exp_sum = sum_by_category(filtered_exp)

    total_inc = sum(inc_sum.values())
    total_exp = sum(exp_sum.values())
    balance = total_inc - total_exp

    cur = currency_user.get(user_id, "RUB")
    cur_sign = CURRENCIES.get(cur, "₽")

    report = f"<b>Отчет за {period}</b>\n\n"
    report += f"💵 <b>Доходы:</b> {total_inc:.2f} {cur_sign}\n"
    for cat, val in inc_sum.items():
        report += f"  - {cat}: {val:.2f} {cur_sign}\n"
    report += f"\n💸 <b>Расходы:</b> {total_exp:.2f} {cur_sign}\n"
    for cat, val in exp_sum.items():
        report += f"  - {cat}: {val:.2f} {cur_sign}\n"
    report += f"\n<b>Баланс:</b> {balance:.2f} {cur_sign}\n"

    return report


if __name__ == "__main__":
    main()
