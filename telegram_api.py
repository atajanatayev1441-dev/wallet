import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def api_call(token, method, params=None):
    url = API_URL.format(token=token, method=method)
    if params is not None:
        data = urllib.parse.urlencode(params).encode('utf-8')
    else:
        data = None

    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_data = response.read()
            return json.loads(resp_data.decode('utf-8'))
    except Exception as e:
        print(f"Telegram API call error: {e}")
        return None

def get_updates(token, offset=0, timeout=20):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    return api_call(token, "getUpdates", params)

def send_message(token, chat_id, text, reply_markup=None, parse_mode='HTML'):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup is not None:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return api_call(token, "sendMessage", params)

def answer_callback_query(token, callback_query_id, text=None, show_alert=False):
    params = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        params["text"] = text
    return api_call(token, "answerCallbackQuery", params)
