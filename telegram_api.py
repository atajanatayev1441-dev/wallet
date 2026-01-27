import urllib.request
import urllib.parse
import json

def get_updates(token, offset=None, timeout=10):
    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout={timeout}"
    if offset:
        url += f"&offset={offset}"
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
            return json.loads(data).get("result", [])
    except Exception as e:
        print(f"Telegram API call error in get_updates: {e}")
        return []

def send_message(token, chat_id, text, reply_markup=None, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    try:
        with urllib.request.urlopen(url, data=encoded_data) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Telegram API call error in send_message: {e}")
        return None

def answer_callback_query(token, callback_query_id, text=None, show_alert=False):
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    data = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert,
    }
    if text:
        data["text"] = text
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    try:
        with urllib.request.urlopen(url, data=encoded_data) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Telegram API call error in answer_callback_query: {e}")
        return None
