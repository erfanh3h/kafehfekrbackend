from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum
from datetime import datetime

from Entities.RewardManagerClass.reward_data import rank_win_coin, rank_lose_xp, rank_win_xp, rank_lose_score, \
    rank_draw_score, rank_draw_xp, rank_coin_cost, rank_draw_coin, rank_win_score, multi_rank_coin_cost, \
    multi_rank_rank1_coin, multi_rank_rank2_coin, multi_rank_rankn_coin, multi_rank_rank1_score, multi_rank_rankn_score, \
    multi_rank_rank1_xp, multi_rank_rank2_xp, multi_rank_rankn_xp, multi_rank_rank2_score


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

    def finish_game(self, winner_gamer_id, game_types, game_winners):
        # -1 is when game terminated by not joining users
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
        if self.game_score_type == GameScoreTypesEnum.RANK:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                rank_win_coin, 0, rank_draw_coin, rank_win_score, rank_lose_score, rank_draw_score, rank_win_xp,
                rank_lose_xp, rank_draw_xp)
        elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            from Commons.static_functions import gametype_to_difficulty
            from Entities.Games.game_difficulty import GameDifficultyEnum
            g_type = game_types[0] if game_types else ""
            diff = gametype_to_difficulty(g_type)
            if diff == GameDifficultyEnum.Easy:
                win_xp, draw_xp, lose_xp = 15, 8, 4
            elif diff == GameDifficultyEnum.Normal:
                win_xp, draw_xp, lose_xp = 25, 14, 7
            else:
                win_xp, draw_xp, lose_xp = 40, 20, 10
            win_coin, lose_coin, draw_coin = 0, 0, 0
            win_score, lose_score, draw_score = 0, 0, 0
        else:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                0, 0, 0, 0, 0, 0, 0, 0, 0)

        for idx in range(min(2, len(self.players_idis))):
            uid = self.players_idis[idx]
            gamer_num = idx + 1
            if winner_gamer_id == 0:
                p_xp, p_score, p_coin = draw_xp, draw_score, draw_coin
            elif winner_gamer_id == gamer_num:
                p_xp, p_score, p_coin = win_xp, win_score, win_coin
            else:
                p_xp, p_score, p_coin = lose_xp, lose_score, lose_coin

            self.last_awarded_xp[uid] = p_xp
            self.last_awarded_score[uid] = p_score
            self.last_awarded_coin[uid] = p_coin

            if str(uid).startswith("bot_"):
                continue

            user_data = None
            try:
                user_data = game_database.users_manager.read_user(uid)
            except Exception as e:
                print(f"[RewardManager] Error reading user {uid}: {e}")

            try:
                if user_data is not None:
                    game_database.users_manager.update_user(
                        uid,
                        score=user_data.get('score', 0) + p_score,
                        xp=user_data.get('xp', 0) + p_xp,
                        coin=user_data.get('coin', 0) + p_coin,
                        open_game_id="",
                        last_time_played=datetime.now()
                    )
                else:
                    game_database.users_manager.update_user(uid, open_game_id="")
            except Exception as e:
                print(f"[RewardManager] Error updating user {uid}: {e}")

        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        if is_rank and len(self.players_idis) >= 2:
            try:
                user1_history, user2_history = self.get_history_map(winner_gamer_id)
                if not str(self.players_idis[0]).startswith("bot_"):
                    game_database.user_history_manager.update_user_history(self.players_idis[0], user1_history)
                if not str(self.players_idis[1]).startswith("bot_"):
                    game_database.user_history_manager.update_user_history(self.players_idis[1], user2_history)
            except Exception as e:
                print(f"[RewardManager] Error updating rank history: {e}")

    def finish_multiplayer_game(self, rank1_gamer_id, rank2_gamer_id, game_types):
        self.game_types = game_types
        self.last_awarded_xp = {}
        self.last_awarded_score = {}
        self.last_awarded_coin = {}
        from Entities.Database import game_database
        if self.game_score_type == GameScoreTypesEnum.MultiRANK:
            rank1_coin, rank2_coin, rankn_coin, rank1_score, rank2_score, rankn_score, rank1_xp, rank2_xp, rankn_xp = (
                multi_rank_rank1_coin, multi_rank_rank2_coin, multi_rank_rankn_coin,
                multi_rank_rank1_score, multi_rank_rank2_score, multi_rank_rankn_score, multi_rank_rank1_xp,
                multi_rank_rank2_xp, multi_rank_rankn_xp,)
        elif self.game_score_type == GameScoreTypesEnum.CLASSIC_RANK:
            from Commons.static_functions import gametype_to_difficulty
            from Entities.Games.game_difficulty import GameDifficultyEnum
            g_type = game_types[0] if game_types else ""
            diff = gametype_to_difficulty(g_type)
            if diff == GameDifficultyEnum.Easy:
                rank1_xp, rank2_xp, rankn_xp = 15, 4, 4
            elif diff == GameDifficultyEnum.Normal:
                rank1_xp, rank2_xp, rankn_xp = 25, 7, 7
            else:
                rank1_xp, rank2_xp, rankn_xp = 40, 10, 10
            rank1_coin, rank2_coin, rankn_coin = 0, 0, 0
            rank1_score, rank2_score, rankn_score = 0, 0, 0
        else:
            rank1_coin, rank2_coin, rankn_coin, rank1_score, rank2_score, rankn_score, rank1_xp, rank2_xp, rankn_xp = (
                0, 0, 0, 0, 0, 0, 0, 0, 0)

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

        is_rank = self.game_score_type == GameScoreTypesEnum.MultiRANK
        if is_rank:
            try:
                histories = self.get_multiplayer_history_map(rank1_gamer_id, rank2_gamer_id)
                for idx, uid in enumerate(self.players_idis[:4]):
                    if idx < len(users_data) and users_data[idx] is not None and not str(uid).startswith("bot_"):
                        game_database.user_history_manager.update_user_history_multiplayer(uid, histories[idx])
            except Exception as e:
                print(f"[RewardManager] Error updating multiplayer history: {e}")

        for idx, uid in enumerate(self.players_idis[:4]):
            gamer_num = idx + 1
            is_r1 = (rank1_gamer_id == gamer_num) or (rank1_gamer_id is not None and str(rank1_gamer_id) == str(uid))
            is_r2 = (rank2_gamer_id == gamer_num) or (rank2_gamer_id is not None and str(rank2_gamer_id) == str(uid))
            if is_r1:
                d_score, d_xp, d_coin = rank1_score, rank1_xp, rank1_coin
            elif is_r2:
                d_score, d_xp, d_coin = rank2_score, rank2_xp, rank2_coin
            else:
                d_score, d_xp, d_coin = rankn_score, rankn_xp, rankn_coin

            self.last_awarded_xp[uid] = d_xp
            self.last_awarded_score[uid] = d_score
            self.last_awarded_coin[uid] = d_coin

            if str(uid).startswith("bot_"):
                continue

            u_data = users_data[idx] if idx < len(users_data) else None
            try:
                if u_data is not None:
                    game_database.users_manager.update_user(
                        uid,
                        score=u_data.get('score', 0) + d_score,
                        xp=u_data.get('xp', 0) + d_xp,
                        coin=u_data.get('coin', 0) + d_coin,
                        open_game_id="",
                        last_time_played=datetime.now()
                    )
                else:
                    game_database.users_manager.update_user(uid, open_game_id="")
            except Exception as e:
                print(f"[RewardManager] Error updating multiplayer user {uid}: {e}")

    def get_history_map(self, total_game_winner):
        user1_history = {}
        user2_history = {}
        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        if is_rank:
            if total_game_winner == 0:
                user1_history = {"draw_rank": 1}
                user2_history = {"draw_rank": 1}
            else:
                if total_game_winner == 1:
                    user1_history = {"win_rank": 1}
                    user2_history = {"lose_rank": 1}
                else:
                    user2_history = {"win_rank": 1}
                    user1_history = {"lose_rank": 1}
            for index, game_type in enumerate(self.game_types):
                if index >= len(self.game_winners):
                    continue
                if self.game_winners[index] == 1:
                    user1_history[f"{game_type.lower()}_win"] = 1
                    user2_history[f"{game_type.lower()}_lose"] = 1
                elif self.game_winners[index] == 2:
                    user2_history[f"{game_type.lower()}_win"] = 1
                    user1_history[f"{game_type.lower()}_lose"] = 1
                else:
                    user1_history[f"{game_type.lower()}_draw"] = 1
                    user2_history[f"{game_type.lower()}_draw"] = 1
        return user1_history, user2_history

    def get_multiplayer_history_map(self, rank1_gamer_id, rank2_gamer_id):
        user1_history = {}
        user2_history = {}
        user3_history = {}
        user4_history = {}
        histories = [user1_history, user2_history, user3_history, user4_history]
        for index, game_type in enumerate(self.game_types):
            for p_idx in range(min(4, len(self.players_idis))):
                uid = self.players_idis[p_idx]
                g_num = p_idx + 1
                if rank1_gamer_id == g_num or (rank1_gamer_id is not None and str(rank1_gamer_id) == str(uid)):
                    histories[p_idx][f"{game_type.lower()}_rank1"] = 1
                elif rank2_gamer_id == g_num or (rank2_gamer_id is not None and str(rank2_gamer_id) == str(uid)):
                    histories[p_idx][f"{game_type.lower()}_rank2"] = 1
                else:
                    histories[p_idx][f"{game_type.lower()}_rankn"] = 1
        return user1_history, user2_history, user3_history, user4_history
