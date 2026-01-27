import time
import json
from telegram_api import get_updates, send_message
from collections import defaultdict

TOKEN = "8263345320:AAFr3_tHDhX_x0eNywQkq-SCXBTQG7avYvk"
ADMIN_ID = 8283258905  # Заменить на ID админа

DATA_FILE = "data.json"

# Загрузка/сохранение данных
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

user_states = {}  # Состояния пользователей: {chat_id: {action: ..., step: ..., ...}}

# Клавиатуры
def main_keyboard(chat_id):
    kb = [
        [{"text": "➕ Добавить доход", "callback_data": "add_income"}],
        [{"text": "➖ Добавить расход", "callback_data": "add_expense"}],
        [{"text": "📊 Отчёты и анализ", "callback_data": "reports"}],
        [{"text": "✉️ Связь с админом", "callback_data": "contact_admin"}],
    ]
    if chat_id == ADMIN_ID:
        kb.append([{"text": "👥 Пользователи", "callback_data": "users_list"}])
    return {"inline_keyboard": kb}

def cancel_keyboard():
    return {"inline_keyboard": [[{"text": "❌ Отмена", "callback_data": "cancel"}]]}

def category_keyboard(categories):
    kb = [[{"text": c, "callback_data": f"cat_{c}"}] for c in categories]
    kb.append([{"text": "➕ Добавить категорию", "callback_data": "add_category"}])
    kb.append([{"text": "❌ Отмена", "callback_data": "cancel"}])
    return {"inline_keyboard": kb}

# Помощь при старте
def handle_start(chat_id, user):
    if str(chat_id) not in data["users"]:
        data["users"][str(chat_id)] = {
            "incomes": [],
            "expenses": [],
            "categories_income": ["Зарплата", "Подарки", "Прочее"],
            "categories_expense": ["Еда", "Транспорт", "Развлечения", "Прочее"]
        }
        save_data(data)
    send_message(TOKEN, chat_id, f"Привет, {user.get('first_name', '')}! Это трекер доходов и расходов. Выбери действие:", reply_markup=main_keyboard(chat_id))
    user_states.pop(str(chat_id), None)

# Обработка добавления дохода и расходов (шаги)
def process_amount(chat_id, text):
    state = user_states.get(str(chat_id))
    if not state:
        send_message(TOKEN, chat_id, "Что-то пошло не так. Пожалуйста, выберите действие заново.", reply_markup=main_keyboard(chat_id))
        return

    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            raise ValueError()
    except:
        send_message(TOKEN, chat_id, "Введите корректную сумму (например, 123.45) или ❌ Отмена.")
        return

    state["amount"] = amount
    state["step"] = "category"

    # Выбор категорий зависит от типа действия
    if state["action"] == "add_income":
        categories = data["users"][str(chat_id)]["categories_income"]
    else:
        categories = data["users"][str(chat_id)]["categories_expense"]

    send_message(TOKEN, chat_id, "Выберите категорию:", reply_markup=category_keyboard(categories))

# Обработка выбора категории
def process_category(chat_id, category):
    state = user_states.get(str(chat_id))
    if not state or "amount" not in state:
        send_message(TOKEN, chat_id, "Произошла ошибка. Попробуйте заново.", reply_markup=main_keyboard(chat_id))
        return

    amount = state["amount"]
    user_data = data["users"][str(chat_id)]

    if state["action"] == "add_income":
        user_data["incomes"].append({"amount": amount, "category": category})
        save_data(data)
        send_message(TOKEN, chat_id, f"Добавлен доход: {amount:.2f} в категории '{category}'.", reply_markup=main_keyboard(chat_id))
    elif state["action"] == "add_expense":
        user_data["expenses"].append({"amount": amount, "category": category})
        save_data(data)
        send_message(TOKEN, chat_id, f"Добавлен расход: {amount:.2f} в категории '{category}'.", reply_markup=main_keyboard(chat_id))
    else:
        send_message(TOKEN, chat_id, "Неизвестное действие.", reply_markup=main_keyboard(chat_id))

    user_states.pop(str(chat_id), None)

# Добавление новой категории
def process_add_category(chat_id, text):
    state = user_states.get(str(chat_id))
    if not state or "action" not in state:
        send_message(TOKEN, chat_id, "Ошибка. Попробуйте заново.", reply_markup=main_keyboard(chat_id))
        return

    new_cat = text.strip()
    if not new_cat:
        send_message(TOKEN, chat_id, "Название категории не может быть пустым. Попробуйте снова или ❌ Отмена.")
        return

    user_data = data["users"][str(chat_id)]
    if state["action"] == "add_income":
        cats = user_data["categories_income"]
    else:
        cats = user_data["categories_expense"]

    if new_cat in cats:
        send_message(TOKEN, chat_id, "Такая категория уже есть. Введите другую или ❌ Отмена.")
        return

    cats.append(new_cat)
    save_data(data)
    send_message(TOKEN, chat_id, f"Категория '{new_cat}' добавлена.")
    user_states.pop(str(chat_id), None)
    send_message(TOKEN, chat_id, "Возвращаемся в меню.", reply_markup=main_keyboard(chat_id))

