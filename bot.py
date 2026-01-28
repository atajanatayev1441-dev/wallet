import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN, NIGHT_TIME, DAY_TIME, VOTING_TIME
from game.manager import Game
from game.keyboards import players_kb
from game.phases import *

bot = Bot(BOT_TOKEN, parse_mode="Markdown")
dp = Dispatcher()

games: dict[int, Game] = {}

@dp.message(Command("create"))
async def create_game(message: types.Message):
    games[message.chat.id] = Game(message.chat.id)
    await message.answer("🎲 Игра создана! /join")

@dp.message(Command("join"))
async def join_game(message: types.Message):
    game = games.get(message.chat.id)
    if not game:
        return
    if game.add_player(message.from_user.id, message.from_user.first_name):
        await message.answer(f"✅ {message.from_user.first_name} в игре")

@dp.message(Command("startgame"))
async def start_game(message: types.Message):
    game = games.get(message.chat.id)
    if not game or not game.start():
        return await message.answer("❌ Нужно 6–20 игроков")

    await message.answer("🌙 Наступает ночь. Все действия — в личке.")
    await night_phase(game)

async def night_phase(game: Game):
    game.phase = NIGHT

    for p in game.alive_players():
        if p.role == "mafia":
            await bot.send_message(p.user_id, "🔪 Выбери жертву", reply_markup=players_kb(game.alive_players(), "kill"))
        elif p.role == "doctor":
            await bot.send_message(p.user_id, "💉 Кого лечим?", reply_markup=players_kb(game.alive_players(), "heal"))
        elif p.role == "detective":
            await bot.send_message(p.user_id, "🕵️ Кого проверить?", reply_markup=players_kb(game.alive_players(), "check"))

    await asyncio.sleep(NIGHT_TIME)
    await resolve_night(game)

@dp.callback_query(F.data.startswith(("kill", "heal", "check", "vote")))
async def actions(call: types.CallbackQuery):
    action, target = call.data.split(":")
    game = next((g for g in games.values() if call.from_user.id in g.players), None)
    if not game:
        return

    player = game.players[call.from_user.id]
    player.night_target = int(target)
    await call.answer("✅ Принято")

    if action == "check":
        role = game.players[int(target)].role
        await call.message.answer(f"🔍 Роль: {role}")

async def resolve_night(game: Game):
    kills = []
    heals = []

    for p in game.alive_players():
        if p.role == "mafia" and p.night_target:
            kills.append(p.night_target)
        if p.role == "doctor" and p.night_target:
            heals.append(p.night_target)

    victim = max(set(kills), key=kills.count) if kills else None
    if victim and victim not in heals:
        game.players[victim].alive = False
        await bot.send_message(game.chat_id, f"☠️ Ночью погиб {game.players[victim].name}")
    else:
        await bot.send_message(game.chat_id, "🌅 Все выжили этой ночью")

    await day_phase(game)

async def day_phase(game: Game):
    game.phase = DAY
    await bot.send_message(game.chat_id, "☀️ День. Обсуждение.")
    await asyncio.sleep(DAY_TIME)
    await voting_phase(game)

async def voting_phase(game: Game):
    game.phase = VOTING
    for p in game.alive_players():
        await bot.send_message(p.user_id, "🗳 Голосуй", reply_markup=players_kb(game.alive_players(), "vote"))

    await asyncio.sleep(VOTING_TIME)
    votes = {}

    for p in game.alive_players():
        if p.night_target:
            votes[p.night_target] = votes.get(p.night_target, 0) + 1

    if votes:
        executed = max(votes, key=votes.get)
        game.players[executed].alive = False
        await bot.send_message(game.chat_id, f"⚖️ Казнён {game.players[executed].name}")

    winner = game.check_win()
    if winner:
        await bot.send_message(game.chat_id, f"🏁 {winner}")
        game.phase = ENDED
    else:
        await night_phase(game)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
