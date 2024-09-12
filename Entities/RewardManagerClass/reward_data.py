from Commons.static_functions import gametype_to_difficulty
from Entities.Games.game_difficulty import GameDifficultyEnum


def gametype_to_rewards(game_type):
    difficulty = gametype_to_difficulty(game_type)
    if difficulty == GameDifficultyEnum.Easy:
        return 10, 8, 4, 2, 1
    if difficulty == GameDifficultyEnum.Normal:
        return 15, 16, 8, 3, 2
    if difficulty == GameDifficultyEnum.Hard:
        return 20, 24, 12, 4, 3