# Формирование отчёта
def process_reports(chat_id):
    user_data = data["users"].get(str(chat_id))
    if not user_data:
        send_message(TOKEN, chat_id, "Данных нет.")
        return

    total_income = sum(i["amount"] for i in user_data["incomes"])
    total_expense = sum(e["amount"] for e in user_data["expenses"])
    balance = total_income - total_expense

    # Анализ категорий расходов
    cat_expense_sum = defaultdict(float)
    for e in user_data["expenses"]:
        cat_expense_sum[e["category"]] += e["amount"]

    report = f"📊 Отчёт:\n\nДоходы: {total_income:.2f}\nРасходы: {total_expense:.2f}\nБаланс: {balance:.2f}\n\n"

    if cat_expense_sum:
        report += "Топ расходов по категориям:\n"
        for cat, val in sorted(cat_expense_sum.items(), key=lambda x: x[1], reverse=True)[:5]:
            report += f" - {cat}: {val:.2f}\n"

    send_message(TOKEN, chat_id, report, reply_markup=main_keyboard(chat_id))

# Связь с админом
def process_contact_admin(chat_id, text):
    if chat_id == ADMIN_ID:
        send_message(TOKEN, chat_id, "Вы — админ. Используйте команды.")
        return
    send_message(TOKEN, ADMIN_ID, f"Сообщение от пользователя {chat_id}:\n\n{text}")
    send_message(TOKEN, chat_id, "Сообщение отправлено администратору.", reply_markup=main_keyboard(chat_id))
    user_states.pop(str(chat_id), None)

# Обработка callback_query
def handle_callback(update):
    callback = update.get("callback_query")
    if not callback:
        return
    data_cb = callback["data"]
    chat_id = callback["message"]["chat"]["id"]

    if data_cb == "cancel":
        user_states.pop(str(chat_id), None)
        send_message(TOKEN, chat_id, "Действие отменено.", reply_markup=main_keyboard(chat_id))
        return

    if data_cb == "add_income":
        user_states[str(chat_id)] = {"action": "add_income", "step": "amount"}
        send_message(TOKEN, chat_id, "Введите сумму дохода:")
        return

    if data_cb == "add_expense":
        user_states[str(chat_id)] = {"action": "add_expense", "step": "amount"}
        send_message(TOKEN, chat_id, "Введите сумму расхода:")
        return

    if data_cb == "reports":
        process_reports(chat_id)
        return

    if data_cb == "contact_admin":
        user_states[str(chat_id)] = {"action": "contact_admin"}
        send_message(TOKEN, chat_id, "Напишите сообщение администратору:")
        return

    if data_cb == "users_list" and chat_id == ADMIN_ID:
        count = len(data.get("users", {}))
        send_message(TOKEN, chat_id, f"Всего пользователей: {count}", reply_markup=main_keyboard(chat_id))
        return

    if data_cb.startswith("cat_"):
        cat = data_cb[4:]
        process_category(chat_id, cat)
        return

    if data_cb == "add_category":
        state = user_states.get(str(chat_id))
        if state and state["action"] in ["add_income", "add_expense"]:
            send_message(TOKEN, chat_id, "Введите название новой категории:")
            user_states[str(chat_id)] = {"action": state["action"], "step": "add_category"}
        else:
            send_message(TOKEN, chat_id, "Ошибка, начните заново.", reply_markup=main_keyboard(chat_id))
        return

# Основной цикл
def main():
    offset = 0
    print("Бот запущен")
    while True:
        try:
            updates = get_updates(TOKEN, offset, timeout=20)
            for update in updates:
                offset = update["update_id"] + 1

                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")
                    user = msg.get("from", {})

                    state = user_states.get(str(chat_id))

                    if text == "/start":
                        handle_start(chat_id, user)
                        continue

                    if state:
                        action = state.get("action")
                        step = state.get("step")

                        if action in ["add_income", "add_expense"]:
                            if step == "amount":
                                process_amount(chat_id, text)
                                continue
                            elif step == "add_category":
                                process_add_category(chat_id, text)
                                continue

                        if action == "contact_admin":
                            if text.strip() != "❌ Отмена":
                                process_contact_admin(chat_id, text)
                            else:
                                send_message(TOKEN, chat_id, "Связь с админом отменена.", reply_markup=main_keyboard(chat_id))
                                user_states.pop(str(chat_id), None)
                            continue

                    # Если нет активных состояний, просто напоминаем меню
                    send_message(TOKEN, chat_id, "Пожалуйста, используйте меню.", reply_markup=main_keyboard(chat_id))

                elif "callback_query" in update:
                    handle_callback(update)

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
