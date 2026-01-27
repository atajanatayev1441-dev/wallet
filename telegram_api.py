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

def get_updates(token, offset=0, timeout=10):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    result = api_call(token, "getUpdates", params)
    if result and result.get("ok"):
        return result.get("result", [])
    return []

def send_message(token, chat_id, text):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    result = api_call(token, "sendMessage", params)
    return result
