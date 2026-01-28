import random
from game.models import Player
from game.phases import *
from game.roles import ROLES

class Game:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players: dict[int, Player] = {}
        self.phase = LOBBY

    def add_player(self, user_id, name):
        if self.phase != LOBBY or user_id in self.players:
            return False
        self.players[user_id] = Player(user_id, name)
        return True

    def start(self):
        count = len(self.players)
        if count < 6 or count > 20:
            return False

        roles = (
            ["mafia"] * max(1, count // 4)
            + ["doctor"]
            + ["detective"]
        )

        while len(roles) < count:
            roles.append("civilian")

        random.shuffle(roles)

        for player, role in zip(self.players.values(), roles):
            player.role = role

        self.phase = NIGHT
        return True

    def alive_players(self):
        return [p for p in self.players.values() if p.alive]

    def check_win(self):
        mafia = [p for p in self.alive_players() if p.role == "mafia"]
        others = [p for p in self.alive_players() if p.role != "mafia"]

        if not mafia:
            return "Мирные победили 🎉"
        if len(mafia) >= len(others):
            return "Мафия победила 😈"
        return None
