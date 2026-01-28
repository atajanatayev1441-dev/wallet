import os
from aiogram import Bot, Dispatcher, types, DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# Пример: старт и кнопка
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Присоединиться к игре", callback_data="join_game")
    kb.adjust(1)

    await message.answer("Привет! Добро пожаловать в Мафию. Нажми кнопку, чтобы присоединиться к игре.", reply_markup=kb.as_markup())

# Обработка нажатий на инлайн-кнопки
@dp.callback_query(lambda c: c.data == "join_game")
async def process_join_game(callback_query: types.CallbackQuery):
    await callback_query.answer("Ты присоединился к игре!")
    # Тут можно добавить логику добавления игрока в игру

# Запуск polling
async def main()
