import json
import os
import time
from telegram_api import get_updates, send_message, answer_callback_query

TOKEN = os.getenv("BOT_TOKEN")  # Установи через переменную окружения
ADMIN_ID = 8283258905 # Заменить на свой Telegram ID администратора

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TX_FILE = os.path.join(DATA_DIR, "transactions.json")
STATE_FILE = os.path.join(DATA_DIR, "states.json")

# Создаём папку и файлы, если их нет
def ensure_files():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    for f in [USERS_FILE, TX_FILE, STATE_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as file:
                if f == USERS_FILE or f == STATE_FILE:
                    file.write("{}")  # словарь
                else:
                    file.write("[]")  # список для транзакций

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Работа с пользователями и состояниями ---

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

# --- Транзакции ---

def add_transaction(chat_id, kind, amount, category, currency):
    txs = load_json(TX_FILE)
    txs.append({
        "user_id": chat_id,
        "kind": kind,  # income/expense
        "amount": amount,
        "category": category,
        "currency": currency,
        "timestamp": int(time.time())
    })
    save_json(TX_FILE, txs)

def get_user_transactions(chat_id):
    txs = load_json(TX_FILE)
    return [tx for tx in txs if tx["user_id"] == chat_id]

# --- Категории ---

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

# --- Кнопки ---

def make_keyboard(buttons, row_width=2):
    keyboard = []
    row = []
    for i, (text, callback_data) in enumerate(buttons, 1):
        row.append({"text": text, "callback_data": callback_data})
        if i % row_width == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return {"inline_keyboard": keyboard}

def main_menu_keyboard(is_admin=False):
    buttons = [
        ("➕ Добавить доход", "add_income"),
        ("➖ Добавить расход", "add_expense"),
        ("📊 Показать отчёт", "show_report"),
        ("➕ Добавить категорию дохода", "add_cat_income"),
        ("➕ Добавить категорию расхода", "add_cat_expense"),
        ("💬 Связь с админом", "contact_admin"),
    ]
    if is_admin:
        buttons.append(("👥 Пользователи", "admin_users"))
        buttons.append(("📢 Рассылка", "admin_broadcast"))
    return make_keyboard(buttons, row_width=2)

def currency_keyboard():
    buttons = [
        ("🇷🇺 RUB", "cur_RUB"),
        ("🇹🇲 TMT", "cur_TMT"),
        ("🇺🇸 USD", "cur_USD"),
    ]
    return make_keyboard(buttons, row_width=3)

def cancel_button():
    return make_keyboard([("❌ Отмена", "cancel")], row_width=1)

def back_to_menu_button():
    return make_keyboard([("⬅️ Вернуться в меню", "back_menu")], row_width=1)

# --- Логика обработки сообщений и callback ---

def start_handler(chat_id):
    user = get_user(chat_id)
    if user and user.get("currency"):
        text = f"С возвращением! Валюта: {user['currency']}\nВыберите действие:"
        is_admin = (chat_id == ADMIN_ID)
        send_message(TOKEN, chat_id, text, main_menu_keyboard(is_admin))
    else:
        send_message(TOKEN, chat_id, "Выберите валюту для учёта:", currency_keyboard())

def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    is_admin = (chat_id == ADMIN_ID)

    if data == "cancel":
        clear_state(chat_id)
        send_message(TOKEN, chat_id, "Действие отменено.", main_menu_keyboard(is_admin))
        answer_callback_query(TOKEN, callback["id"])
        return

    if data == "back_menu":
        clear_state(chat_id)
        send_message(TOKEN, chat_id, "Главное меню:", main_menu_keyboard(is_admin))
        answer_callback_query(TOKEN, callback["id"])
        return

    if data.startswith("cur_"):
        currency = data.split("_")[1]
        user = get_user(chat_id) or {}
        user["currency"] = currency
        if "categories" not in user:
            user["categories"] = {"income": [], "expense": []}
        save_user(chat_id, user)
        send_message(TOKEN, chat_id, f"Валюта установлена: {currency}\nВыберите действие:", main_menu_keyboard(is_admin))
        answer_callback_query(TOKEN, callback["id"])
        return

    state = get_state(chat_id)

    # Добавление дохода
    if data == "add_income":
        state.update({"action": "adding_income", "step": "amount"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Введите сумму дохода:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Добавление расхода
    if data == "add_expense":
        state.update({"action": "adding_expense", "step": "amount"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Введите сумму расхода:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Добавление категории дохода
    if data == "add_cat_income":
        state.update({"action": "adding_category", "kind": "income", "step": "name"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Введите название новой категории дохода:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Добавление категории расхода
    if data == "add_cat_expense":
        state.update({"action": "adding_category", "kind": "expense", "step": "name"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Введите название новой категории расхода:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Показать отчёт
    if data == "show_report":
        show_report(chat_id)
        answer_callback_query(TOKEN, callback["id"])
        return

    # Связь с админом
    if data == "contact_admin":
        state.update({"action": "contacting_admin"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Напишите сообщение администратору:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Админ: показать пользователей
    if is_admin and data == "admin_users":
        users = load_json(USERS_FILE)
        count = len(users)
        send_message(TOKEN, chat_id, f"Всего пользователей: {count}", back_to_menu_button())
        answer_callback_query(TOKEN, callback["id"])
        return

    # Админ: рассылка
    if is_admin and data == "admin_broadcast":
        state.update({"action": "admin_broadcast"})
        save_state(chat_id, state)
        send_message(TOKEN, chat_id, "Напишите сообщение для рассылки всем пользователям:", cancel_button())
        answer_callback_query(TOKEN, callback["id"])
        return

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    is_admin = (chat_id == ADMIN_ID)
    state = get_state(chat_id)

    # Если в процессе какого-то действия
    if state:
        action = state.get("action")
        step = state.get("step")

        if action == "adding_income":
            if step == "amount":
                if not is_valid_amount(text):
                    send_message(TOKEN, chat_id, "Введите корректную сумму (например, 1000.50):", cancel_button())
                    return
                state["amount"] = float(text)
                state["step"] = "category"
                save_state(chat_id, state)

                categories = get_categories(chat_id).get("income", [])
                if not categories:
                    send_message(TOKEN, chat_id, "Категории доходов отсутствуют. Введите новую категорию дохода:", cancel_button())
                    state["action"] = "adding_category"
                    state["kind"] = "income"
                    state["step"] = "name"
                    save_state(chat_id, state)
                else:
                    kb = make_keyboard([(c, f"cat_income_{c}") for c in categories], row_width=2)
                    kb["inline_keyboard"].append([{"text": "➕ Добавить категорию", "callback_data": "add_cat_income"}])
                    kb["inline_keyboard"].append([{"text": "❌ Отмена", "callback_data": "cancel"}])
                    send_message(TOKEN, chat_id, "Выберите категорию дохода или добавьте новую:", kb)
                return

            if step == "category":
                # Категории выбираются через callback, не текстом
                send_message(TOKEN, chat_id, "Пожалуйста, выберите категорию с помощью кнопок ниже.", cancel_button())
                return

        if action == "adding_expense":
            if step == "amount":
                if not is_valid_amount(text):
                    send_message(TOKEN, chat_id, "Введите корректную сумму (например, 1000.50):", cancel_button())
                    return
                state["amount"] = float(text)
                state["step"] = "category"
                save_state(chat_id, state)

                categories = get_categories(chat_id).get("expense", [])
                if not categories:
                    send_message(TOKEN, chat_id, "Категории расходов отсутствуют. Введите новую категорию расхода:", cancel_button())
                    state["action"] = "adding_category"
                    state["kind"] = "expense"
                    state["step"] = "name"
                    save_state(chat_id, state)
                else:
                    kb = make_keyboard([(c, f"cat_expense_{c}") for c in categories], row_width=2)
                    kb["inline_keyboard"].append([{"text": "➕ Добавить категорию", "callback_data": "add_cat_expense"}])
                    kb["inline_keyboard"].append([{"text": "❌ Отмена", "callback_data": "cancel"}])
                    send_message(TOKEN, chat_id, "Выберите категорию расхода или добавьте новую:", kb)
                return

            if step == "category":
                send_message(TOKEN, chat_id, "Пожалуйста, выберите категорию с помощью кнопок ниже.", cancel_button())
                return

        if action == "adding_category":
            if step == "name":
                name = text.strip()
                if not name:
                    send_message(TOKEN, chat_id, "Название категории не может быть пустым. Введите снова:", cancel_button())
                    return
                add_category(chat_id, state["kind"], name)
                send_message(TOKEN, chat_id, f"Категория '{name}' добавлена.", back_to_menu_button())
                clear_state(chat_id)
                return

        if action == "contacting_admin":
            msg = text.strip()
            if not msg:
                send_message(TOKEN, chat_id, "Сообщение не может быть пустым. Попробуйте ещё раз:", cancel_button())
                return
            users = load_json(USERS_FILE)
            user_info = users.get(str(chat_id), {})
            user_name = user_info.get("first_name", "Пользователь")
            admin_message = f"📩 <b>Сообщение от пользователя</b> <i>{user_name}</i> (id: {chat_id}):\n\n{msg}"
            send_message(TOKEN, ADMIN_ID, admin_message)
            send_message(TOKEN, chat_id, "Сообщение отправлено администратору.", back_to_menu_button())
            clear_state(chat_id)
            return

        if action == "admin_broadcast" and is_admin:
            msg = text.strip()
            if not msg:
                send_message(TOKEN, chat_id, "Сообщение не может быть пустым. Попробуйте ещё раз:", cancel_button())
                return
            users = load_json(USERS_FILE)
            count = 0
            for u in users.keys():
                try:
                    send_message(TOKEN, int(u), msg)
                    count +=1
                    time.sleep(0.1)
                except:
                    pass
            send_message(TOKEN, chat_id, f"Рассылка выполнена. Отправлено {count} пользователям.", back_to_menu_button())
            clear_state(chat_id)
            return

    # Обработка выбора категории (callback)
    # Обрабатываем в handle_callback

    # Если не в процессе действий, реагируем на команды
    if text == "/start":
        start_handler(chat_id)
    else:
        send_message(TOKEN, chat_id, "Пожалуйста, используйте кнопки меню.", main_menu_keyboard(is_admin))

def is_valid_amount(text):
    try:
        val = float(text.replace(",", "."))
        return val > 0
    except:
        return False

def show_report(chat_id):
    txs = get_user_transactions(chat_id)
    if not txs:
        send_message(TOKEN, chat_id, "Нет данных для отчёта.", back_to_menu_button())
        return

    # Подсчёт доходов и расходов по категориям
    income_sum = 0
    expense_sum = 0
    income_cats = {}
    expense_cats = {}

    user = get_user(chat_id)
    currency = user.get("currency", "RUB")

    for tx in txs:
        if tx["kind"] == "income":
            income_sum += tx["amount"]
            income_cats[tx["category"]] = income_cats.get(tx["category"], 0) + tx["amount"]
        else:
            expense_sum += tx["amount"]
            expense_cats[tx["category"]] = expense_cats.get(tx["category"], 0) + tx["amount"]

    text = f"📊 <b>Отчёт по финансам</b>\nВалюта: {currency}\n\n"
    text += f"💰 Доходы: {income_sum:.2f} {currency}\n"
    text += f"💸 Расходы: {expense_sum:.2f} {currency}\n\n"

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

    send_message(TOKEN, chat_id, text, back_to_menu_button())

# --- Основной цикл ---

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
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    # Сохраняем пользователя при первом общении
                    users = load_json(USERS_FILE)
                    if str(chat_id) not in users:
                        users[str(chat_id)] = {
                            "first_name": msg["chat"].get("first_name", ""),
                            "categories": {"income": [], "expense": []},
                            "currency": None
                        }
                        save_json(USERS_FILE, users)
                    handle_message(msg)
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
        time.sleep(0.3)

if __name__ == "__main__":
    main()

