import random

from Entities.Games.Ludo.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands

gamer_pieces_win_map = {1: {34: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            35: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            36: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            37: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            38: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            39: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        2: {14: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            15: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            16: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            17: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            18: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            19: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        3: {24: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            25: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            26: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            27: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            28: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            29: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        4: {4: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            5: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            6: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            7: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            8: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            9: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        }

gamer_win_indexes_map = {
    1: {34: {6: 40}, 35: {5: 40, 6: 41}, 36: {4: 40, 5: 41, 6: 42}, 37: {3: 40, 4: 41, 5: 42, 6: 43},
        38: {2: 40, 3: 41, 4: 42, 5: 43}, 39: {1: 40, 2: 41, 3: 42, 4: 43}},
    2: {14: {6: 44}, 15: {5: 44, 6: 45}, 16: {4: 44, 5: 45, 6: 46}, 17: {3: 44, 4: 45, 5: 46, 6: 47},
        18: {2: 44, 3: 45, 4: 46, 5: 47}, 19: {1: 44, 2: 45, 3: 46, 4: 47}},
    3: {24: {6: 48}, 25: {5: 48, 6: 49}, 26: {4: 48, 5: 49, 6: 50}, 27: {3: 48, 4: 49, 5: 50, 6: 51},
        28: {2: 48, 3: 49, 4: 50, 5: 51}, 29: {1: 48, 2: 49, 3: 50, 4: 51}},
    4: {4: {6: 52}, 5: {5: 52, 6: 53}, 6: {4: 52, 5: 53, 6: 54}, 7: {3: 52, 4: 53, 5: 54, 6: 55},
        8: {2: 52, 3: 53, 4: 54, 5: 55}, 9: {1: 52, 2: 53, 3: 54, 4: 55}},
}


def roll_dices():
    return random.randint(1, 6)


def is_valid_index(index):
    if 0 <= index < 40:
        return True
    return False


def is_valid_index_in_end_phase(index, gamer_id):
    if gamer_id == 1:
        if 0 <= index <= 40:
            return True
    if gamer_id == 2:
        if -1 <= index < 40:
            return True
    return False


class LudoGameClass(BaseGameClass):
    def __init__(self, send_data_function, players_count=2):
        super().__init__(send_data_function)
        self.board = [BoardSpotClass() for i in range(56)]  # 0 : 40 , normals , 40 : 55 win pieces
        self.players_count = players_count
        self.players_out_pieces = []
        self.init_board()
        self.current_turn = 1
        self.current_dice = 0
        self.current_turn_player_rolled = False
        self.has_more_dice = False
        self.current_available_indexes = []

    def init_board(self):
        for i in range(self.players_count):
            self.players_out_pieces.append(4)

    def get_game_data(self):
        board_data = []
        for index in range(0, len(self.board)):
            # check peace equiped or not
            board_data.append(self.board[index].to_json())

        data = {"board": board_data, "players_out_pieces": self.players_out_pieces, "current_turn": self.current_turn,
                "current_dice": self.current_dice, "current_turn_player_rolled": self.current_turn_player_rolled, }
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print(command_id, data, gamer_id)
        if command_id == commands.Roll_Dice:
            self.current_dice = data['dice']
            # self.current_dice = roll_dices()
            self.current_turn_player_rolled = True
            if self.current_dice == 6:
                self.has_more_dice = True
        if command_id == commands.Select_Peace:
            index = data['index']
            self.move_piece(index)

    def get_game_winner(self):
        winner = super().get_game_winner()
        return winner

    def change_turn(self):
        self.is_current_turn_played = False
        self.has_more_dice = False
        self.current_dice = 0
        self.current_turn_player_rolled = False
        if self.current_turn == 1:
            self.current_turn = 2
        if self.players_count == 4:
            if self.current_turn == 2:
                self.current_turn = 3
            if self.current_turn == 3:
                self.current_turn = 4
            else:
                self.current_turn = 1
        if self.players_count == 3:
            if self.current_turn == 2:
                self.current_turn = 3
            else:
                self.current_turn = 1
        else:
            self.current_turn = 1

    def check_game_ended(self):
        return False

    def move_piece(self, index):
        gamer_id = self.board[index].equipped_user
        target_index = 0
        if index == -1:  # enter game from out
            if gamer_id == 1:
                target_index = self.current_dice
            elif gamer_id == 2:
                target_index = 20 + self.current_dice
            elif gamer_id == 3:
                target_index = 30 + self.current_dice
            elif gamer_id == 4:
                target_index = 10 + self.current_dice
            self.players_out_pieces[gamer_id - 1] -= 1
        elif (gamer_id == 1 and index <= 33) or (gamer_id == 2 and (index <= 13 or index >= 20)) or (
                gamer_id == 3 and (index <= 23 or index >= 30)) or (gamer_id == 4 and (index <= 3 or index >= 10)):
            target_index = (index + self.current_dice) % 40
            self.board[index].clear()
        else:
            is_index_winable = gamer_pieces_win_map[gamer_id - 1][index][self.current_dice]
            if is_index_winable is None:
                pass
            elif is_index_winable:
                target_index = gamer_win_indexes_map[gamer_id][index][self.current_dice]
            else:
                target_index = (index + self.current_dice) % 40
        if target_index < 40:  # win not happens
            if (gamer_id != 1 and target_index == 0) or (gamer_id != 2 and target_index == 20) or (
                    gamer_id != 3 and target_index == 30) or (
                    gamer_id != 4 and target_index == 10):  # other players cant enter others home
                target_index += 1
            if self.board[target_index].is_enemy_spot(gamer_id):  # hit enemy
                enemy_index = self.board[target_index].equipped_user
                enemy_count = self.board[target_index].count
                self.players_out_pieces[enemy_index] += enemy_count
                self.board[target_index].clear()
        self.board[target_index].add_piece(gamer_id)

    def get_my_piece_indexes(self, gamer_id):
        result = []
        for index in range(0, len(self.board)):
            if self.board[index].is_gamer_id_spot(gamer_id):
                result.append(index)
        return result

    def check_index_available(self, index):
        gamer_id = self.board[index].equipped_user
        if gamer_id == 1 and index <= 33:
            return True
        if gamer_id == 2 and (index <= 13 or index >= 20):
            return True
        if gamer_id == 3 and (index <= 23 or index >= 30):
            return True
        if gamer_id == 4 and (index <= 3 or index >= 10):
            return True
        is_index_winable = gamer_pieces_win_map[gamer_id - 1][index][self.current_dice]
        if is_index_winable is None:
            return False
        if is_index_winable:
            win_index = gamer_win_indexes_map[gamer_id - 1][index][self.current_dice]
            if self.board[win_index].is_empty():
                return True
            return False
        return True

    def set_available_move(self, gamer_id):
        pieces = self.get_my_piece_indexes(gamer_id)
        for piece_index in pieces:
            if self.check_index_available(piece_index):
                self.current_available_indexes.append(piece_index)
        have_piece_out = self.check_gamer_piece_is_out(gamer_id)
        if have_piece_out:
            self.current_available_indexes.append(-1)

    def check_gamer_piece_is_out(self, gamer_id):
        if self.players_out_pieces[gamer_id - 1] > 0:
            return True
        return False

    def check_authority(self, data, gamer_id: int):
        # if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2) or (
        #         self.current_turn == 3 and gamer_id != 3) or (self.current_turn == 4 and gamer_id != 4):
        #     print("not turn of : ", gamer_id)
        #     return False
        # if self.is_game_finished:
        #     return False
        return True
