import json
import os
from collections import defaultdict

class WalletManager:
    def __init__(self, filename):
        self.filename = filename
        self.data = {
            "incomes": [],
            "expenses": []
        }
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"incomes": [], "expenses": []}

    def save(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add_income(self, amount, source):
        self.data["incomes"].append({
            "amount": amount,
            "source": source
        })
        self.save()

    def add_expense(self, amount, category, comment):
        self.data["expenses"].append({
            "amount": amount,
            "category": category,
            "comment": comment
        })
        self.save()

    def get_balance(self):
        total_income = sum(item["amount"] for item in self.data["incomes"])
        total_expense = sum(item["amount"] for item in self.data["expenses"])
        balance = total_income - total_expense
        return balance, total_income, total_expense

    def get_report(self):
        total_income = sum(item["amount"] for item in self.data["incomes"])
        total_expense = sum(item["amount"] for item in self.data["expenses"])
        balance = total_income - total_expense

        report = (f"📊 Отчёт за всё время:\n"
                  f"Доходы: {total_income:.2f} руб.\n"
                  f"Расходы: {total_expense:.2f} руб.\n"
                  f"Баланс: {balance:.2f} руб.\n\n"
                  f"Расходы по категориям:\n")

        categories = defaultdict(float)
        for exp in self.data["expenses"]:
            categories[exp["category"]] += exp["amount"]

        if categories:
            for cat, amt in categories.items():
                emoji = self._category_emoji(cat)
                report += f"{emoji} {cat}: {amt:.2f} руб.\n"
        else:
            report += "Нет расходов."

        return report

    def get_categories_report(self):
        categories = defaultdict(float)
        for exp in self.data["expenses"]:
            categories[exp["category"]] += exp["amount"]

        if not categories:
            return "Нет расходов."

        report = "📊 Расходы по категориям:\n"
        for cat, amt in categories.items():
            emoji = self._category_emoji(cat)
            report += f"{emoji} {cat}: {amt:.2f} руб.\n"
        return report

    def _category_emoji(self, category):
        # Простейшее соответствие категорий и эмодзи
        mapping = {
            "Еда": "🍔",
            "Транспорт": "🚗",
            "Развлечения": "🎉",
            "Коммуналка": "🏠",
            "Одежда": "👗",
            "Здоровье": "💊",
            "Образование": "📚",
            "Прочее": "🛍️",
        }
        return mapping.get(category, "❓")
