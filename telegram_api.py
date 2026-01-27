import requests

BASE_URL = "https://api.telegram.org/bot"

def get_updates(token, offset=None, timeout=20):
    url = f"{BASE_URL}{token}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    resp = requests.get(url, params=params)
    result = resp.json()
    if not result["ok"]:
        raise Exception("Ошибка получения обновлений")
    return result["result"]

def send_message(token, chat_id, text, keyboard=None):
    url = f"{BASE_URL}{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    resp = requests.post(url, json=payload)
    result = resp.json()
    if not result["ok"]:
        print(f"Telegram API call error: {result}")
    return result

def send_sticker(token, chat_id, sticker_id):
    url = f"{BASE_URL}{token}/sendSticker"
    payload = {
        "chat_id": chat_id,
        "sticker": sticker_id
    }
    resp = requests.post(url, json=payload)
    result = resp.json()
    if not result["ok"]:
        print(f"Telegram API call error: {result}")
    return result
