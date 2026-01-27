# telegram_api.py
import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def _encode(params):
    return urllib.parse.urlencode(params, encoding="utf-8").encode("utf-8")

def api_call(token, method, params=None):
    url = API_URL.format(token=token, method=method)
    data = _encode(params) if params else None

    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Telegram API error:", e)
        return None

def get_updates(token, offset=0, timeout=20):
    params = {"timeout": timeout, "offset": offset}
    resp = api_call(token, "getUpdates", params)
    if resp and resp.get("ok"):
        return resp["result"]
    return []

def send_message(token, chat_id, text, keyboard=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        params["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return api_call(token, "sendMessage", params)
