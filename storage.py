# storage.py
import json
import os
import time

DATA_DIR = "data"
USERS = os.path.join(DATA_DIR, "users.json")
TX = os.path.join(DATA_DIR, "transactions.json")
STATES = os.path.join(DATA_DIR, "states.json")

def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    for file, default in [
        (USERS, {}),
        (TX, []),
        (STATES, {})
    ]:
        if not os.path.exists(file):
            with open(file, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False)

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_transaction(user_id, kind, amount, category):
    tx = load(TX)
    tx.append({
        "user_id": str(user_id),
        "kind": kind,
        "amount": amount,
        "category": category,
        "timestamp": int(time.time())
    })
    save(TX, tx)
