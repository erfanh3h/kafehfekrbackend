from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum
from datetime import datetime

from Entities.RewardManagerClass.reward_data import rank_win_coin, rank_lose_xp, rank_win_xp, rank_lose_score, \
    rank_draw_score, rank_draw_xp, rank_coin_cost, rank_draw_coin, rank_win_score


class RewardManagerClass:
    def __init__(self, game_score_type):
        self.players_idis = []
        self.game_score_type = game_score_type
        self.game_types = []
        self.game_winners = []

    def set_user_data(self, idis):
        self.players_idis = idis

    def finish_game(self, winner_gamer_id, game_types, game_winners):
        # -1 is when game terminated by not joining users
        if winner_gamer_id == -1:
            return
        self.game_types = game_types
        self.game_winners = game_winners
        from Entities.Database import game_database
        if self.game_score_type == GameScoreTypesEnum.RANK:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                rank_win_coin, 0, rank_draw_coin, rank_win_score, rank_lose_score, rank_draw_score, rank_win_xp,
                rank_lose_xp, rank_draw_xp)
        else:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                0, 0, 0, 0, 0, 0, 0, 0, 0)
        user1_data = game_database.users_manager.read_user(self.players_idis[0])
        user2_data = game_database.users_manager.read_user(self.players_idis[1])
        if winner_gamer_id == 0:
            user1_new_score = user1_data['score'] + draw_score
            user1_new_xp = user1_data['xp'] + draw_xp
            user1_new_coin = user1_data['coin'] + draw_coin
            user2_new_score = user2_data['score'] + draw_score
            user2_new_xp = user2_data['xp'] + draw_xp
            user2_new_coin = user2_data['coin'] + draw_coin
        else:
            if winner_gamer_id == 1:
                user1_new_score = user1_data['score'] + win_score
                user1_new_xp = user1_data['xp'] + win_xp
                user1_new_coin = user1_data['coin'] + win_coin
                user2_new_score = user2_data['score'] + lose_score
                user2_new_xp = user2_data['xp'] + lose_xp
                user2_new_coin = user2_data['coin'] + lose_coin
            else:
                user2_new_score = user2_data['score'] + win_score
                user2_new_xp = user2_data['xp'] + win_xp
                user2_new_coin = user2_data['coin'] + win_coin
                user1_new_score = user1_data['score'] + lose_score
                user1_new_xp = user1_data['xp'] + lose_xp
                user1_new_coin = user1_data['coin'] + lose_coin
        game_database.users_manager.update_user(self.players_idis[0], score=user1_new_score, xp=user1_new_xp,
                                                coin=user1_new_coin, open_game_id="", last_time_played=datetime.now())
        game_database.users_manager.update_user(self.players_idis[1], score=user2_new_score, xp=user2_new_xp,
                                                coin=user2_new_coin, open_game_id="", last_time_played=datetime.now())
        is_lobby = self.game_score_type == GameScoreTypesEnum.LOBBY
        if not is_lobby:
            user1_history, user2_history = self.get_history_map(winner_gamer_id)
            game_database.user_history_manager.update_user_history(self.players_idis[0], user1_history)
            game_database.user_history_manager.update_user_history(self.players_idis[1], user2_history)

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
