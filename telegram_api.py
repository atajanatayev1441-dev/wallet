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

    if params and method in ("sendMessage", "editMessageText", "answerCallbackQuery"):
        # При отправке кнопок, лучше JSON в reply_markup
        if "reply_markup" in params:
            rm = params["reply_markup"]
            if isinstance(rm, str):
                # Уже сериализовано
                params["reply_markup"] = rm
            else:
                params["reply_markup"] = json.dumps(rm, ensure_ascii=False)
            data = urllib.parse.urlencode(params).encode()

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
    return api_call(token, "getUpdates", params)

def send_message(token, chat_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    return api_call(token, "sendMessage", params)

def answer_callback_query(token, callback_query_id, text=None, show_alert=False):
    params = {
        "callback_query_id": callback_query_id,
        "show_alert": show_alert
    }
    if text:
        params["text"] = text
    return api_call(token, "answerCallbackQuery", params)
