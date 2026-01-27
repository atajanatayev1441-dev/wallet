import urllib.request
import urllib.parse
import json

API_URL = "https://api.telegram.org/bot{token}/{method}"

def api_call(token, method, params=None, is_post=True):
    url = API_URL.format(token=token, method=method)
    data = None
    headers = {}

    if params:
        if is_post:
            data = urllib.parse.urlencode(params).encode('utf-8')
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp = response.read()
            return json.loads(resp.decode('utf-8'))
    except Exception as e:
        print(f"Telegram API call error: {e}")
        return None

def get_updates(token, offset=0, timeout=10):
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    return api_call(token, "getUpdates", params, is_post=False)

def send_message(token, chat_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        params["reply_markup"] = reply_markup

    return api_call(token, "sendMessage", params)

def send_sticker(token, chat_id, sticker_id):
    params = {
        "chat_id": chat_id,
        "sticker": sticker_id
    }
    return api_call(token, "sendSticker", params)
