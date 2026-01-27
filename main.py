import json
import os
import time
from telegram_api import get_updates, send_message

TOKEN = os.getenv("BOT_TOKEN")  # Вставь сюда свой токен или используй переменную окружения
ADMIN_ID = 8283258905  # Твой Telegram ID

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TX_FILE = os.path.join(DATA_DIR, "transactions.json")
STATE_FILE = os.path.join(DATA_DIR, "states.json")

def ensure_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    for f in [USERS_FILE, TX_FILE, STATE_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as file:
                if f == TX_FILE:
                    file.write("[]")
                else:
                    file.write("{}")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(chat_id):
    users = load_json(USERS_FILE)
    return users.get(str(chat_id))

def save_user(chat_id, user_data):
    users = load_json(USERS_FILE)
    users[str(chat_id)] = user_data
    save_json(USERS_FILE, users)

def get_state(chat_id):
    states = load_json(STATE_FILE)
    return states.get(str(chat_id), {})

def save_state(chat_id, state_data):
    states = load_json(STATE_FILE)
    states[str(chat_id)] = state_data
    save_json(STATE_FILE, states)

def clear_state(chat_id):
    states = load_json(STATE_FILE)
    if str(chat_id) in states:
        del states[str(chat_id)]
        save_json(STATE_FILE, states)

def add_transaction(chat_id, kind, amount, category):
    txs = load_json(TX_FILE)
    txs.append({
        "user_id": chat_id,
        "kind": kind,
        "amount": amount,
        "category": category,
        "timestamp": int(time.time())
    })
    save_json(TX_FILE, txs)

def get_user_transactions(chat_id):
    txs = load_json(TX_FILE)
    return [tx for tx in txs if tx["user_id"] == chat_id]

def get_categories(chat_id):
    user = get_user(chat_id)
    if not user:
        return {"income": [], "expense": []}
    return user.get("categories", {"income": [], "expense": []})

def add_category(chat_id, kind, name):
    user = get_user(chat_id) or {"categories": {"income": [], "expense": []}, "currency": "RUB"}
    if kind not in user["categories"]:
        user["categories"][kind] = []
    if name not in user["categories"][kind]:
        user["categories"][kind].append(name)
    save_user(chat_id, user)

def reply_keyboard(buttons, resize=True, one_time=False):
    return {
        "keyboard": buttons,
        "resize_keyboard": resize,
        "one_time_keyboard": one_time
    }

def main_menu_keyboard():
    buttons = [
        ["➕ Добавить доход", "➖ Добавить расход"],
        ["📊 Показать отчёт", "➕ Добавить категорию"],
        ["💬 Связь с админом", "/start"]
    ]
    return reply_keyboard(buttons)

def category_menu_keyboard(categories):
    btns = [[cat] for cat in categories]
    btns.append(["❌ Отмена"])
    return reply_keyboard(btns, one_time=True)

def cancel_keyboard():
    return reply_keyboard([["❌ Отмена"]], one_time=True)

def is_valid_amount(text):
    try:
        val = float(text.replace(",", "."))
        return val > 0
    except:
        return False

def start_handler(chat_id):
    user = get_user(chat_id)
    if user and user.get("currency"):
        send_message(TOKEN, chat_id,
            f"Привет! Валюта учёта: {user['currency']}\nВыберите действие:",
            reply_markup=main_menu_keyboard())
    else:
        # Создаем пользователя с валютой по умолчанию
        save_user(chat_id, {"first_name": "", "currency": "RUB", "categories": {"income": [], "expense": []}})
        send_message(TOKEN, chat_id,
            "Привет! Валюта учёта установлена по умолчанию в RUB.\nВыберите действие:",
            reply_markup=main_menu_keyboard())

def show_report(chat_id):
    txs = get_user_transactions(chat_id)
    if not txs:
        send_message(TOKEN, chat_id, "Нет данных для отчёта.", reply_markup=main_menu_keyboard())
        return

    income_sum = 0
    expense_sum = 0
    income_cats = {}
    expense_cats = {}

    for tx in txs:
        if tx["kind"] == "income":
            income_sum += tx["amount"]
            income_cats[tx["category"]] = income_cats.get(tx["category"], 0) + tx["amount"]
        else:
            expense_sum += tx["amount"]
            expense_cats[tx["category"]] = expense_cats.get(tx["category"], 0) + tx["amount"]

    balance = income_sum - expense_sum

    text = f"📊 <b>Отчёт по финансам</b>\n\n"
    text += f"💰 Доходы: {income_sum:.2f}\n"
    text += f"💸 Расходы: {expense_sum:.2f}\n"
    text += f"⚖️ Баланс: {balance:.2f}\n\n"

    text += "📈 Доходы по категориям:\n"
    if income_cats:
        for cat, amt in income_cats.items():
            text += f" - {cat}: {amt:.2f}\n"
    else:
        text += " - Нет данных\n"

    text += "\n📉 Расходы по категориям:\n"
    if expense_cats:
        for cat, amt in expense_cats.items():
            text += f" - {cat}: {amt:.2f}\n"
    else:
        text += " - Нет данных\n"

    send_message(TOKEN, chat_id, text, reply_markup=main_menu_keyboard())

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user = get_user(chat_id)
    if not user:
        save_user(chat_id, {"first_name": message["chat"].get("first_name", ""), "currency": "RUB", "categories": {"income": [], "expense": []}})
        user = get_user(chat_id)

    state = get_state(chat_id)

    if text == "/start":
        start_handler(chat_id)
        clear_state(chat_id)
        return

    if state:
        action = state.get("action")
        if action == "add_income_amount":
            if not is_valid_amount(text):
                send_message(TOKEN, chat_id, "Ошибка: введите положительное число для суммы.", reply_markup=cancel_keyboard())
                return
            state["amount"] = float(text.replace(",", "."))
            save_state(chat_id, state)

            categories = get_categories(chat_id).get("income", [])
            if not categories:
                send_message(TOKEN, chat_id, "Категорий доходов нет. Введите название новой категории:", reply_markup=cancel_keyboard())
                state["action"] = "add_income_category_new"
                save_state(chat_id, state)
                return

            send_message(TOKEN, chat_id, "Выберите категорию дохода:", reply_markup=category_menu_keyboard(categories))
            state["action"] = "add_income_category"
            save_state(chat_id, state)
            return

        if action == "add_income_category_new":
            category = text
            if category == "❌ Отмена" or not category:
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            add_category(chat_id, "income", category)
            amount = state.get("amount", 0)
            add_transaction(chat_id, "income", amount, category)
            clear_state(chat_id)
            send_message(TOKEN, chat_id, f"Доход {amount} добавлен в категорию '{category}'.", reply_markup=main_menu_keyboard())
            return

        if action == "add_income_category":
            category = text
            if category == "❌ Отмена":
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            categories = get_categories(chat_id).get("income", [])
            if category not in categories:
                send_message(TOKEN, chat_id, "Такой категории нет. Введите правильную или добавьте новую через кнопку '➕ Добавить категорию'.", reply_markup=category_menu_keyboard(categories))
                return
            amount = state.get("amount", 0)
            add_transaction(chat_id, "income", amount, category)
            clear_state(chat_id)
            send_message(TOKEN, chat_id, f"Доход {amount} добавлен в категорию '{category}'.", reply_markup=main_menu_keyboard())
            return

        if action == "add_expense_amount":
            if not is_valid_amount(text):
                send_message(TOKEN, chat_id, "Ошибка: введите положительное число для суммы.", reply_markup=cancel_keyboard())
                return
            state["amount"] = float(text.replace(",", "."))
            save_state(chat_id, state)

            categories = get_categories(chat_id).get("expense", [])
            if not categories:
                send_message(TOKEN, chat_id, "Категорий расходов нет. Введите название новой категории:", reply_markup=cancel_keyboard())
                state["action"] = "add_expense_category_new"
                save_state(chat_id, state)
                return

            send_message(TOKEN, chat_id, "Выберите категорию расхода:", reply_markup=category_menu_keyboard(categories))
            state["action"] = "add_expense_category"
            save_state(chat_id, state)
            return

        if action == "add_expense_category_new":
            category = text
            if category == "❌ Отмена" or not category:
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            add_category(chat_id, "expense", category)
            amount = state.get("amount", 0)
            add_transaction(chat_id, "expense", amount, category)
            clear_state(chat_id)
            send_message(TOKEN, chat_id, f"Расход {amount} добавлен в категорию '{category}'.", reply_markup=main_menu_keyboard())
            return

        if action == "add_expense_category":
            category = text
            if category == "❌ Отмена":
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            categories = get_categories(chat_id).get("expense", [])
            if category not in categories:
                send_message(TOKEN, chat_id, "Такой категории нет. Введите правильную или добавьте новую через кнопку '➕ Добавить категорию'.", reply_markup=category_menu_keyboard(categories))
                return
            amount = state.get("amount", 0)
            add_transaction(chat_id, "expense", amount, category)
            clear_state(chat_id)
            send_message(TOKEN, chat_id, f"Расход {amount} добавлен в категорию '{category}'.", reply_markup=main_menu_keyboard())
            return

        if action == "add_category":
            if text == "Доход":
                save_state(chat_id, {"action": "add_category_new", "kind": "income"})
                send_message(TOKEN, chat_id, "Введите название новой категории дохода:", reply_markup=cancel_keyboard())
                return
            elif text == "Расход":
                save_state(chat_id, {"action": "add_category_new", "kind": "expense"})
                send_message(TOKEN, chat_id, "Введите название новой категории расхода:", reply_markup=cancel_keyboard())
                return
            elif text == "❌ Отмена":
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            else:
                send_message(TOKEN, chat_id, "Выберите 'Доход' или 'Расход' или отмену.", reply_markup=reply_keyboard([["Доход", "Расход"], ["❌ Отмена"]], one_time=True))
                return

        if action == "add_category_new":
            category = text
            if category == "❌ Отмена" or not category:
                clear_state(chat_id)
                send_message(TOKEN, chat_id, "Отмена.", reply_markup=main_menu_keyboard())
                return
            kind = state.get("kind")
            add_category(chat_id, kind, category)
            clear_state(chat_id)
            send_message(TOKEN, chat_id, f"Категория '{category}' добавлена в {kind}.", reply_markup=main_menu_keyboard())
            return

        if action == "contact_admin":
            msg = text
            if not msg:
                send_message(TOKEN, chat_id, "Сообщение не может быть пустым. Попробуйте ещё раз.", reply_markup=cancel_keyboard())
                return
            users = load_json(USERS_FILE)
            user_info = users.get(str(chat_id), {})
            user_name = user_info.get("first_name", "Пользователь")
            admin_message = f"📩 Сообщение от пользователя <b>{user_name}</b> (id: {chat_id}):\n\n{msg}"
            send_message(TOKEN, ADMIN_ID, admin_message)
            send_message(TOKEN, chat_id, "Сообщение отправлено администратору.", reply_markup=main_menu_keyboard())
            clear_state(chat_id)
            return

    # Если не в состоянии — обрабатываем кнопки главного меню

    if text == "➕ Добавить доход":
        save_state(chat_id, {"action": "add_income_amount"})
        send_message(TOKEN, chat_id, "Введите сумму дохода:", reply_markup=cancel_keyboard())
        return

    if text == "➖ Добавить расход":
        save_state(chat_id, {"action": "add_expense_amount"})
        send_message(TOKEN, chat_id, "Введите сумму расхода:", reply_markup=cancel_keyboard())
        return

    if text == "➕ Добавить категорию":
        save_state(chat_id, {"action": "add_category"})
        send_message(TOKEN, chat_id, "Выберите тип категории:", reply_markup=reply_keyboard([["Доход", "Расход"], ["❌ Отмена"]], one_time=True))
        return

    if text == "📊 Показать отчёт":
        show_report(chat_id)
        return

    if text == "💬 Связь с админом":
        save_state(chat_id, {"action": "contact_admin"})
        send_message(TOKEN, chat_id, "Напишите сообщение администратору:", reply_markup=cancel_keyboard())
        return

    if text == "❌ Отмена":
        clear_state(chat_id)
        send_message(TOKEN, chat_id, "Действие отменено.", reply_markup=main_menu_keyboard())
        return

    send_message(TOKEN, chat_id, "Пожалуйста, используйте кнопки меню.", reply_markup=main_menu_keyboard())

def main():
    ensure_files()
    offset = 0
    print("Бот запущен...")
    while True:
        updates = get_updates(TOKEN, offset, timeout=15)
        if updates and updates.get("ok"):
            for update in updates["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    handle_message(update["message"])
        time.sleep(0.3)

if __name__ == "__main__":
    main()
