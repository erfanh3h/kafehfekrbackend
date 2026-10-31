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

    def set_user_data(self, idis):
        self.players_idis = idis

    def finish_game(self, winner_gamer_id, game_types, game_winners):
        # -1 is when game terminated by not joining users
        if winner_gamer_id == -1:
            return
        self.game_types = game_types
        self.game_winners = game_winners
        self.last_awarded_xp = {}
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

        if len(self.players_idis) > 0:
            if winner_gamer_id == 0:
                p1_xp = draw_xp
                p1_score = draw_score
                p1_coin = draw_coin
            elif winner_gamer_id == 1:
                p1_xp = win_xp
                p1_score = win_score
                p1_coin = win_coin
            else:
                p1_xp = lose_xp
                p1_score = lose_score
                p1_coin = lose_coin
            self.last_awarded_xp[self.players_idis[0]] = p1_xp
            try:
                user1_data = game_database.users_manager.read_user(self.players_idis[0])
            except Exception:
                user1_data = None
            if user1_data is not None:
                game_database.users_manager.update_user(
                    self.players_idis[0],
                    score=user1_data.get('score', 0) + p1_score,
                    xp=user1_data.get('xp', 0) + p1_xp,
                    coin=user1_data.get('coin', 0) + p1_coin,
                    open_game_id="",
                    last_time_played=datetime.now()
                )

        if len(self.players_idis) > 1:
            if winner_gamer_id == 0:
                p2_xp = draw_xp
                p2_score = draw_score
                p2_coin = draw_coin
            elif winner_gamer_id == 2:
                p2_xp = win_xp
                p2_score = win_score
                p2_coin = win_coin
            else:
                p2_xp = lose_xp
                p2_score = lose_score
                p2_coin = lose_coin
            self.last_awarded_xp[self.players_idis[1]] = p2_xp
            try:
                user2_data = game_database.users_manager.read_user(self.players_idis[1])
            except Exception:
                user2_data = None
            if user2_data is not None:
                game_database.users_manager.update_user(
                    self.players_idis[1],
                    score=user2_data.get('score', 0) + p2_score,
                    xp=user2_data.get('xp', 0) + p2_xp,
                    coin=user2_data.get('coin', 0) + p2_coin,
                    open_game_id="",
                    last_time_played=datetime.now()
                )

        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        if is_rank:
            user1_history, user2_history = self.get_history_map(winner_gamer_id)
            if user1_data is not None:
                game_database.user_history_manager.update_user_history(self.players_idis[0], user1_history)
            if user2_data is not None:
                game_database.user_history_manager.update_user_history(self.players_idis[1], user2_history)

    def finish_multiplayer_game(self, rank1_gamer_id, rank2_gamer_id, game_types):
        self.game_types = game_types
        from Entities.Database import game_database
        if self.game_score_type == GameScoreTypesEnum.MultiRANK:
            rank1_coin, rank2_coin, rankn_coin, rank1_score, rank2_score, rankn_score, rank1_xp, rank2_xp, rankn_xp = (
                multi_rank_rank1_coin, multi_rank_rank2_coin, multi_rank_rankn_coin,
                multi_rank_rank1_score, multi_rank_rank2_score, multi_rank_rankn_score, multi_rank_rank1_xp,
                multi_rank_rank2_xp, multi_rank_rankn_xp,)
        else:
            rank1_coin, rank2_coin, rankn_coin, rank1_score, rank2_score, rankn_score, rank1_xp, rank2_xp, rankn_xp = (
                0, 0, 0, 0, 0, 0, 0, 0, 0)
        users_data = []
        for user_id in self.players_idis:
            user_data = game_database.users_manager.read_user(user_id)
            users_data.append(user_data)

        is_rank = self.game_score_type == GameScoreTypesEnum.MultiRANK
        if is_rank:
            user1_history, user2_history, user3_history, user4_history = self.get_multiplayer_history_map(
                rank1_gamer_id, rank2_gamer_id)
            if len(users_data) >= 1:
                game_database.user_history_manager.update_user_history_multiplayer(self.players_idis[0], user1_history)
            if len(users_data) >= 2:
                game_database.user_history_manager.update_user_history_multiplayer(self.players_idis[1], user2_history)
            if len(users_data) >= 3:
                game_database.user_history_manager.update_user_history_multiplayer(self.players_idis[2], user3_history)
            if len(users_data) >= 4:
                game_database.user_history_manager.update_user_history_multiplayer(self.players_idis[3], user4_history)

        if rank1_gamer_id == 1:
            user1_new_score = users_data[0]['score'] + rank1_score
            user1_new_xp = users_data[0]['xp'] + rank1_xp
            user1_new_coin = users_data[0]['coin'] + rank1_coin
        elif rank2_gamer_id == 1:
            user1_new_score = users_data[0]['score'] + rank2_score
            user1_new_xp = users_data[0]['xp'] + rank2_xp
            user1_new_coin = users_data[0]['coin'] + rank2_coin
        else:
            user1_new_score = users_data[0]['score'] + rankn_score
            user1_new_xp = users_data[0]['xp'] + rankn_xp
            user1_new_coin = users_data[0]['coin'] + rankn_coin
        game_database.users_manager.update_user(self.players_idis[0], score=user1_new_score, xp=user1_new_xp,
                                                coin=user1_new_coin, open_game_id="", last_time_played=datetime.now())
        if len(users_data) <= 1:
            return
        if rank1_gamer_id == 2:
            user2_new_score = users_data[1]['score'] + rank1_score
            user2_new_xp = users_data[1]['xp'] + rank1_xp
            user2_new_coin = users_data[1]['coin'] + rank1_coin
        elif rank2_gamer_id == 2:
            user2_new_score = users_data[1]['score'] + rank2_score
            user2_new_xp = users_data[1]['xp'] + rank2_xp
            user2_new_coin = users_data[1]['coin'] + rank2_coin
        else:
            user2_new_score = users_data[1]['score'] + rankn_score
            user2_new_xp = users_data[1]['xp'] + rankn_xp
            user2_new_coin = users_data[1]['coin'] + rankn_coin
        game_database.users_manager.update_user(self.players_idis[1], score=user2_new_score, xp=user2_new_xp,
                                                coin=user2_new_coin, open_game_id="", last_time_played=datetime.now())
        if len(users_data) <= 2:
            return
        if rank1_gamer_id == 3:
            user3_new_score = users_data[2]['score'] + rank1_score
            user3_new_xp = users_data[2]['xp'] + rank1_xp
            user3_new_coin = users_data[2]['coin'] + rank1_coin
        elif rank2_gamer_id == 3:
            user3_new_score = users_data[2]['score'] + rank2_score
            user3_new_xp = users_data[2]['xp'] + rank2_xp
            user3_new_coin = users_data[2]['coin'] + rank2_coin
        else:
            user3_new_score = users_data[2]['score'] + rankn_score
            user3_new_xp = users_data[2]['xp'] + rankn_xp
            user3_new_coin = users_data[2]['coin'] + rankn_coin
        game_database.users_manager.update_user(self.players_idis[2], score=user3_new_score, xp=user3_new_xp,
                                                coin=user3_new_coin, open_game_id="", last_time_played=datetime.now())
        if len(users_data) <= 3:
            return
        if rank1_gamer_id == 4:
            user4_new_score = users_data[3]['score'] + rank1_score
            user4_new_xp = users_data[3]['xp'] + rank1_xp
            user4_new_coin = users_data[3]['coin'] + rank1_coin
        elif rank2_gamer_id == 4:
            user4_new_score = users_data[3]['score'] + rank2_score
            user4_new_xp = users_data[3]['xp'] + rank2_xp
            user4_new_coin = users_data[3]['coin'] + rank2_coin
        else:
            user4_new_score = users_data[3]['score'] + rankn_score
            user4_new_xp = users_data[3]['xp'] + rankn_xp
            user4_new_coin = users_data[3]['coin'] + rankn_coin
        game_database.users_manager.update_user(self.players_idis[3], score=user4_new_score, xp=user4_new_xp,
                                                coin=user4_new_coin, open_game_id="", last_time_played=datetime.now())

    def get_history_map(self, total_game_winner):
        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        # is_lobby = self.game_score_type == GameScoreTypesEnum.LOBBY
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
                if self.game_winners[index] == 1:
                    user1_history[f"{game_type.lower()}_win"] = 1
                    user2_history[f"{game_type.lower()}_lose"] = 1
                elif self.game_winners[index] == 2:
                    user2_history[f"{game_type.lower()}_win"] = 1
                    user1_history[f"{game_type.lower()}_lose"] = 1
                else:
                    user1_history[f"{game_type.lower()}_draw"] = 1
                    user2_history[f"{game_type.lower()}_draw"] = 1
        else:
            pass
        return user1_history, user2_history

    def get_multiplayer_history_map(self, rank1_gamer_id, rank2_gamer_id):
        user1_history = {}
        user2_history = {}
        user3_history = {}
        user4_history = {}
        for index, game_type in enumerate(self.game_types):
            if rank1_gamer_id == self.players_idis[0]:
                user1_history[f"{game_type.lower()}_rank1"] = 1
            elif rank2_gamer_id == self.players_idis[0]:
                user1_history[f"{game_type.lower()}_rank2"] = 1
            else:
                user1_history[f"{game_type.lower()}_rankn"] = 1
            if rank1_gamer_id == self.players_idis[1]:
                user2_history[f"{game_type.lower()}_rank1"] = 1
            elif rank2_gamer_id == self.players_idis[1]:
                user2_history[f"{game_type.lower()}_rank2"] = 1
            else:
                user2_history[f"{game_type.lower()}_rankn"] = 1
            if len(self.players_idis) <= 2:
                continue
            if rank1_gamer_id == self.players_idis[2]:
                user3_history[f"{game_type.lower()}_rank1"] = 1
            elif rank2_gamer_id == self.players_idis[2]:
                user3_history[f"{game_type.lower()}_rank2"] = 1
            else:
                user1_history[f"{game_type.lower()}_rankn"] = 1
            if len(self.players_idis) <= 3:
                continue
            if rank1_gamer_id == self.players_idis[3]:
                user4_history[f"{game_type.lower()}_rank1"] = 1
            elif rank2_gamer_id == self.players_idis[3]:
                user4_history[f"{game_type.lower()}_rank2"] = 1
            else:
                user4_history[f"{game_type.lower()}_rankn"] = 1

        return user1_history, user2_history, user3_history, user4_history
