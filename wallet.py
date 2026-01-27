# wallet.py
from storage import load, TX

def get_balance(user_id):
    tx = [t for t in load(TX) if t["user_id"] == str(user_id)]
    income = sum(t["amount"] for t in tx if t["kind"] == "income")
    expense = sum(t["amount"] for t in tx if t["kind"] == "expense")
    return income, expense, income - expense

def report_by_category(user_id, kind):
    tx = [t for t in load(TX) if t["user_id"] == str(user_id) and t["kind"] == kind]
    result = {}
    for t in tx:
        result[t["category"]] = result.get(t["category"], 0) + t["amount"]
    return result
