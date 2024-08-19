import random

from Entities.Games.BackGammon.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def roll_dices():
    result = []
    for i in range(2):
        result.append(random.randint(1, 6))
    if result[0] == result[1]:
        result.append(result[0])
        result.append(result[0])
    return result


def is_valid_index(index):
    if 0 <= index < 24:
        return True
    return False


class BackGammonGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.board = [BoardSpotClass() for i in range(24)]
        self.player1_score = 0
        self.player2_score = 0
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.current_turn = 1
        self.init_board()
        self.current_dices = []
        self.player1_out_pieces = 0
        self.player2_out_pieces = 0

    def init_board(self):
        self.board[0].add_piece(1, 2)
        self.board[23].add_piece(2, 2)
        self.board[5].add_piece(2, 5)
        self.board[18].add_piece(1, 5)
        self.board[7].add_piece(2, 3)
        self.board[16].add_piece(1, 3)
        self.board[11].add_piece(1, 5)
        self.board[12].add_piece(2, 5)

    def get_game_data(self):
        board_data = []
        for index in range(0, len(self.board)):
            # check peace equiped or not
            board_data.append(self.board[index].to_json())

        data = {"board": board_data, "scores": [self.player1_score, self.player2_score],
                "current_turn": self.current_turn, "out_pieces": [self.player1_out_pieces, self.player2_out_pieces]}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            index = data['index']
            dice_index = data['dice_index']
            is_correct = self.move_piece(index, self.current_dices[dice_index], gamer_id)
            await self.send_data_function(commands.Peace_Selected,
                                          {'gamer_id': gamer_id, 'index': index, 'dice_index': dice_index,
                                           'is_correct': is_correct})
            self.current_dices.remove(self.current_dices[dice_index])
            return len(self.current_dices) == 0
            # is_game_finished = self.check_game_ended()
            # if is_game_finished:
            #     self.is_game_finished = True
            #     winner = self.get_game_winner()
            #     await self.send_data_function(commands.Finish_Game, {'Winner': winner})
        return False

    def check_source_can_move_n_count(self, index, count, gamer_id):
        if gamer_id == 1:
            multiple = 1
        else:
            multiple = -1
        destination = index + (count * multiple)
        if not is_valid_index(destination):
            return False
        if self.board[destination].is_enemy_spot(gamer_id):
            return False
        return True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        if len(self.current_dices) == 0:
            return False
        index = data['index']
        dice_index = data['dice_index']
        if not self.check_source_can_move_n_count(index, self.current_dices[dice_index], gamer_id):
            return False

        return True

    def get_game_winner(self):
        winner = 0
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        elif self.player1_score > self.player2_score:
            winner = self.symbol_1
        elif self.player2_score > self.player1_score:
            winner = self.symbol_2
        return winner

    def change_turn(self):
        self.current_dices = roll_dices()
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    def check_game_ended(self):
        is_game_finished = False
        return is_game_finished

    def move_piece(self, index, dice, gamer_id):
        self.board[index].remove_piece()
        if gamer_id == 1:
            multiple = 1
        else:
            multiple = -1
        target_index = index + (dice * multiple)
        if self.board[target_index].is_enemy_spot(gamer_id):
            if self.board[target_index].is_single():
                if gamer_id == 1:
                    self.player2_out_pieces += 1
                else:
                    self.player1_out_pieces += 1
                self.board[target_index].remove_piece()
                self.board[target_index].add_piece(gamer_id)
            else:
                return False
        else:
            self.board[target_index].add_piece(gamer_id)
        return True

    def print_game(self):
        print(f"""
        {self.board[0]}----------{self.board[23]}
        {self.board[1]}----------{self.board[22]}
        {self.board[2]}----------{self.board[21]}
        {self.board[3]}----------{self.board[20]}
        {self.board[4]}----------{self.board[19]}
        {self.board[5]}----------{self.board[18]}
        {self.board[6]}----------{self.board[17]}
        {self.board[7]}----------{self.board[16]}
        {self.board[8]}----------{self.board[15]}
        {self.board[9]}----------{self.board[14]}
        {self.board[10]}----------{self.board[13]}
        {self.board[11]}----------{self.board[12]}
        """)

    def print_equippes(self):
        print(f"""
        {self.board[0].equipped_user}----------{self.board[23].equipped_user}
        {self.board[1].equipped_user}----------{self.board[22].equipped_user}
        {self.board[2].equipped_user}----------{self.board[21].equipped_user}
        {self.board[3].equipped_user}----------{self.board[20].equipped_user}
        {self.board[4].equipped_user}----------{self.board[19].equipped_user}
        {self.board[5].equipped_user}----------{self.board[18].equipped_user}
        {self.board[6].equipped_user}----------{self.board[17].equipped_user}
        {self.board[7].equipped_user}----------{self.board[16].equipped_user}
        {self.board[8].equipped_user}----------{self.board[15].equipped_user}
        {self.board[9].equipped_user}----------{self.board[14].equipped_user}
        {self.board[10].equipped_user}----------{self.board[13].equipped_user}
        {self.board[11].equipped_user}----------{self.board[12].equipped_user}
        """)
