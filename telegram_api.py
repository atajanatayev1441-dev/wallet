import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def api_call(token, method, params=None):
    url = API_URL.format(token=token, method=method)
    data = None
    if params:
        data = urllib.parse.urlencode(params).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Telegram API call error: {e}")
        return None

def get_updates(token, offset=0, timeout=20):
    params = {"timeout": timeout, "offset": offset}
    res = api_call(token, "getUpdates", params)
    if res and res.get("ok"):
        return res["result"]
    return []

def send_message(token, chat_id, text, keyboard=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    api_call(token, "sendMessage", params)
