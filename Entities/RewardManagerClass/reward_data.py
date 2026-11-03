import math
from datetime import datetime

from Commons.static_functions import gametype_to_difficulty
from Entities.Games.game_difficulty import GameDifficultyEnum

# Basic Rank Constants
rank_coin_cost = 15
rank_win_coin = 15
rank_draw_coin = 5
rank_lose_coin = 0

rank_win_score = 10
rank_draw_score = 0
rank_lose_score = -5

rank_win_xp = 15
rank_draw_xp = 12
rank_lose_xp = 10

# MultiRank Constants
multi_rank_coin_cost = 15
multi_rank_rank1_coin = 25
multi_rank_rank2_coin = 15
multi_rank_rank3_coin = 0
multi_rank_rankn_coin = 0

multi_rank_rank1_score = 12
multi_rank_rank2_score = 4
multi_rank_rank3_score = -4
multi_rank_rankn_score = -8

multi_rank_rank1_xp = 25
multi_rank_rank2_xp = 15
multi_rank_rank3_xp = 8
multi_rank_rankn_xp = 4

# Streak and Daily First Win Bonuses
DAILY_FIRST_WIN_XP = 15
DAILY_FIRST_WIN_COIN = 15
WIN_STREAK_XP_BONUS = 8


def calculate_elo_change(
    score_a: int,
    score_b: int,
    winner_gamer_id: int,
    is_clean_sweep: bool = False,
    is_afk_or_dc_a: bool = False,
    is_afk_or_dc_b: bool = False
) -> tuple[int, int]:
    """
    Computes dynamic Elo rating adjustments for 1v1 RANK series.
    winner_gamer_id: 1 if Player A won, 2 if Player B won, 0 for Draw.
    Surrender counts as a NORMAL loss (is_afk_or_dc is False).
    Only full disconnect timeout or AFK incurs harsh penalty (is_afk_or_dc is True).
    Returns: (delta_a, delta_b)
    """
    score_a = max(0, int(score_a))
    score_b = max(0, int(score_b))

    diff = (score_b - score_a) / 400.0
    diff = max(-10.0, min(10.0, diff))
    ea = 1.0 / (1.0 + math.pow(10.0, diff))
    eb = 1.0 - ea

    k_base = 20.0

    if winner_gamer_id == 1:
        # Player A won
        delta_a = k_base * (1.0 - ea)
        if is_clean_sweep:
            delta_a *= 1.15
        delta_a = max(2, min(25, round(delta_a)))

        # Player B lost
        # Beginner protection: if B has low score (< 300), softer K
        k_b = 12.0 if score_b < 300 else 20.0
        delta_b = -round(k_b * eb)
        delta_b = min(-2, max(-20, delta_b))

        # Harsh penalty ONLY for AFK or full disconnect
        if is_afk_or_dc_b:
            delta_b = min(delta_b, -15)

    elif winner_gamer_id == 2:
        # Player B won
        delta_b = k_base * (1.0 - eb)
        if is_clean_sweep:
            delta_b *= 1.15
        delta_b = max(2, min(25, round(delta_b)))

        # Player A lost
        k_a = 12.0 if score_a < 300 else 20.0
        delta_a = -round(k_a * ea)
        delta_a = min(-2, max(-20, delta_a))

        # Harsh penalty ONLY for AFK or full disconnect
        if is_afk_or_dc_a:
            delta_a = min(delta_a, -15)

    else:
        # Draw (winner_gamer_id == 0)
        delta_a = round(k_base * (0.5 - ea))
        delta_b = round(k_base * (0.5 - eb))

    return int(delta_a), int(delta_b)


def calculate_rank_series_xp(
    game_types: list,
    game_winners: list,
    winner_gamer_id: int,
    gamer_index: int,
    is_clean_sweep: bool = False,
    is_afk_or_dc: bool = False
) -> int:
    """
    Computes series EXP for 1v1 RANK match.
    Surrender is a normal loss and receives normal series loss EXP.
    Only full disconnect timeout or AFK receives 0 XP.
    """
    if is_afk_or_dc:
        return 0

    gamer_num = gamer_index + 1
    total_xp = 0

    # Sub-game XP based on difficulty and individual game outcome
    for idx, g_type in enumerate(game_types):
        diff = gametype_to_difficulty(g_type)
        sub_winner = game_winners[idx] if idx < len(game_winners) else -1
        if sub_winner == -1:
            continue

        if diff == GameDifficultyEnum.Easy:
            win_val, draw_val, lose_val = 8, 5, 3
        elif diff == GameDifficultyEnum.Normal:
            win_val, draw_val, lose_val = 12, 7, 4
        else:  # Hard
            win_val, draw_val, lose_val = 16, 10, 6

        if sub_winner == 0:
            total_xp += draw_val
        elif sub_winner == gamer_num:
            total_xp += win_val
        else:
            total_xp += lose_val

    # Series outcome bonus
    if winner_gamer_id == 0:
        total_xp += 8  # Series Draw
    elif winner_gamer_id == gamer_num:
        total_xp += 15  # Series Winner
        if is_clean_sweep:
            total_xp += 5  # Clean sweep (2-0) bonus
    else:
        total_xp += 5  # Series Completion effort reward (surrenders receive this normally)

    return max(0, total_xp)


def calculate_social_xp(game_type: str, is_win: bool, is_draw: bool, is_afk_or_dc: bool = False) -> int:
    """
    Calculates EXP for LOBBY and NORMAL matches. Strictly 0 coins and 0 score.
    """
    if is_afk_or_dc:
        return 0

    diff = gametype_to_difficulty(game_type)
    if diff == GameDifficultyEnum.Easy:
        win_xp, draw_xp, lose_xp = 5, 2, 1
    elif diff == GameDifficultyEnum.Normal:
        win_xp, draw_xp, lose_xp = 9, 4, 2
    else:  # Hard
        win_xp, draw_xp, lose_xp = 14, 7, 3

    if is_draw:
        return draw_xp
    elif is_win:
        return win_xp
    else:
        return lose_xp


def gametype_to_rewards(game_type):
    difficulty = gametype_to_difficulty(game_type)
    if difficulty == GameDifficultyEnum.Easy:
        return 10, 8, 4, 2, 1
    if difficulty == GameDifficultyEnum.Normal:
        return 15, 16, 8, 3, 2
    if difficulty == GameDifficultyEnum.Hard:
        return 20, 24, 12, 4, 3
