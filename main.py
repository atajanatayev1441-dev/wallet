import os
import time
import json
import csv
import urllib.request
import urllib.parse
import traceback

from telegram_api import send_message, get_updates, api_call, send_sticker

ADMIN_ID = int(os.getenv("ADMIN_ID", "8283258905"))

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Set it in environment variables.")

USERS_FILE = "users.json"
DATA_FILE = "user_data.json"

offset = 0
users = set()
user_currency = {}
user_states = {}

STICKERS = {
    "RUB": "CAACAgIAAxkBAAIBHmHqg6R7_R8US-V7C1d27gU8RxFwAAKdBAACGhTgSvhN14Xw45bsLwQ",
    "USD": "CAACAgIAAxkBAAIBIGHqg67DxFjkDTr6ZAmvsk2yk-6WAAJhBAACGhTgSn1DrRzknzxVvLwQ",
    "TMT": "CAACAgIAAxkBAAIBIWHqg6eX6aHYo2ycbVjL8DkQwFtuAAJfBAACGhTgSnESevjE6ivF4LwQ"
}

def load_json_file(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения файла {filename}: {e}")

def load_users():
    return set(load_json_file(USERS_FILE, []))

def save_users(users_set):
    save_json_file(USERS_FILE, list(users_set))

def load_user_data():
    return load_json_file(DATA_FILE, {})

def save_user_data(data):
    save_json_file(DATA_FILE, data)

def reset_state(chat_id):
    if chat_id in user_states:
        del user_states[chat_id]

def build_inline_keyboard(buttons):
    keyboard = {"inline_keyboard": buttons}
    return json.dumps(keyboard)

def build_cancel_keyboard():
    buttons = [[{"text": "❌ Отмена"}]]
    keyboard = {
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    return json.dumps(keyboard)

def answer_callback_query(token, callback_query_id):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    data = urllib.parse.urlencode({"callback_query_id": callback_query_id}).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        print(f"Ошибка answerCallbackQuery: {e}")
        return False

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

def main_menu_text_and_keyboard(chat_id):
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
    if chat_id == ADMIN_ID:
        buttons.append([{"text": "👥 Количество пользователей"}])
        buttons.append([{"text": "📢 Отправить всем"}])

    reply_markup = json.dumps({
        "keyboard": buttons,
        "resize_keyboard": True,
        "one_time_keyboard": False
    })
    return text, reply_markup

def send_users_file(token, chat_id, users):
    filename = "users.csv"
    try:
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["User Chat ID"])
            for user_id in users:
                writer.writerow([user_id])

        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        data_list = []

        data_list.append(f'--{boundary}')
        data_list.append('Content-Disposition: form-data; name="chat_id"\r\n')
        data_list.append(str(chat_id))

        data_list.append(f'--{boundary}')
        data_list.append('Content-Disposition: form-data; name="document"; filename="users.csv"')
        data_list.append('Content-Type: text/csv\r\n')

        with open(filename, "rb") as f:
            file_content = f.read()
        data_list.append(file_content)

        data_list.append(f'--{boundary}--\r\n')

        body = b"\r\n".join(
            item.encode() if isinstance(item, str) else item
            for item in data_list
        )

        url = f"https://api.telegram.org/bot{token}/sendDocument"

        req = urllib.request.Request(url, data=body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"Ошибка отправки файла users.csv: {e}")
        return None

def add_user_if_new(chat_id):
    if chat_id not in users:
        users.add(chat_id)
        save_users(users)

def handle_message(message, currency, user_data):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    state = user_states.get(chat_id)

    add_user_if_new(chat_id)

    if text == "❌ Отмена":
        reset_state(chat_id)
        text_, reply_markup = main_menu_text_and_keyboard(chat_id)
        send_message(TOKEN, chat_id, "Действие отменено. Главное меню:", reply_markup)
        return

    # Команда /users (только для админа)
    if text == "/users" or text == "👥 Количество пользователей":
        if chat_id == ADMIN_ID:
            send_users_file(TOKEN, chat_id, users)
        else:
            send_message(TOKEN, chat_id, "❌ Эта команда доступна только администратору.")
        return

    # Команда отправки сообщения всем (только для админа)
    if text == "📢 Отправить всем":
        if chat_id == ADMIN_ID:
            user_states[chat_id] = {'action': 'broadcast'}
            send_message(TOKEN, chat_id, "📝 Напишите сообщение, которое нужно отправить всем пользователям:")
        else:
            send_message(TOKEN, chat_id, "❌ Эта команда доступна только администратору.")
        return

    if state:
        action = state.get('action')
        if action == 'broadcast':
            broadcast_message = text
            count = 0
            for user_id in users:
                try:
                    send_message(TOKEN, user_id, f"📢 Сообщение от администратора:\n\n{broadcast_message}")
                    count += 1
                    time.sleep(0.05)
                except Exception as e:
                    print(f"Ошибка рассылки пользователю {user_id}: {e}")
            send_message(TOKEN, chat_id, f"✅ Сообщение отправлено {count} пользователям.")
            reset_state(chat_id)
            return
        elif action == 'add_income':
            cancel_kb = build_cancel_keyboard()
            if 'step' not in state or state['step'] == 1:
                try:
                    amount = float(text.replace(",", "."))
                    if amount <= 0:
                        send_message(TOKEN, chat_id, "❌ Введите положительное число для суммы.", cancel_kb)
                        return
                    user_states[chat_id]['amount'] = amount
                    user_states[chat_id]['step'] = 2
                    send_message(TOKEN, chat_id, "Введите категорию дохода:", cancel_kb)
                except ValueError:
                    send_message(TOKEN, chat_id, "❌ Пожалуйста, введите число для суммы.", cancel_kb)
                return
            elif state['step'] == 2:
                category = text
                amount = user_states[chat_id]['amount']
                data = user_data.setdefault(str(chat_id), {'currency': currency, 'income': [], 'expense': []})
                data['income'].append({'amount': amount, 'category': category, 'timestamp': time.time()})
                save_user_data(user_data)
                send_message(TOKEN, chat_id, f"✅ Доход {amount} {currency} добавлен в категорию '{category}'.")
                reset_state(chat_id)
                return
        elif action == 'add_expense':
            cancel_kb = build_cancel_keyboard()
            if 'step' not in state or state['step'] == 1:
                try:
                    amount = float(text.replace(",", "."))
                    if amount <= 0:
                        send_message(TOKEN, chat_id, "❌ Введите положительное число для суммы.", cancel_kb)
                        return
                    user_states[chat_id]['amount'] = amount
                    user_states[chat_id]['step'] = 2
                    send_message(TOKEN, chat_id, "Введите категорию расхода:", cancel_kb)
                except ValueError:
                    send_message(TOKEN, chat_id, "❌ Пожалуйста, введите число для суммы.", cancel_kb)
                return
            elif state['step'] == 2:
                category = text
                amount = user_states[chat_id]['amount']
                data = user_data.setdefault(str(chat_id), {'currency': currency, 'income': [], 'expense': []})
                data['expense'].append({'amount': amount, 'category': category, 'timestamp': time.time()})
                save_user_data(user_data)
                send_message(TOKEN, chat_id, f"✅ Расход {amount} {currency} добавлен в категорию '{category}'.")
                reset_state(chat_id)
                return
        elif action == 'support':
            admin_msg = f"📩 Сообщение от пользователя {chat_id}:\n\n{text}"
            send_message(TOKEN, ADMIN_ID, admin_msg)
            send_message(TOKEN, chat_id, "✅ Ваше сообщение отправлено администратору.")
            reset_state(chat_id)
            return

    if text == "/start" or text == "🔄 Главное меню":
        reset_state(chat_id)
        if chat_id not in user_currency or user_currency[chat_id] is None:
            start_message(chat_id)
            user_currency[chat_id] = None
        else:
            text_, reply_markup = main_menu_text_and_keyboard(chat_id)
            send_message(TOKEN, chat_id, text_, reply_markup)
        return

    if text in ("➕ Добавить доход", "/add_income"):
        user_states[chat_id] = {'action': 'add_income', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму дохода:", build_cancel_keyboard())
        return

    if text in ("➖ Добавить расход", "/add_expense"):
        user_states[chat_id] = {'action': 'add_expense', 'step': 1}
        send_message(TOKEN, chat_id, "Введите сумму расхода:", build_cancel_keyboard())
        return

    if text in ("💰 Баланс", "/balance"):
        data = user_data.get(str(chat_id))
        if not data:
            send_message(TOKEN, chat_id, "💰 У вас пока нет доходов и расходов.")
            return
        income_sum = sum(item['amount'] for item in data['income'])
        expense_sum = sum(item['amount'] for item in data['expense'])
        balance = income_sum - expense_sum
        currency_ = data['currency']
        msg = (f"💰 Баланс: {balance:.2f} {currency_}\n"
               f"⬆️ Доходы: {income_sum:.2f} {currency_}\n"
               f"⬇️ Расходы: {expense_sum:.2f} {currency_}")
        send_message(TOKEN, chat_id, msg)
        return

    if text in ("📊 Отчёт", "/report"):
        data = user_data.get(str(chat_id))
        if not data:
            send_message(TOKEN, chat_id, "📊 Нет данных для отчёта.")
            return
        income_sum = sum(item['amount'] for item in data['income'])
        expense_sum = sum(item['amount'] for item in data['expense'])
        categories_expense = {}
        for exp in data['expense']:
            cat = exp['category']
            categories_expense[cat] = categories_expense.get(cat, 0) + exp['amount']
        currency_ = data['currency']

        msg = f"📊 Отчёт по расходам:\n"
        for cat, amount in categories_expense.items():
            msg += f"- {cat}: {amount:.2f} {currency_}\n"
        msg += f"\nОбщий доход: {income_sum:.2f} {currency_}\n"
        msg += f"Общий расход: {expense_sum:.2f} {currency_}\n"
        send_message(TOKEN, chat_id, msg)
        return

    if text in ("📂 Категории", "/categories"):
        send_message(TOKEN, chat_id, "📂 Введите категории расходов при добавлении расхода.\nПока категории не фиксированы.")
        return

    if text in ("📩 Связь с админом", "/support"):
        user_states[chat_id] = {'action': 'support'}
        send_message(TOKEN, chat_id, "📝 Напишите ваше сообщение для администратора:")
        return

    send_message(TOKEN, chat_id, "❓ Неизвестная команда. Напишите /start для начала.")

def main():
    global offset
    global user_currency

    users.update(load_users())
    user_data = load_user_data()

    print("Бот запущен")
    while True:
        try:
            updates = get_updates(TOKEN, offset)
            if not updates:
                time.sleep(1)
                continue

            for update in updates:
                offset = update["update_id"] + 1

                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]

                    if chat_id not in user_currency or user_currency[chat_id] is None:
                        start_message(chat_id)
                        user_currency[chat_id] = None
                        continue

                    handle_message(message, user_currency[chat_id], user_data)

                elif "callback_query" in update:
                    callback = update["callback_query"]
                    data = callback["data"]
                    chat_id = callback["message"]["chat"]["id"]
                    callback_id = callback["id"]

                    answer_callback_query(TOKEN, callback_id)

                    if data.startswith("currency_"):
                        currency = data.split("_")[1]
                        user_currency[chat_id] = currency
                        send_message(TOKEN, chat_id, f"✅ Валюта установлена: {currency}")

                        sticker_id = STICKERS.get(currency)
                        if sticker_id:
                            send_sticker(TOKEN, chat_id, sticker_id)

                        text_, reply_markup = main_menu_text_and_keyboard(chat_id)
                        send_message(TOKEN, chat_id, text_, reply_markup)

        except Exception as e:
            print("Ошибка в основном цикле:", e)
            print(traceback.format_exc())
            time.sleep(3)

if __name__ == "__main__":
    main()
