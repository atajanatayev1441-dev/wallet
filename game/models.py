from dataclasses import dataclass

@dataclass
class Player:
    user_id: int
    name: str
    role: str = ""
    alive: bool = True
    vote: int | None = None
    night_target: int | None = None
