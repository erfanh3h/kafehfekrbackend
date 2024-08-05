from Entities.Games.game_types import GameTypesEnum
from Entities.ScoreManagerClass.game_score_types import GameScoreTypesEnum


class ScoreManagerClass:
    def __init__(self, game_score_type):
        self.player1_user_id = ""
        self.player2_user_id = ""
        self.game_type = GameTypesEnum.C
        self.game_score_type = game_score_type

    def set_data(self, player1_user_id, player2_user_id, game_type):
        self.player1_user_id = player1_user_id
        self.player2_user_id = player2_user_id
        self.game_type = game_type

    def finish_game(self, winner_gamer_id):
        print("winner  :  ", winner_gamer_id)
