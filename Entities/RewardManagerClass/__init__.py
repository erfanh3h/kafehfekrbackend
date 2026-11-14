from datetime import datetime

from Commons.static_functions import gametype_to_difficulty
from Entities.Games.game_difficulty import GameDifficultyEnum
from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum
from Entities.RewardManagerClass.reward_data import (
    rank_win_coin, rank_lose_coin, rank_draw_coin, rank_coin_cost,
    multi_rank_coin_cost, multi_rank_rank1_coin, multi_rank_rank2_coin,
    multi_rank_rank3_coin, multi_rank_rankn_coin,
    multi_rank_rank1_score, multi_rank_rank2_score, multi_rank_rank3_score, multi_rank_rankn_score,
    multi_rank_rank1_xp, multi_rank_rank2_xp, multi_rank_rank3_xp, multi_rank_rankn_xp,
    calculate_elo_change, calculate_rank_series_xp, calculate_social_xp,
    DAILY_FIRST_WIN_XP, DAILY_FIRST_WIN_COIN, WIN_STREAK_XP_BONUS
)


class RewardManagerClass:
    def __init__(self, game_score_type):
        self.players_idis = []
        self.game_score_type = game_score_type
        self.game_types = []
        self.game_winners = []
        self.last_awarded_xp = {}
        self.last_awarded_score = {}
        self.last_awarded_coin = {}

    def set_user_data(self, idis):
        self.players_idis = idis

    def finish_game(self, winner_gamer_id, game_types, game_winners, gamer_scores=None, afk_or_dc_user_id=None, leaver_user_id=None):
        # -1 indicates game was terminated before start (e.g. user never joined)
        if winner_gamer_id == -1:
            return

        if winner_gamer_id not in [0, 1, 2]:
            if len(self.players_idis) > 0 and str(winner_gamer_id) == str(self.players_idis[0]):
                winner_gamer_id = 1
            elif len(self.players_idis) > 1 and str(winner_gamer_id) == str(self.players_idis[1]):
                winner_gamer_id = 2
            else:
                winner_gamer_id = 0

        self.game_types = game_types
        self.game_winners = game_winners
        self.last_awarded_xp = {}
        self.last_awarded_score = {}
        self.last_awarded_coin = {}

        from Entities.Database import game_database

        num_players = min(2, len(self.players_idis))
        users_data = {}
        for idx in range(num_players):
            uid = self.players_idis[idx]
            if not str(uid).startswith("bot_"):
                try:
                    users_data[str(uid)] = game_database.users_manager.read_user(uid)
                except Exception as e:
                    print(f"[RewardManager] Error reading user {uid}: {e}")
                    users_data[str(uid)] = None
            else:
                users_data[str(uid)] = None

        is_clean_sweep = (
            gamer_scores is not None and
            len(gamer_scores) >= 2 and
            (gamer_scores[:2] == [2, 0] or gamer_scores[:2] == [0, 2])
        )

        uid0 = self.players_idis[0] if len(self.players_idis) > 0 else None
        uid1 = self.players_idis[1] if len(self.players_idis) > 1 else None
        u0 = users_data.get(str(uid0)) if uid0 else None
        u1 = users_data.get(str(uid1)) if uid1 else None

        # Surrenders are normal losses - ONLY full disconnect timeout or AFK triggers penalty!
        penalty_uid = afk_or_dc_user_id
        is_penalty_0 = (penalty_uid is not None and uid0 is not None and str(uid0) == str(penalty_uid))
        is_penalty_1 = (penalty_uid is not None and uid1 is not None and str(uid1) == str(penalty_uid))

        now = datetime.now()
        rewards_map = {}

        if self.game_score_type == GameScoreTypesEnum.RANK:
            s0 = u0.get('score', 0) if u0 else 0
            s1 = u1.get('score', 0) if u1 else 0

            # Dynamic Elo Calculation (Surrender is a normal loss; only AFK/DC gets penalty)
            delta_0, delta_1 = calculate_elo_change(
                s0, s1, winner_gamer_id,
                is_clean_sweep=is_clean_sweep,
                is_afk_or_dc_a=is_penalty_0,
                is_afk_or_dc_b=is_penalty_1
            )

            # Enhanced Main Rank Series EXP (Surrender receives normal series loss EXP)
            xp_0 = calculate_rank_series_xp(
                game_types, game_winners, winner_gamer_id,
                gamer_index=0, is_clean_sweep=is_clean_sweep, is_afk_or_dc=is_penalty_0
            )
            xp_1 = calculate_rank_series_xp(
                game_types, game_winners, winner_gamer_id,
                gamer_index=1, is_clean_sweep=is_clean_sweep, is_afk_or_dc=is_penalty_1
            )

            # Coins
            if is_penalty_0:
                coin_0 = 0
            elif winner_gamer_id == 1:
                coin_0 = rank_win_coin
            elif winner_gamer_id == 0:
                coin_0 = rank_draw_coin
            else:
                coin_0 = rank_lose_coin

            if is_penalty_1:
                coin_1 = 0
            elif winner_gamer_id == 2:
                coin_1 = rank_win_coin
            elif winner_gamer_id == 0:
                coin_1 = rank_draw_coin
            else:
                coin_1 = rank_lose_coin

            # Win Streaks and Daily First Win Bonuses
            streak_0, daily_win_0 = 0, None
            if u0:
                daily_win_0 = u0.get('last_daily_win')
                if winner_gamer_id == 1 and not is_penalty_0:
                    streak_0 = u0.get('win_streak', 0) + 1
                    if streak_0 >= 2:
                        streak_bonus = min((streak_0 - 1) * 2, 6)
                        delta_0 += streak_bonus
                        xp_0 += WIN_STREAK_XP_BONUS
                    if daily_win_0 is None or not isinstance(daily_win_0, datetime) or daily_win_0.date() < now.date():
                        xp_0 += DAILY_FIRST_WIN_XP
                        coin_0 += DAILY_FIRST_WIN_COIN
                        daily_win_0 = now
                elif winner_gamer_id == 0:
                    streak_0 = u0.get('win_streak', 0)
                else:
                    streak_0 = 0

            streak_1, daily_win_1 = 0, None
            if u1:
                daily_win_1 = u1.get('last_daily_win')
                if winner_gamer_id == 2 and not is_penalty_1:
                    streak_1 = u1.get('win_streak', 0) + 1
                    if streak_1 >= 2:
                        streak_bonus = min((streak_1 - 1) * 2, 6)
                        delta_1 += streak_bonus
                        xp_1 += WIN_STREAK_XP_BONUS
                    if daily_win_1 is None or not isinstance(daily_win_1, datetime) or daily_win_1.date() < now.date():
                        xp_1 += DAILY_FIRST_WIN_XP
                        coin_1 += DAILY_FIRST_WIN_COIN
                        daily_win_1 = now
                elif winner_gamer_id == 0:
                    streak_1 = u1.get('win_streak', 0)
                else:
                    streak_1 = 0

            rewards_map[str(uid0)] = (xp_0, delta_0, coin_0, streak_0, daily_win_0)
            rewards_map[str(uid1)] = (xp_1, delta_1, coin_1, streak_1, daily_win_1)

        elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            g_type = game_types[0] if game_types else ""
            diff = gametype_to_difficulty(g_type)
            if diff == GameDifficultyEnum.Easy:
                win_xp, draw_xp, lose_xp = 8, 4, 2
            elif diff == GameDifficultyEnum.Normal:
                win_xp, draw_xp, lose_xp = 14, 7, 3
            else:
                win_xp, draw_xp, lose_xp = 20, 10, 5

            for idx in range(num_players):
                uid = self.players_idis[idx]
                gamer_num = idx + 1
                is_penalty = (penalty_uid is not None and str(uid) == str(penalty_uid))
                if is_penalty:
                    p_xp = 0
                elif winner_gamer_id == 0:
                    p_xp = draw_xp
                elif winner_gamer_id == gamer_num:
                    p_xp = win_xp
                else:
                    p_xp = lose_xp
                rewards_map[str(uid)] = (p_xp, 0, 0, None, None)

        else:
            # LOBBY and NORMAL: Social progression EXP only, STRICTLY 0 Coins and 0 Score
            g_type = game_types[0] if game_types else ""
            for idx in range(num_players):
                uid = self.players_idis[idx]
                gamer_num = idx + 1
                is_penalty = (penalty_uid is not None and str(uid) == str(penalty_uid))
                is_win = (winner_gamer_id == gamer_num)
                is_draw = (winner_gamer_id == 0)
                p_xp = calculate_social_xp(g_type, is_win=is_win, is_draw=is_draw, is_afk_or_dc=is_penalty)
                rewards_map[str(uid)] = (p_xp, 0, 0, None, None)

        # Update database and populate last_awarded dicts
        for idx in range(num_players):
            uid = self.players_idis[idx]
            p_xp, p_score, p_coin, p_streak, p_daily_win = rewards_map.get(str(uid), (0, 0, 0, None, None))

            self.last_awarded_xp[uid] = p_xp
            self.last_awarded_score[uid] = p_score
            self.last_awarded_coin[uid] = p_coin

            if str(uid).startswith("bot_"):
                continue

            user_data = users_data.get(str(uid))
            try:
                if user_data is not None:
                    update_kwargs = {
                        "score": max(0, user_data.get('score', 0) + p_score),
                        "xp": max(0, user_data.get('xp', 0) + p_xp),
                        "coin": max(0, user_data.get('coin', 0) + p_coin),
                        "open_game_id": "",
                        "last_time_played": datetime.now()
                    }
                    if p_streak is not None:
                        update_kwargs["win_streak"] = p_streak
                    if p_daily_win is not None:
                        update_kwargs["last_daily_win"] = p_daily_win

                    game_database.users_manager.update_user(uid, **update_kwargs)
                else:
                    game_database.users_manager.update_user(uid, open_game_id="")
                # Clan contribution tracking (Ranked/Classic Rank modes with anti-farming protection)
                is_ranked_mode = self.game_score_type in (GameScoreTypesEnum.RANK, GameScoreTypesEnum.CLASSIC_RANK)
                if is_ranked_mode and hasattr(game_database, "clans_manager"):
                    opp_ids = [str(other) for other in self.players_idis if str(other) != str(uid) and not str(other).startswith("bot_")]
                    gamer_num = idx + 1
                    is_win_match = (winner_gamer_id == gamer_num)
                    game_database.clans_manager.record_member_match_contribution(
                        user_id=str(uid),
                        is_win=is_win_match,
                        xp_earned=max(0, p_xp),
                        score_earned=max(0, p_score),
                        opponent_ids=opp_ids,
                        is_ranked=True,
                    )
            except Exception as e:
                print(f"[RewardManager] Error updating user {uid}: {e}")

        # Update User History (only for RANK and CLASSIC_RANK; LOBBY and NORMAL are strictly excluded)
        if self.game_score_type == GameScoreTypesEnum.RANK and len(self.players_idis) >= 2:
            try:
                user1_history, user2_history = self.get_history_map(winner_gamer_id)
                if not str(self.players_idis[0]).startswith("bot_"):
                    game_database.user_history_manager.update_user_history(self.players_idis[0], user1_history)
                if not str(self.players_idis[1]).startswith("bot_"):
                    game_database.user_history_manager.update_user_history(self.players_idis[1], user2_history)
            except Exception as e:
                print(f"[RewardManager] Error updating rank history: {e}")
        elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            try:
                classic_histories = self.get_classic_rank_history_map(winner_gamer_id, game_types)
                for idx, h_data in classic_histories.items():
                    if idx < len(self.players_idis):
                        uid = self.players_idis[idx]
                        if not str(uid).startswith("bot_"):
                            game_database.user_history_manager.update_user_history(uid, h_data)
            except Exception as e:
                print(f"[RewardManager] Error updating classic rank history: {e}")

    def finish_multiplayer_game(self, rank1_gamer_id, rank2_gamer_id, game_types):
        self.game_types = game_types
        self.last_awarded_xp = {}
        self.last_awarded_score = {}
        self.last_awarded_coin = {}

        from Entities.Database import game_database

        users_data = []
        for user_id in self.players_idis:
            if str(user_id).startswith("bot_"):
                users_data.append(None)
                continue
            try:
                user_data = game_database.users_manager.read_user(user_id)
            except Exception:
                user_data = None
            users_data.append(user_data)

        if self.game_score_type == GameScoreTypesEnum.MultiRANK:
            try:
                histories = self.get_multiplayer_history_map(rank1_gamer_id, rank2_gamer_id)
                for idx, uid in enumerate(self.players_idis[:4]):
                    if idx < len(users_data) and users_data[idx] is not None and not str(uid).startswith("bot_"):
                        game_database.user_history_manager.update_user_history_multiplayer(uid, histories[idx])
            except Exception as e:
                print(f"[RewardManager] Error updating multiplayer history: {e}")
        elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            try:
                classic_histories = self.get_classic_rank_history_map(rank1_gamer_id, game_types)
                for idx, h_data in classic_histories.items():
                    if idx < len(self.players_idis):
                        uid = self.players_idis[idx]
                        if not str(uid).startswith("bot_"):
                            game_database.user_history_manager.update_user_history(uid, h_data)
            except Exception as e:
                print(f"[RewardManager] Error updating classic rank multiplayer history: {e}")

        total_players = min(4, len(self.players_idis))
        now = datetime.now()

        is_total_draw = rank1_gamer_id in (0, None, "0", "")

        for idx, uid in enumerate(self.players_idis[:total_players]):
            gamer_num = idx + 1
            is_r1 = (not is_total_draw) and ((rank1_gamer_id == gamer_num) or (str(rank1_gamer_id) == str(uid)))
            is_r2 = (not is_total_draw) and (rank2_gamer_id not in (0, None, "0", "")) and ((rank2_gamer_id == gamer_num) or (str(rank2_gamer_id) == str(uid)))

            u_data = users_data[idx] if idx < len(users_data) else None
            daily_win_update = None

            if self.game_score_type == GameScoreTypesEnum.MultiRANK:
                if is_total_draw:
                    d_score = 0
                    d_xp = 15
                    d_coin = 0
                elif is_r1:
                    d_score = multi_rank_rank1_score  # +12
                    d_xp = multi_rank_rank1_xp        # +50
                    d_coin = multi_rank_rank1_coin    # +25
                    # Daily first win bonus for Rank 1
                    if u_data:
                        last_win = u_data.get('last_daily_win')
                        if last_win is None or not isinstance(last_win, datetime) or last_win.date() < now.date():
                            d_xp += DAILY_FIRST_WIN_XP
                            d_coin += DAILY_FIRST_WIN_COIN
                            daily_win_update = now
                elif is_r2:
                    d_score = multi_rank_rank2_score  # +4
                    d_xp = multi_rank_rank2_xp        # +30
                    d_coin = multi_rank_rank2_coin    # +15
                else:
                    # 3rd or 4th place
                    if total_players == 3:
                        d_score = -6
                        d_xp = 15
                        d_coin = 0
                    else:
                        if idx == 2:
                            d_score = multi_rank_rank3_score  # -4
                            d_xp = multi_rank_rank3_xp        # +15
                            d_coin = multi_rank_rank3_coin    # 0
                        else:
                            d_score = multi_rank_rankn_score  # -8
                            d_xp = multi_rank_rankn_xp        # +10
                            d_coin = multi_rank_rankn_coin    # 0

            elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
                g_type = game_types[0] if game_types else ""
                diff = gametype_to_difficulty(g_type)
                if diff == GameDifficultyEnum.Easy:
                    r1_xp, r2_xp, rn_xp, draw_xp = 15, 8, 4, 6
                elif diff == GameDifficultyEnum.Normal:
                    r1_xp, r2_xp, rn_xp, draw_xp = 25, 14, 7, 10
                else:
                    r1_xp, r2_xp, rn_xp, draw_xp = 40, 20, 10, 15

                d_score, d_coin = 0, 0
                if is_total_draw:
                    d_xp = draw_xp
                elif is_r1:
                    d_xp = r1_xp
                elif is_r2:
                    d_xp = r2_xp
                else:
                    d_xp = rn_xp

            else:
                # LOBBY / NORMAL Multiplayer: Social EXP only, STRICTLY 0 Coins and 0 Score
                d_score, d_coin = 0, 0
                if is_total_draw:
                    d_xp = 10
                elif is_r1:
                    d_xp = 20
                elif is_r2:
                    d_xp = 12
                elif idx == 2:
                    d_xp = 6
                else:
                    d_xp = 4

            self.last_awarded_xp[uid] = d_xp
            self.last_awarded_score[uid] = d_score
            self.last_awarded_coin[uid] = d_coin

            if str(uid).startswith("bot_"):
                continue

            try:
                if u_data is not None:
                    update_kwargs = {
                        "score": max(0, u_data.get('score', 0) + d_score),
                        "xp": max(0, u_data.get('xp', 0) + d_xp),
                        "coin": max(0, u_data.get('coin', 0) + d_coin),
                        "open_game_id": "",
                        "last_time_played": datetime.now()
                    }
                    if daily_win_update is not None:
                        update_kwargs["last_daily_win"] = daily_win_update

                    game_database.users_manager.update_user(uid, **update_kwargs)
                else:
                    game_database.users_manager.update_user(uid, open_game_id="")
                is_ranked_multi = self.game_score_type in (GameScoreTypesEnum.MultiRANK, GameScoreTypesEnum.CLASSIC_RANK)
                if is_ranked_multi and hasattr(game_database, "clans_manager"):
                    opp_ids = [str(other) for other in self.players_idis[:total_players] if str(other) != str(uid) and not str(other).startswith("bot_")]
                    game_database.clans_manager.record_member_match_contribution(
                        user_id=str(uid),
                        is_win=bool(is_r1),
                        xp_earned=max(0, d_xp),
                        score_earned=max(0, d_score),
                        opponent_ids=opp_ids,
                        is_ranked=True,
                    )
            except Exception as e:
                print(f"[RewardManager] Error updating multiplayer user {uid}: {e}")

    def get_history_map(self, total_game_winner):
        user1_history = {}
        user2_history = {}
        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        if is_rank:
            if total_game_winner == 0:
                user1_history["draw_rank"] = 1
                user2_history["draw_rank"] = 1
            else:
                if total_game_winner == 1:
                    user1_history["win_rank"] = 1
                    user2_history["lose_rank"] = 1
                else:
                    user2_history["win_rank"] = 1
                    user1_history["lose_rank"] = 1
            for index, game_type in enumerate(self.game_types):
                if index >= len(self.game_winners):
                    continue
                sub_w = self.game_winners[index]
                if sub_w == -1:
                    continue
                gt_lower = str(game_type).lower()
                if sub_w == 1:
                    user1_history[f"{gt_lower}_win"] = user1_history.get(f"{gt_lower}_win", 0) + 1
                    user2_history[f"{gt_lower}_lose"] = user2_history.get(f"{gt_lower}_lose", 0) + 1
                elif sub_w == 2:
                    user2_history[f"{gt_lower}_win"] = user2_history.get(f"{gt_lower}_win", 0) + 1
                    user1_history[f"{gt_lower}_lose"] = user1_history.get(f"{gt_lower}_lose", 0) + 1
                else:
                    user1_history[f"{gt_lower}_draw"] = user1_history.get(f"{gt_lower}_draw", 0) + 1
                    user2_history[f"{gt_lower}_draw"] = user2_history.get(f"{gt_lower}_draw", 0) + 1
        return user1_history, user2_history

    def get_classic_rank_history_map(self, winner_gamer_id, game_types=None):
        histories = {}
        g_types = game_types or self.game_types
        g_type = g_types[0] if g_types else ""
        gt_lower = str(g_type).lower()

        total_players = min(4, len(self.players_idis))
        for idx in range(total_players):
            uid = self.players_idis[idx]
            if str(uid).startswith("bot_") or str(uid).startswith("test_bot"):
                continue
            gamer_num = idx + 1
            h = {}
            is_win = (winner_gamer_id == gamer_num) or (winner_gamer_id is not None and str(winner_gamer_id) == str(uid))
            if winner_gamer_id == 0:
                h["draw_classic_rank"] = 1
                if gt_lower:
                    h[f"{gt_lower}_draw"] = 1
            elif is_win:
                h["win_classic_rank"] = 1
                if gt_lower:
                    h[f"{gt_lower}_win"] = 1
            else:
                h["lose_classic_rank"] = 1
                if gt_lower:
                    h[f"{gt_lower}_lose"] = 1
            histories[idx] = h

        return histories

    def get_multiplayer_history_map(self, rank1_gamer_id, rank2_gamer_id):
        user1_history = {}
        user2_history = {}
        user3_history = {}
        user4_history = {}
        histories = [user1_history, user2_history, user3_history, user4_history]
        total_players = min(4, len(self.players_idis))

        for index, game_type in enumerate(self.game_types):
            gt_lower = str(game_type).lower()
            for p_idx in range(total_players):
                uid = self.players_idis[p_idx]
                if str(uid).startswith("bot_") or str(uid).startswith("test_bot"):
                    continue
                g_num = p_idx + 1
                is_r1 = (rank1_gamer_id == g_num) or (rank1_gamer_id not in (0, None, "0", "") and str(rank1_gamer_id) == str(uid))
                is_r2 = (rank2_gamer_id == g_num) or (rank2_gamer_id not in (0, None, "0", "") and str(rank2_gamer_id) == str(uid))

                if rank1_gamer_id in (0, None, "0", ""):
                    histories[p_idx]["draw_multi_rank"] = histories[p_idx].get("draw_multi_rank", 0) + 1
                    histories[p_idx][f"{gt_lower}_draw"] = histories[p_idx].get(f"{gt_lower}_draw", 0) + 1
                elif is_r1:
                    histories[p_idx]["win_multi_rank"] = histories[p_idx].get("win_multi_rank", 0) + 1
                    histories[p_idx]["rank1_multi_rank"] = histories[p_idx].get("rank1_multi_rank", 0) + 1
                    histories[p_idx][f"{gt_lower}_win"] = histories[p_idx].get(f"{gt_lower}_win", 0) + 1
                    histories[p_idx][f"{gt_lower}_rank1"] = histories[p_idx].get(f"{gt_lower}_rank1", 0) + 1
                elif is_r2:
                    histories[p_idx]["lose_multi_rank"] = histories[p_idx].get("lose_multi_rank", 0) + 1
                    histories[p_idx]["rank2_multi_rank"] = histories[p_idx].get("rank2_multi_rank", 0) + 1
                    histories[p_idx][f"{gt_lower}_lose"] = histories[p_idx].get(f"{gt_lower}_lose", 0) + 1
                    histories[p_idx][f"{gt_lower}_rank2"] = histories[p_idx].get(f"{gt_lower}_rank2", 0) + 1
                else:
                    histories[p_idx]["lose_multi_rank"] = histories[p_idx].get("lose_multi_rank", 0) + 1
                    histories[p_idx]["rankn_multi_rank"] = histories[p_idx].get("rankn_multi_rank", 0) + 1
                    histories[p_idx][f"{gt_lower}_lose"] = histories[p_idx].get(f"{gt_lower}_lose", 0) + 1
                    histories[p_idx][f"{gt_lower}_rankn"] = histories[p_idx].get(f"{gt_lower}_rankn", 0) + 1
        return user1_history, user2_history, user3_history, user4_history
