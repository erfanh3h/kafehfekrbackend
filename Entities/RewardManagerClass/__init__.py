from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum
from Entities.RewardManagerClass import reward_data
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
        #-1 is when game terminated by not joining users
        if winner_gamer_id == -1:
            return
        from Entities.Database import game_database
        win_score, lose_score, draw_score, win_xp, lose_xp, draw_xp, win_coin, lose_coin, draw_coin = self.get_reward_data()
        user1_data = game_database.users_manager.read_user(self.player1_user_id)
        user2_data = game_database.users_manager.read_user(self.player2_user_id)
        if winner_gamer_id == 0:
            user1_new_score = user1_data['score'] + draw_score
            user1_new_xp = user1_data['xp'] + draw_xp
            user1_new_coin = user1_data['coin'] + draw_coin
            user1_history = {f"{str(self.game_type.value).lower()}_draw": 1, "draw": 1}
            user2_new_score = user2_data['score'] + draw_score
            user2_new_xp = user2_data['xp'] + draw_xp
            user2_new_coin = user2_data['coin'] + draw_coin
            user2_history = {f"{str(self.game_type.value).lower()}_draw": 1, "draw": 1}
        else:
            if winner_gamer_id == 1:
                user1_new_score = user1_data['score'] + win_score
                user1_new_xp = user1_data['xp'] + win_xp
                user1_new_coin = user1_data['coin'] + win_coin
                user1_history = {f"{str(self.game_type.value).lower()}_win": 1, "win": 1}
                user2_new_score = user2_data['score'] + lose_score
                user2_new_xp = user2_data['xp'] + lose_xp
                user2_new_coin = user2_data['coin'] + lose_coin
                user2_history = {f"{str(self.game_type.value).lower()}_lose": 1, "lose": 1}
            else:
                user2_new_score = user2_data['score'] + win_score
                user2_new_xp = user2_data['xp'] + win_xp
                user2_new_coin = user2_data['coin'] + win_coin
                user2_history = {f"{str(self.game_type.value).lower()}_win": 1, "win": 1}
                user1_new_score = user1_data['score'] + lose_score
                user1_new_xp = user1_data['xp'] + lose_xp
                user1_new_coin = user1_data['coin'] + lose_coin
                user1_history = {f"{str(self.game_type.value).lower()}_lose": 1, "lose": 1}
        game_database.users_manager.update_user(self.player1_user_id, score=user1_new_score, xp=user1_new_xp,
                                                coin=user1_new_coin, open_game_id="", last_time_played=datetime.now())
        game_database.users_manager.update_user(self.player2_user_id, score=user2_new_score, xp=user2_new_xp,
                                                coin=user2_new_coin, open_game_id="", last_time_played=datetime.now())
        game_database.user_history_manager.update_user_history(self.player1_user_id, user1_history)
        game_database.user_history_manager.update_user_history(self.player2_user_id, user2_history)
        game_database.game_history_manager.update_game_history(self.game_id, winner_gamer_id)
        print("winner  :  ", winner_gamer_id)

    def get_reward_data(self):
        # TODO : uncomment this
        is_rank = True
        # is_rank = self.game_score_type == GameScoreTypesEnum.RANK
        # is_lobby = self.game_score_type == GameScoreTypesEnum.LOBBY
        if self.game_type == GameTypesEnum.BACKGAMMON:
            if is_rank:
                return reward_data.backgammon_rank_data()
            else:
                return reward_data.backgammon_normal_data()
        elif self.game_type == GameTypesEnum.BATTLESHIP:
            if is_rank:
                return reward_data.battleship_rank_data()
            else:
                return reward_data.battleship_normal_data()
        elif self.game_type == GameTypesEnum.BOXFOUR:
            if is_rank:
                return reward_data.boxfour_rank_data()
            else:
                return reward_data.boxfour_normal_data()
        elif self.game_type == GameTypesEnum.CHECKERS:
            if is_rank:
                return reward_data.checkers_rank_data()
            else:
                return reward_data.checkers_normal_data()
        elif self.game_type == GameTypesEnum.CHESS:
            if is_rank:
                return reward_data.chess_rank_data()
            else:
                return reward_data.chess_normal_data()
        elif self.game_type == GameTypesEnum.DOTBOX:
            if is_rank:
                return reward_data.dotbox_rank_data()
            else:
                return reward_data.dotbox_normal_data()
        elif self.game_type == GameTypesEnum.FOURINROW:
            if is_rank:
                return reward_data.fourinrow_rank_data()
            else:
                return reward_data.fourinrow_normal_data()
        elif self.game_type == GameTypesEnum.MILL:
            if is_rank:
                return reward_data.mill_rank_data()
            else:
                return reward_data.mill_normal_data()
        elif self.game_type == GameTypesEnum.MNUMBERS:
            if is_rank:
                return reward_data.mnumbers_rank_data()
            else:
                return reward_data.mnumbers_normal_data()
        elif self.game_type == GameTypesEnum.MSweeper:
            if is_rank:
                return reward_data.msweeper_rank_data()
            else:
                return reward_data.msweeper_normal_data()
        elif self.game_type == GameTypesEnum.OTHELLO:
            if is_rank:
                return reward_data.othello_rank_data()
            else:
                return reward_data.othello_normal_data()
        elif self.game_type == GameTypesEnum.RPC:
            if is_rank:
                return reward_data.rpc_rank_data()
            else:
                return reward_data.rpc_normal_data()
        elif self.game_type == GameTypesEnum.SUDOKU:
            if is_rank:
                return reward_data.sudoku_rank_data()
            else:
                return reward_data.sudoku_normal_data()
        elif self.game_type == GameTypesEnum.TEN:
            if is_rank:
                return reward_data.ten_rank_data()
            else:
                return reward_data.ten_normal_data()
        elif self.game_type == GameTypesEnum.TIC_TAC_TOE:
            if is_rank:
                return reward_data.tictactoe_rank_data()
            else:
                return reward_data.tictactoe_normal_data()
        else:
            if is_rank:
                return reward_data.yatzy_rank_data()
            else:
                return reward_data.yatzy_normal_data()
