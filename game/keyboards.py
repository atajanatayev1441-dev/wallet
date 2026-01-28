from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def players_kb(players, action):
    buttons = [
        [InlineKeyboardButton(text=p.name, callback_data=f"{action}:{p.user_id}")]
        for p in players if p.alive
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
