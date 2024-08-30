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


def is_valid_index_in_end_phase(index, gamer_id):
    if gamer_id == 1:
        if 0 <= index <= 24:
            return True
    if gamer_id == 2:
        if -1 <= index < 24:
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
        self.player1_is_in_end_phase = False
        self.player2_is_in_end_phase = False

    def init_board(self):
        self.board[0].add_piece(1, 2)
        self.board[23].add_piece(2, 2)
        self.board[5].add_piece(2, 5)
        self.board[18].add_piece(1, 5)
        self.board[7].add_piece(2, 3)
        self.board[16].add_piece(1, 3)
        self.board[11].add_piece(1, 5)
        self.board[12].add_piece(2, 5)
        # self.board[19].add_piece(1, 2)
        # self.board[23].add_piece(2, 2)
        # self.board[5].add_piece(2, 5)
        # self.board[20].add_piece(1, 5)
        # self.board[7].add_piece(2, 3)
        # self.board[21].add_piece(1, 3)
        # self.board[22].add_piece(1, 5)
        # self.board[12].add_piece(2, 5)

    def get_game_data(self):
        board_data = []
        for index in range(0, len(self.board)):
            # check peace equiped or not
            board_data.append(self.board[index].to_json())

        data = {"board": board_data, "scores": [self.player1_score, self.player2_score],
                "current_turn": self.current_turn, "out_pieces": [self.player1_out_pieces, self.player2_out_pieces],
                "current_dices": self.current_dices,
                "end_phases": [self.player1_is_in_end_phase, self.player2_is_in_end_phase]}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        async def check_game_finish():
            is_game_finished = self.check_game_ended()
            if is_game_finished:
                self.is_game_finished = True
                winner = self.get_game_winner()
                await self.send_data_function(commands.Finish_Game, {'Winner': winner})

        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            index = data['index']
            dice_index = data['dice_index']
            is_piece_out = self.check_gamer_piece_is_out(gamer_id)
            if is_piece_out:
                if gamer_id == 1:
                    index = -1
                else:
                    index = 24
                is_correct = self.move_piece(index, self.current_dices[dice_index], gamer_id)
                if is_correct:
                    if gamer_id == 1:
                        self.player1_out_pieces -= 1
                    else:
                        self.player2_out_pieces -= 1
                    await self.send_data_function(commands.Peace_Selected,
                                                  {'gamer_id': gamer_id, 'index': index, 'dice_index': dice_index})
                    self.current_dices.remove(self.current_dices[dice_index])
                    await check_game_finish()
            else:
                is_correct = self.move_piece(index, self.current_dices[dice_index], gamer_id)
                if is_correct:
                    await self.send_data_function(commands.Peace_Selected,
                                                  {'gamer_id': gamer_id, 'index': index, 'dice_index': dice_index})
                    self.current_dices.remove(self.current_dices[dice_index])
                    await check_game_finish()

            return len(self.current_dices) == 0

        return False

    def check_gamer_piece_is_out(self, gamer_id):
        if gamer_id == 1 and self.player1_out_pieces > 0:
            return True
        if gamer_id == 2 and self.player2_out_pieces > 0:
            return True
        return False

    def check_source_can_move_n_count(self, index, count, gamer_id):
        if gamer_id == 1:
            multiple = 1
        else:
            multiple = -1
        destination = index + (count * multiple)
        is_in_end_phase = False
        if gamer_id == 1 and self.player1_is_in_end_phase:
            is_in_end_phase = True
        elif gamer_id == 2 and self.player2_is_in_end_phase:
            is_in_end_phase = True
        if is_in_end_phase:
            if not is_valid_index_in_end_phase(destination, gamer_id):
                return False
            if (destination != -1 and destination != 24 and self.board[destination].is_enemy_spot(gamer_id) and
                    not self.board[destination].is_single()):
                return False
        else:
            if not is_valid_index(destination):
                return False
            if self.board[destination].is_enemy_spot(gamer_id) and not self.board[destination].is_single():
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
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_score == 15:
                winner = self.symbol_1
            elif self.player2_score == 15:
                winner = self.symbol_2
        return winner

    def change_turn(self):
        self.current_dices = roll_dices()
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    def check_game_ended(self):
        if self.player1_score == 15 or self.player2_score == 15:
            return True
        return False

    def check_gamer_is_in_end_phase(self, gamer_id):
        if gamer_id == 1:
            if (self.board[18].count + self.board[19].count + self.board[20].count + self.board[21].count +
                    self.board[22].count + self.board[23].count + self.player1_score == 15):
                self.player1_is_in_end_phase = True
            else:
                self.player1_is_in_end_phase = False
        else:
            if (self.board[0].count + self.board[1].count + self.board[2].count + self.board[3].count +
                    self.board[4].count + self.board[5].count + self.player2_score == 15):
                self.player2_is_in_end_phase = True
            else:
                self.player2_is_in_end_phase = False

    def move_piece(self, index, dice, gamer_id):
        result = True
        if index == -1 or index == 24:
            pass
        else:
            self.board[index].remove_piece()
        if gamer_id == 1:
            multiple = 1
        else:
            multiple = -1
        target_index = index + (dice * multiple)
        is_in_end_phase = False
        if gamer_id == 1 and self.player1_is_in_end_phase:
            is_in_end_phase = True
        elif gamer_id == 2 and self.player2_is_in_end_phase:
            is_in_end_phase = True
        # check player is in end phae
        if is_in_end_phase and (target_index == -1 or target_index == 24):
            if gamer_id == 1:
                self.player1_score += 1
            else:
                self.player2_score += 1
        else:
            if self.board[target_index].is_enemy_spot(gamer_id):
                if self.board[target_index].is_single():
                    if gamer_id == 1:
                        self.player2_out_pieces += 1
                    else:
                        self.player1_out_pieces += 1
                    self.board[target_index].remove_piece()
                    self.board[target_index].add_piece(gamer_id)
                else:
                    result = False
            else:
                self.board[target_index].add_piece(gamer_id)

        if result:
            self.check_gamer_is_in_end_phase(gamer_id)
        return result
