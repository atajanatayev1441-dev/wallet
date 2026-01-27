import requests

BASE_URL = "https://api.telegram.org/bot"

def get_updates(token, offset=None, timeout=20):
    url = f"{BASE_URL}{token}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(url, params=params)
        return resp.json()
    except Exception as e:
        print(f"Ошибка при getUpdates: {e}")
        return None

def send_message(token, chat_id, text, reply_markup=None, parse_mode="HTML"):
    url = f"{BASE_URL}{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        import json
        data["reply_markup"] = json.dumps(reply_markup)
    try:
        resp = requests.post(url, data=data)
        if not resp.ok:
            print(f"Ошибка Telegram API: {resp.text}")
        return resp.json()
    except Exception as e:
        print(f"Ошибка при sendMessage: {e}")
        return None
