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
        self.player1_rolled_dice_time = 1
        self.player2_rolled_dice_time = 1
        self.is_player1_round_done = False
        self.is_player2_round_done = False
        self.current_round = 0
        self.player1_selected_dice_type = 0
        self.player2_selected_dice_type = 0

    def get_game_data_yatzy(self, gamer_id):
        player1_board_data = []
        player2_board_data = []
        for index in range(0, len(self.player1_board)):
            player1_board_data.append(self.player1_board[index].to_json())
        for index in range(0, len(self.player2_board)):
            player2_board_data.append(self.player2_board[index].to_json())
        if gamer_id == 1:
            current_dices = self.player1_current_dices
            rolled_dice_times = self.player1_rolled_dice_time
            is_round_done = self.is_player1_round_done
        else:
            current_dices = self.player2_current_dices
            rolled_dice_times = self.player2_rolled_dice_time
            is_round_done = self.is_player2_round_done
        data = {"player1_board": player1_board_data, "player2_board": player2_board_data,
                "is_round_done": is_round_done,
                "current_dices": current_dices, "rolled_dice_times": rolled_dice_times,
                "scores": [self.player1_score, self.player2_score], "current_round": self.current_round}
        return data

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
            user_selected_index = data['index']
            let_broadcast = False
            score = 0
            if gamer_id == 1:
                if not self.player1_board[user_selected_index].is_selected:
                    self.player1_selected_dice_type = user_selected_index
                    score = self.calculate_score(1, user_selected_index)
                    self.player1_board[user_selected_index].select(score)
                    self.is_player1_round_done = True
                    let_broadcast = True
            else:
                if not self.player2_board[user_selected_index].is_selected:
                    self.player2_selected_dice_type = user_selected_index
                    score = self.calculate_score(2, user_selected_index)
                    self.player2_board[user_selected_index].select(score)
                    self.is_player2_round_done = True
                    let_broadcast = True
            if let_broadcast:
                await self.send_data_function(commands.Peace_Selected,
                                              {'gamer_id': gamer_id, 'selected_index': user_selected_index,
                                               'score': score, 'player1_score': self.player1_score,
                                               'player2_score': self.player2_score}, )
            if self.is_player1_round_done and self.is_player2_round_done:
                return True
        return False

    def check_authority(self, data, gamer_id: int):
        if (gamer_id == 1 and self.is_player1_round_done) or (gamer_id == 2 and self.is_player2_round_done):
            print("round done : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        return True

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_score > self.player2_score:
                winner = self.symbol_1
            elif self.player2_score > self.player1_score:
                winner = self.symbol_2
        return winner

    def change_turn(self):
        self.current_round += 1
        if self.current_round > 12:
            self.is_game_finished = True
        else:
            self.player1_current_dices = roll_dices(5)
            self.player2_current_dices = roll_dices(5)
            self.player1_rolled_dice_time = 1
            self.player2_rolled_dice_time = 1
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

    def calculate_all_dices(self, gamer_id):
        score = 0
        if gamer_id == 1:
            for dice in self.player1_current_dices:
                score += dice
        else:
            for dice in self.player2_current_dices:
                score += dice
        return score

    def calculate_simple_dices(self, number, gamer_id):
        score = 0
        if gamer_id == 1:
            for dice in self.player1_current_dices:
                if dice == number:
                    score += number
        else:
            for dice in self.player2_current_dices:
                if dice == number:
                    score += number
        return score

    def calculate_repeatness(self, number, count, gamer_id):
        counter = 0
        if gamer_id == 1:
            for dice in self.player1_current_dices:
                if dice == number:
                    counter += 1
        else:
            for dice in self.player2_current_dices:
                if dice == number:
                    counter += 1
        return counter >= count

    def calculate_3times_repeat(self, gamer_id):
        calculated_score = 0
        for i in range(1, 7):
            if self.calculate_repeatness(i, 3, gamer_id):
                calculated_score += self.calculate_all_dices(gamer_id)
                break
        return calculated_score

    def calculate_4times_repeat(self, gamer_id):
        calculated_score = 0
        for i in range(1, 7):
            if self.calculate_repeatness(i, 4, gamer_id):
                calculated_score += self.calculate_all_dices(gamer_id)
                break
        return calculated_score

    def calculate_23_times_repeat(self, gamer_id):
        is2_times_exists = False
        is3_times_exists = False
        three_times_index = -1
        for i in range(1, 7):
            if self.calculate_repeatness(i, 3, gamer_id):
                is3_times_exists = True
                three_times_index = i
                break
        if is3_times_exists:
            for i in range(1, 7):
                if self.calculate_repeatness(i, 2, gamer_id) and i != three_times_index:
                    is2_times_exists = True
                    break
        return is2_times_exists and is3_times_exists

    def calculate_15_exists(self, gamer_id):
        if gamer_id == 1:
            if (self.player1_current_dices.__contains__(1) and self.player1_current_dices.__contains__(
                    2) and self.player1_current_dices.__contains__(3) and self.player1_current_dices.__contains__(
                4) and self.player1_current_dices.__contains__(5)):
                return True
            if (self.player1_current_dices.__contains__(2) and self.player1_current_dices.__contains__(
                    3) and self.player1_current_dices.__contains__(4) and self.player1_current_dices.__contains__(
                5) and self.player1_current_dices.__contains__(6)):
                return True
        else:
            if (self.player2_current_dices.__contains__(1) and self.player2_current_dices.__contains__(
                    2) and self.player2_current_dices.__contains__(3) and self.player2_current_dices.__contains__(
                4) and self.player2_current_dices.__contains__(5)):
                return True
            if (self.player2_current_dices.__contains__(2) and self.player2_current_dices.__contains__(
                    3) and self.player2_current_dices.__contains__(4) and self.player2_current_dices.__contains__(
                5) and self.player2_current_dices.__contains__(6)):
                return True
        return False

    def calculate_5times_repeat(self, gamer_id):
        calculated_score = 0
        for i in range(1, 7):
            if self.calculate_repeatness(i, 5, gamer_id):
                calculated_score += 50
                break
        return calculated_score

    def calculate_score(self, gamer_id, selected_index):
        calculated_score = 0
        if selected_index == 0:
            calculated_score = self.calculate_simple_dices(1, gamer_id)
        elif selected_index == 1:
            calculated_score = self.calculate_simple_dices(2, gamer_id)
        elif selected_index == 2:
            calculated_score = self.calculate_simple_dices(3, gamer_id)
        elif selected_index == 3:
            calculated_score = self.calculate_simple_dices(4, gamer_id)
        elif selected_index == 4:
            calculated_score = self.calculate_simple_dices(5, gamer_id)
        elif selected_index == 5:
            calculated_score = self.calculate_simple_dices(6, gamer_id)
        elif selected_index == 6:
            calculated_score = self.calculate_3times_repeat(gamer_id)
        elif selected_index == 7:
            calculated_score = self.calculate_4times_repeat(gamer_id)
        elif selected_index == 8:
            calculated_score = self.calculate_all_dices(gamer_id)
        elif selected_index == 9:
            is_correct = self.calculate_23_times_repeat(gamer_id)
            if is_correct:
                calculated_score = 25
            else:
                calculated_score = 0
        elif selected_index == 10:
            is_correct = self.calculate_15_exists(gamer_id)
            if is_correct:
                calculated_score = 40
            else:
                calculated_score = 0
        elif selected_index == 11:
            calculated_score = self.calculate_5times_repeat(gamer_id)
        if gamer_id == 1:
            self.player1_score += calculated_score
        else:
            self.player2_score += calculated_score
        return calculated_score

    def check_player_played_this_round(self, gamer_id):
        if gamer_id == 1:
            if not self.is_player1_round_done:
                self.player1_board[self.player1_selected_dice_type].select(0)
                return self.player1_selected_dice_type
        else:
            if not self.is_player2_round_done:
                self.player2_board[self.player2_selected_dice_type].select(0)
                return self.player2_selected_dice_type
        return -1
