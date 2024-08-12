import random

from Entities.Games.Yatzy.board_spot import boardSpot
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def roll_dices(count):
    result = []
    for i in range(count):
        result.append(random.randint(1, 6))
    return result


class YatzyGameClass(BaseGameClass):
    def __init__(self, send_data_function, send_private_data_function):
        super().__init__(send_data_function)
        self.send_private_data_function = send_private_data_function
        self.player1_board = [boardSpot(index, 1) for index in range(12)]
        self.player2_board = [boardSpot(index, 2) for index in range(12)]
        self.player1_score = 0
        self.player2_score = 0
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.player1_current_dices = []
        self.player2_current_dices = []
        self.player1_submitted_dices = [0 for i in range(5)]
        self.player2_submitted_dices = [0 for i in range(5)]
        self.player1_rolled_dice_time = 0
        self.player2_rolled_dice_time = 0
        self.is_player1_round_done = False
        self.is_player2_round_done = False

    def get_game_data(self):
        board_data = []
        # for index in range(0, len(self.board)):
        #     # check peace equiped or not
        #     if self.board[index].equipped_user != 0:
        #         board_data.append(self.board[index].to_json())
        #     else:
        #         board_data.append(self.board[index].to_empty_json())
        #
        # data = {"board": board_data, "scores": [self.player1_score, self.player2_score],
        #         "current_turn": self.current_turn}
        return board_data

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            first_peace_index = data['index1']
            second_peace_index = data['index2']
            # is_correct = self.check_match_two(first_peace_index, second_peace_index)
            # if is_correct:
            #     self.submit_peaces_for_user(first_peace_index, second_peace_index, gamer_id)
            # await self.send_data_function(commands.Peace_Selected,
            #                               {'user': gamer_id, 'index1': first_peace_index,
            #                                'value1': self.board[first_peace_index].value,
            #                                'index2': second_peace_index, 'value2': self.board[second_peace_index].value,
            #                                'is_correct': is_correct})
            # is_game_finished = self.check_game_ended()
            # if is_game_finished:
            #     self.is_game_finished = True
            #     winner = self.get_game_winner()
            #     await self.send_data_function(commands.Finish_Game, {'Winner': winner})

    def check_authority(self, data, gamer_id: int):
        if (gamer_id == 1 and self.is_player1_round_done) or (gamer_id == 2 and self.is_player2_round_done):
            print("round done : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        return True

    def get_game_winner(self):
        winner = 0
        if self.player1_score > self.player2_score:
            winner = self.symbol_1
        elif self.player2_score > self.player1_score:
            winner = self.symbol_2
        return winner

    def change_turn(self):
        self.player1_submitted_dices = [0 for i in range(5)]
        self.player2_submitted_dices = [0 for i in range(5)]
        self.player1_current_dices = roll_dices(5)
        self.player2_current_dices = roll_dices(5)
        self.player1_rolled_dice_time = 0
        self.player2_rolled_dice_time = 0
        self.is_player1_round_done = False
        self.is_player2_round_done = False

    def check_game_ended(self):
        is_game_finished = False
        return is_game_finished
