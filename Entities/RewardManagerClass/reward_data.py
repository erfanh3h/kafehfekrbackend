from Commons.static_functions import gametype_to_difficulty
from Entities.Games.game_difficulty import GameDifficultyEnum

rank_coin_cost = 15
rank_win_coin = 15
rank_draw_coin = 5
rank_win_score = 10
rank_draw_score = 0
rank_lose_score = -5
rank_win_xp = 8
rank_draw_xp = 4
rank_lose_xp = 2


def gametype_to_rewards(game_type):
    difficulty = gametype_to_difficulty(game_type)
    if difficulty == GameDifficultyEnum.Easy:
        return 10, 8, 4, 2, 1
    if difficulty == GameDifficultyEnum.Normal:
        return 15, 16, 8, 3, 2
    if difficulty == GameDifficultyEnum.Hard:
        return 20, 24, 12, 4, 3
