"""
Bots module for Cafe Fekr Backend.
Provides access to game logics, human behavior simulation, and Classic Rank Bot Controller.
"""

from .bot_controller import ClassicRankBot
from .bot_data import get_random_bot_profile, PERSIAN_BOT_NAMES
from .games import get_game_logic, list_supported_games

__all__ = [
    "ClassicRankBot",
    "get_random_bot_profile",
    "PERSIAN_BOT_NAMES",
    "get_game_logic",
    "list_supported_games",
]
