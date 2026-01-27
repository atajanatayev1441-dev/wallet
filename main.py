import time
import traceback
from telegram_api import get_updates, send_message

TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
ADMIN_ID = 123456789  # замените на ID вашего админа

offset = 0

def handle_message(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        send_message(TOKEN, chat_id, "Привет! Это твой финансовый трекер.")
        # Можно добавить клавиатуру меню
    elif text == "👥 Пользователи":
        if chat_id == ADMIN_ID:
            # Здесь логика отправки отчёта или количества пользователей
            send_message(TOKEN, chat_id, "Пока что нет пользователей.")
        else:
            send_message(TOKEN, chat_id, "У вас нет доступа к этой команде.")
    else:
        send_message(TOKEN, chat_id, f"Вы написали: {text}")

def handle_callback(update):
    # Здесь обработка нажатий на кнопки, если есть
    pass

def main():
    global offset
    while True:
        try:
            updates = get_updates(TOKEN, offset, timeout=20)
            if not updates:
                continue
            for update in updates:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update)
                else:
                    handle_message(update)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    main()
