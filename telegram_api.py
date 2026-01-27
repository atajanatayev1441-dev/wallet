import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def api_call(token, method, params=None):
    url = API_URL.format(token=token, method=method)
    if params:
        # reply_markup должен быть JSON-строкой, не urlencode
        # Поэтому отдельно обрабатываем reply_markup
        params_for_url = {}
        for key, value in params.items():
            if key == "reply_markup" and value is not None:
                params_for_url[key] = value  # уже json.dumps
            else:
                params_for_url[key] = str(value)
        query_string = urllib.parse.urlencode(params_for_url)
        url = f"{url}?{query_string}"
        data = None
    else:
        data = None

    print(f"Calling URL: {url}")

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
