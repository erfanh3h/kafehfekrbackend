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

# Classic Rank AI Opponent Levels & Reward Scaling
CLASSIC_RANK_DEFAULT_AI_LEVEL = 2
CLASSIC_RANK_AI_LEVELS = (1, 2, 3)

CLASSIC_RANK_REWARDS_TABLE = {
    1: {  # Easy AI (آسان)
        GameDifficultyEnum.Easy.value: {"win_xp": 6, "draw_xp": 3, "lose_xp": 1, "win_coin": 2, "draw_coin": 0, "lose_coin": 0},
        GameDifficultyEnum.Normal.value: {"win_xp": 9, "draw_xp": 4, "lose_xp": 2, "win_coin": 2, "draw_coin": 1, "lose_coin": 0},
        GameDifficultyEnum.Hard.value: {"win_xp": 12, "draw_xp": 6, "lose_xp": 2, "win_coin": 3, "draw_coin": 1, "lose_coin": 0},
    },
    2: {  # Medium AI (متوسط - Default)
        GameDifficultyEnum.Easy.value: {"win_xp": 10, "draw_xp": 5, "lose_xp": 2, "win_coin": 4, "draw_coin": 1, "lose_coin": 0},
        GameDifficultyEnum.Normal.value: {"win_xp": 15, "draw_xp": 7, "lose_xp": 3, "win_coin": 5, "draw_coin": 2, "lose_coin": 0},
        GameDifficultyEnum.Hard.value: {"win_xp": 22, "draw_xp": 11, "lose_xp": 5, "win_coin": 6, "draw_coin": 2, "lose_coin": 0},
    },
    3: {  # Hard AI (سخت)
        GameDifficultyEnum.Easy.value: {"win_xp": 16, "draw_xp": 8, "lose_xp": 4, "win_coin": 7, "draw_coin": 3, "lose_coin": 0},
        GameDifficultyEnum.Normal.value: {"win_xp": 24, "draw_xp": 12, "lose_xp": 5, "win_coin": 9, "draw_coin": 4, "lose_coin": 0},
        GameDifficultyEnum.Hard.value: {"win_xp": 35, "draw_xp": 17, "lose_xp": 8, "win_coin": 12, "draw_coin": 5, "lose_coin": 0},
    },
}


def normalize_ai_level(level) -> int:
    """Normalizes AI opponent difficulty level to 1 (Easy), 2 (Medium, default), or 3 (Hard)."""
    if isinstance(level, bool):
        return CLASSIC_RANK_DEFAULT_AI_LEVEL
    if isinstance(level, (int, float)):
        lvl_int = int(level)
        return lvl_int if lvl_int in CLASSIC_RANK_AI_LEVELS else CLASSIC_RANK_DEFAULT_AI_LEVEL
    if isinstance(level, str):
        s = level.strip().lower()
        if s in ("1", "easy", "beginner", "lvl1", "level1"):
            return 1
        if s in ("2", "medium", "normal", "intermediate", "lvl2", "level2"):
            return 2
        if s in ("3", "hard", "master", "expert", "lvl3", "level3"):
            return 3
        try:
            lvl_int = int(s)
            return lvl_int if lvl_int in CLASSIC_RANK_AI_LEVELS else CLASSIC_RANK_DEFAULT_AI_LEVEL
        except ValueError:
            return CLASSIC_RANK_DEFAULT_AI_LEVEL
    return CLASSIC_RANK_DEFAULT_AI_LEVEL


def get_classic_rank_reward_profile(game_type: str, ai_level=CLASSIC_RANK_DEFAULT_AI_LEVEL) -> dict:
    """Returns win/draw/lose XP and coin rewards for a Classic Rank match."""
    lvl = normalize_ai_level(ai_level)
    diff = gametype_to_difficulty(game_type)
    diff_key = diff.value if hasattr(diff, "value") else str(diff)
    level_table = CLASSIC_RANK_REWARDS_TABLE.get(lvl, CLASSIC_RANK_REWARDS_TABLE[CLASSIC_RANK_DEFAULT_AI_LEVEL])
    return dict(level_table.get(diff_key, level_table[GameDifficultyEnum.Normal.value]))


def calculate_classic_rank_rewards(
    game_type: str,
    ai_level=CLASSIC_RANK_DEFAULT_AI_LEVEL,
    outcome: str = "win",
    is_afk_or_dc: bool = False,
) -> tuple[int, int]:
    """
    Computes (xp, coin) rewards for Classic Rank based on AI opponent level and game difficulty.
    outcome: 'win' | 'draw' | 'lose'
    AFK or disconnect timeout always receives (0, 0).
    """
    if is_afk_or_dc:
        return 0, 0
    profile = get_classic_rank_reward_profile(game_type, ai_level=ai_level)
    out = str(outcome or "lose").strip().lower()
    if out == "win":
        return int(profile["win_xp"]), int(profile["win_coin"])
    if out == "draw":
        return int(profile["draw_xp"]), int(profile["draw_coin"])
    return int(profile["lose_xp"]), int(profile["lose_coin"])


# Classic Rank Anti-Farming / Early Surrender Guard
CLASSIC_RANK_MIN_ELAPSED_SEC_WITH_MOVES = 45.0
CLASSIC_RANK_MIN_ACTIONS_FOR_TIME = 3
CLASSIC_RANK_MIN_ELAPSED_SEC_DEEP_PLAY = 90.0
CLASSIC_RANK_MIN_ROUNDS_FOR_SURRENDER = 3
CLASSIC_RANK_MIN_ACTIONS_FAST_GAME = 6
CLASSIC_RANK_MIN_ELAPSED_SEC_FLOOR = 25.0


def is_classic_rank_surrender_reward_eligible(
    elapsed_seconds: float,
    player_actions: int = 0,
    rounds_played: int = 1,
) -> bool:
    """
    Returns True when a surrendering player in Classic Rank engaged genuinely enough
    to receive defeat rewards, blocking quick-quit / early-turn XP & coin farming.

    Eligible when at least 1 real gameplay action was taken AND any of:
    - Elapsed >= 90s (long match / deep thinking), OR
    - Elapsed >= 45s AND player_actions >= 3, OR
    - Elapsed >= 25s AND (rounds_played >= 3 OR player_actions >= 6).
    """
    elapsed = max(0.0, float(elapsed_seconds or 0.0))
    actions = max(0, int(player_actions or 0))
    rounds = max(1, int(rounds_played or 1))

    if actions <= 0:
        return False
    if elapsed >= CLASSIC_RANK_MIN_ELAPSED_SEC_DEEP_PLAY:
        return True
    if elapsed >= CLASSIC_RANK_MIN_ELAPSED_SEC_WITH_MOVES and actions >= CLASSIC_RANK_MIN_ACTIONS_FOR_TIME:
        return True
    if elapsed >= CLASSIC_RANK_MIN_ELAPSED_SEC_FLOOR and (
        rounds >= CLASSIC_RANK_MIN_ROUNDS_FOR_SURRENDER or actions >= CLASSIC_RANK_MIN_ACTIONS_FAST_GAME
    ):
        return True
    return False


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
