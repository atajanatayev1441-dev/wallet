import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def api_call(token, method, params=None):
    url = API_URL.format(token=token, method=method)
    if params is not None:
        data = urllib.parse.urlencode(params).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_data = response.read()
            return json.loads(resp_data.decode())
    except Exception as e:
        print(f"Telegram API call error: {e}")
        return None

def get_updates(token, offset=0, timeout=20):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    result = api_call(token, "getUpdates", params)
    if result and result.get("ok"):
        return result.get("result", [])
    return []

def send_message(token, chat_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    result = api_call(token, "sendMessage", params)
    return result

def send_sticker(token, chat_id, sticker_id):
    params = {
        "chat_id": chat_id,
        "sticker": sticker_id
    }
    result = api_call(token, "sendSticker", params)
    return result

def answer_callback_query(token, callback_query_id, text=None, show_alert=False):
    params = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        params["text"] = text
    result = api_call(token, "answerCallbackQuery", params)
    return result
