from typing import Optional
from telegram import User
from solitaire_game import Game

class TelegramUser:
    id: int
    full_name: str
    username: str
    # each user can have at most one ongoing game at a time
    game: Optional[Game]

    def __init__(self, effective_user: User, game = None):
        self.id = effective_user.id
        self.full_name = effective_user.full_name
        self.username = effective_user.username
        self.game = game
