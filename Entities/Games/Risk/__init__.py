import random

from Commons.static_functions import make_command_json
from Commons import commands
from Entities.Games.base_multiplayer_game_class import BaseMultiPlayerGameClass


def roll_dice(dice_count):
    result = []
    for i in range(dice_count):
        result.append(random.randint(1, 6))
    return result


class RiskGameClass(BaseMultiPlayerGameClass):
    def __init__(self, send_data_function, players_count=2):
        super().__init__(send_data_function, players_count)
        self.players_out_pieces = []
        self.init_board()
        self.current_turn = 0
        self.current_dice = 0
        self.current_turn_player_rolled = False
        self.has_more_dice = False
        self.current_available_indexes = []

    def init_board(self):
        pass

    def get_game_data(self):
        data = {"players_out_pieces": self.players_out_pieces,
                "current_turn": self.current_turn, "active_player_indexes": self.active_player_indexes,
                'rank1': self.rank1, "current_dice": self.current_dice,
                "current_turn_player_rolled": self.current_turn_player_rolled, }
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print("here",command_id, data, gamer_id)
        if command_id == commands.Roll_Dice:
            pass
        elif command_id == commands.Select_Peace:
            pass
        return True

    def change_turn(self):
        self.current_available_indexes.clear()
        self.is_current_turn_played = False
        self.has_more_dice = False
        self.current_dice = 0
        self.current_turn_player_rolled = False
        super().change_turn()

    def get_game_winner(self):
        return 0

    def check_move_became_win(self):
        return None

    def check_authority(self, data, gamer_id: int):
        # if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2) or (
        #         self.current_turn == 3 and gamer_id != 3) or (self.current_turn == 4 and gamer_id != 4):
        #     print("not turn of : ", gamer_id)
        #     return False
        # if self.is_game_finished:
        #     return False
        return True
