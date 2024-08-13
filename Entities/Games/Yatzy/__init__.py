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
        self.current_round = 0
        self.player1_selected_dice_type = 0
        self.player2_selected_dice_type = 0

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
        if command_id == commands.Roll_Dice:
            selected_indexes = data['selected_indexes']
            if gamer_id == 1:
                pre_dices = self.player1_current_dices
                current_dice_count = self.player1_rolled_dice_time
            else:
                pre_dices = self.player2_current_dices
                current_dice_count = self.player2_rolled_dice_time
            if current_dice_count == 3:
                return
            new_roll_data = roll_dices(5)
            result = []
            for index in range(len(new_roll_data)):
                if selected_indexes.__contains__(index):
                    result.append(pre_dices[index])
                else:
                    result.append(new_roll_data[index])
            if gamer_id == 1:
                self.player1_current_dices = result
                self.player1_rolled_dice_time += 1
            else:
                self.player2_current_dices = result
                self.player2_rolled_dice_time += 1
            await self.send_private_data_function(commands.Roll_Result, {'dices': result}, gamer_id)
        if command_id == commands.Select_Peace:
            user_dices = data['dices']
            user_selected_index = data['index']
            let_broadcast = False
            score = 0
            if gamer_id == 1:
                if not self.player1_board[user_selected_index].is_selected:
                    self.player1_current_dices = user_dices
                    self.player1_selected_dice_type = user_selected_index
                    score = self.calculate_score(1)
                    self.player1_board[user_selected_index].select(score)
                    self.is_player1_round_done = True
                    let_broadcast = True
            else:
                if not self.player2_board[user_selected_index].is_selected:
                    self.player2_current_dices = user_dices
                    self.player2_selected_dice_type = user_selected_index
                    score = self.calculate_score(2)
                    self.player2_board[user_selected_index].select(score)
                    self.is_player2_round_done = True
                    let_broadcast = True
            if let_broadcast:
                await self.send_data_function(commands.Peace_Selected,
                                              {'gamer_id': gamer_id, 'selected_index': user_selected_index,
                                               'score': score}, )

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
        self.current_round += 1
        self.player1_submitted_dices = [0 for i in range(5)]
        self.player2_submitted_dices = [0 for i in range(5)]
        self.player1_current_dices = roll_dices(5)
        self.player2_current_dices = roll_dices(5)
        self.player1_rolled_dice_time = 0
        self.player2_rolled_dice_time = 0
        self.is_player1_round_done = False
        self.is_player2_round_done = False
        self.player1_selected_dice_type = self.get_first_empty_index(1)
        self.player2_selected_dice_type = self.get_first_empty_index(2)

    def check_game_ended(self):
        if self.current_round > 12:
            return True
        return False

    def get_first_empty_index(self, gamer_id):
        if gamer_id == 1:
            for i in range(12):
                if not self.player1_board[i].is_selected:
                    return i
            return 0
        else:
            for i in range(12):
                if not self.player2_board[i].is_selected:
                    return i
            return 0

    def calculate_score(self, gamer_id):
        return 0
