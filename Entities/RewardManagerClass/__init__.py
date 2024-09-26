from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum
from Entities.RewardManagerClass.reward_data import gametype_to_rewards
from datetime import datetime


class RewardManagerClass:
    def __init__(self, game_score_type, game_id, game_type):
        self.player1_user_id = ""
        self.player2_user_id = ""
        self.game_score_type = game_score_type
        self.game_id = game_id
        self.game_type = game_type

    def set_user_data(self, player1_user_id, player2_user_id):
        self.player1_user_id = player1_user_id
        self.player2_user_id = player2_user_id

    def finish_game(self, winner_gamer_id):
        return
        # -1 is when game terminated by not joining users
        if winner_gamer_id == -1:
            return
        from Entities.Database import game_database
        if self.game_score_type == GameScoreTypesEnum.RANK:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                self.get_rank_reward_data())
        else:
            win_coin, lose_coin, draw_coin, win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp = (
                0, 0, 0, 0, 0, 0, 2, 0, 0)
        user1_data = game_database.users_manager.read_user(self.player1_user_id)
        user2_data = game_database.users_manager.read_user(self.player2_user_id)
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
        user1_history, user2_history = self.get_history_map(winner_gamer_id)
        game_database.users_manager.update_user(self.player1_user_id, score=user1_new_score, xp=user1_new_xp,
                                                coin=user1_new_coin, open_game_id="", last_time_played=datetime.now())
        game_database.users_manager.update_user(self.player2_user_id, score=user2_new_score, xp=user2_new_xp,
                                                coin=user2_new_coin, open_game_id="", last_time_played=datetime.now())
        game_database.user_history_manager.update_user_history(self.player1_user_id, user1_history)
        game_database.user_history_manager.update_user_history(self.player2_user_id, user2_history)
        game_database.game_history_manager.update_game_history(self.game_id, winner_gamer_id)
        print("winner  :  ", winner_gamer_id)

    def get_history_map(self, winner):
        is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        # is_lobby = self.game_score_type == GameScoreTypesEnum.LOBBY
        if is_rank:
            if winner == 0:
                user1_history = {f"{str(self.game_type.value).lower()}_draw": 1, "draw_rank": 1}
                user2_history = {f"{str(self.game_type.value).lower()}_draw": 1, "draw_rank": 1}
            else:
                if winner == 1:
                    user1_history = {f"{str(self.game_type.value).lower()}_win": 1, "win_rank": 1}
                    user2_history = {f"{str(self.game_type.value).lower()}_lose": 1, "lose_rank": 1}
                else:
                    user2_history = {f"{str(self.game_type.value).lower()}_win": 1, "win_rank": 1}
                    user1_history = {f"{str(self.game_type.value).lower()}_lose": 1, "lose_rank": 1}
        else:
            if winner == 0:
                user1_history = {"draw_normal": 1}
                user2_history = {"draw_normal": 1}
            else:
                if winner == 1:
                    user1_history = {"win_normal": 1}
                    user2_history = {"lose_normal": 1}
                else:
                    user2_history = {"win_normal": 1}
                    user1_history = {"lose_normal": 1}
        return user1_history, user2_history

    def get_rank_reward_data(self):
        data = gametype_to_rewards(self.game_type.value)
        return data[0], 0, (data[0] / 3).__ceil__(), data[1], -1 * data[1], (data[1] / 4), data[2], data[4], data[3]
