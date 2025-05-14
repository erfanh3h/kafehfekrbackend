import random

from Entities.Games.Ludo.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands

gamer_pieces_win_map = {1: {30: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            31: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            32: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            33: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            34: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            35: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        2: {12: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            13: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            14: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            15: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            16: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            17: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        3: {21: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            22: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            23: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            24: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            25: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            26: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        4: {3: {1: False, 2: False, 3: False, 4: False, 5: False, 6: True},
                            4: {1: False, 2: False, 3: False, 4: False, 5: True, 6: True},
                            5: {1: False, 2: False, 3: False, 4: True, 5: True, 6: True},
                            6: {1: False, 2: False, 3: True, 4: True, 5: True, 6: True},
                            7: {1: False, 2: True, 3: True, 4: True, 5: True, 6: None},
                            8: {1: True, 2: True, 3: True, 4: True, 5: None, 6: None}},
                        }

gamer_win_indexes_map = {
    1: {30: {6: 36}, 31: {5: 36, 6: 37}, 32: {4: 36, 5: 37, 6: 38}, 33: {3: 36, 4: 37, 5: 38, 6: 39},
        34: {2: 36, 3: 37, 4: 38, 5: 39}, 35: {1: 46, 2: 37, 3: 38, 4: 39}},
    2: {12: {6: 40}, 13: {5: 40, 6: 41}, 14: {4: 40, 5: 41, 6: 42}, 15: {3: 40, 4: 41, 5: 42, 6: 43},
        16: {2: 40, 3: 41, 4: 42, 5: 43}, 17: {1: 40, 2: 41, 3: 42, 4: 43}},
    3: {21: {6: 44}, 22: {5: 44, 6: 45}, 23: {4: 44, 5: 45, 6: 46}, 24: {3: 44, 4: 45, 5: 46, 6: 47},
        25: {2: 44, 3: 45, 4: 46, 5: 47}, 26: {1: 44, 2: 45, 3: 46, 4: 47}},
    4: {3: {6: 48}, 4: {5: 48, 6: 49}, 5: {4: 48, 5: 49, 6: 50}, 6: {3: 48, 4: 49, 5: 50, 6: 51},
        7: {2: 48, 3: 49, 4: 50, 5: 51}, 8: {1: 48, 2: 49, 3: 50, 4: 51}},
}


def roll_dices():
    return random.randint(1, 6)


def is_valid_index(index):
    if 0 <= index < 36:
        return True
    return False


def is_valid_index_in_end_phase(index, gamer_id):
    if gamer_id == 1:
        if 0 <= index <= 36:
            return True
    if gamer_id == 2:
        if -1 <= index < 36:
            return True
    return False


class LudoGameClass(BaseGameClass):
    def __init__(self, send_data_function, players_count=2):
        super().__init__(send_data_function)
        self.board = [BoardSpotClass() for i in range(52)]  # 0 : 36 , normals , 36 : 51 win pieces
        self.start_pieces = []  # 4 start piece for each user
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
            self.start_pieces.append(BoardSpotClass())

    def get_game_data(self):
        board_data = []
        start_board_data = []
        for index in range(0, len(self.board)):
            board_data.append(self.board[index].to_json())
        for index in range(0, len(self.start_pieces)):
            start_board_data.append(self.start_pieces[index].to_json())

        data = {"board": board_data, "start_board": start_board_data, "players_out_pieces": self.players_out_pieces,
                "current_turn": self.current_turn,
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
            else:
                self.has_more_dice = False
            self.set_available_moves()
            if len(self.current_available_indexes) == 0:
                return False
        if command_id == commands.Select_Peace:
            index = data['index']
            gamer_id = self.current_turn  # TODO : remove this
            move_type, target_index = self.move_piece(index, gamer_id)
            await self.send_data_function(commands.Peace_Selected,
                                          {'gamer_id': gamer_id, 'index': index, "target_index": target_index,
                                           "type": move_type})
            self.current_dice = 0
            self.current_turn_player_rolled = False
        return True

    def get_game_winner(self):
        winner = super().get_game_winner()
        return winner

    def change_turn(self):
        self.current_available_indexes.clear()
        self.is_current_turn_played = False
        self.has_more_dice = False
        self.current_dice = 0
        self.current_turn_player_rolled = False
        if self.current_turn == 1:
            self.current_turn = 2
        else:
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
        if self.current_turn == 1:
            if (self.board[36].equipped_user == 1 and self.board[37].equipped_user == 1 and
                    self.board[38].equipped_user == 1 and self.board[39].equipped_user == 1):
                return True
        if self.current_turn == 2:
            if (self.board[40].equipped_user == 2 and self.board[41].equipped_user == 2 and
                    self.board[42].equipped_user == 2 and self.board[43].equipped_user == 2):
                return True
        if self.current_turn == 3:
            if (self.board[44].equipped_user == 3 and self.board[45].equipped_user == 3 and
                    self.board[46].equipped_user == 3 and self.board[47].equipped_user == 3):
                return True
        if self.current_turn == 4:
            if (self.board[48].equipped_user == 4 and self.board[49].equipped_user == 4 and
                    self.board[50].equipped_user == 4 and self.board[51].equipped_user == 4):
                return True
        return False

    def check_hit_enemy(self, target_index, gamer_id):
        if target_index < 36:  # win not happens
            if self.board[target_index].is_enemy_spot(gamer_id):  # hit enemy
                enemy_index = self.board[target_index].equipped_user
                enemy_count = self.board[target_index].count
                self.players_out_pieces[enemy_index - 1] += enemy_count
                self.board[target_index].clear()

    def move_piece(self, index, gamer_id):
        target_index = 0
        if index == -2:  # enter game from out
            self.players_out_pieces[gamer_id - 1] -= 1
            self.start_pieces[gamer_id - 1].add_piece(gamer_id)
            return "out", None
        elif index == -1:  # enter game from start piece
            if gamer_id == 1:
                target_index = self.current_dice - 1
            elif gamer_id == 2:
                target_index = 18 + self.current_dice - 1
            elif gamer_id == 3:
                target_index = 27 + self.current_dice - 1
            elif gamer_id == 4:
                target_index = 9 + self.current_dice - 1
            self.check_hit_enemy(target_index, gamer_id)
            self.start_pieces[gamer_id - 1].remove_piece()
            self.board[target_index].add_piece(gamer_id)
            return "start", target_index
        else:  # normal selection
            if (gamer_id == 1 and index <= 29) or (gamer_id == 2 and (index <= 11 or index >= 18)) or (
                    gamer_id == 3 and (index <= 20 or index >= 27)) or (gamer_id == 4 and (index <= 2 or index >= 9)):
                target_index = (index + self.current_dice) % 36
            else:
                is_index_winable = gamer_pieces_win_map[gamer_id][index][self.current_dice]
                if is_index_winable is None:
                    pass
                elif is_index_winable:
                    target_index = gamer_win_indexes_map[gamer_id][index][self.current_dice]
                else:
                    target_index = (index + self.current_dice) % 36
            self.check_hit_enemy(target_index, gamer_id)
            self.board[index].remove_piece()
            self.board[target_index].add_piece(gamer_id)
            return "normal", target_index

    def get_my_piece_indexes(self, gamer_id):
        result = []
        for index in range(0, len(self.board)):
            if self.board[index].is_gamer_id_spot(gamer_id):
                result.append(index)
        return result

    def check_index_available(self, index):
        gamer_id = self.board[index].equipped_user
        if gamer_id == 1 and index <= 29:
            return True
        if gamer_id == 2 and (index <= 11 or index >= 18):
            return True
        if gamer_id == 3 and (index <= 20 or index >= 27):
            return True
        if gamer_id == 4 and (index <= 2 or index >= 9):
            return True
        is_index_winable = gamer_pieces_win_map[gamer_id][index][self.current_dice]
        if is_index_winable is None:
            return False
        if is_index_winable:
            win_index = gamer_win_indexes_map[gamer_id][index][self.current_dice]
            if self.board[win_index].is_empty():
                return True
            return False
        return True

    def set_available_moves(self):
        pieces = self.get_my_piece_indexes(self.current_turn)
        for piece_index in pieces:
            if self.check_index_available(piece_index):
                self.current_available_indexes.append(piece_index)
        have_piece_out = self.check_gamer_piece_is_out(self.current_turn)
        if have_piece_out and self.current_dice == 6:
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
