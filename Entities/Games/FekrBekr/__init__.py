from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class FekrBekrGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.player1_board = []
        self.player2_board = []
        self.player1_choices = []
        self.player2_choices = []
        self.player1_results = []
        self.player2_results = []
        self.player1_board_rdy = False
        self.player2_board_rdy = False
        self.is_play_phase = False
        self.current_round = 0
        self.player1_finished = False
        self.player2_finished = False
        self.player1_played_turn = False
        self.player2_played_turn = False

    def get_game_data_fekrbekr(self, gamer_id):
        if gamer_id == 1:
            is_player_rdy = self.player1_board_rdy
        else:
            is_player_rdy = self.player2_board_rdy
        data = {"player1_choices": self.player1_choices, "player2_choices": self.player2_choices,
                "player1_results": self.player1_results, "player2_results": self.player2_results,
                "is_play_phase": self.is_play_phase, "is_player_rdy": is_player_rdy, "current_turn": self.current_turn,
                "current_round": self.current_round}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        # print(command_id, data, gamer_id)
        if command_id == commands.Save_Board:
            self.save_board(data, gamer_id)
            return self.player1_board_rdy and self.player2_board_rdy
        elif command_id == commands.Select_Peace:
            self.submit_data(data, gamer_id)
            return self.player1_played_turn and self.player2_played_turn
        return False

    def change_round(self):
        self.is_play_phase = True
        self.player1_played_turn = False
        self.player2_played_turn = False
        self.current_round += 1

    def check_game_ended(self):
        if self.player1_finished or self.player2_finished:
            return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_finished and not self.player2_finished:
                winner = self.symbol_1
            elif self.player2_finished and not self.player1_finished:
                winner = self.symbol_2
            elif self.player2_finished and self.player1_finished:
                winner = 0
        return winner

    def board_contains_number(self, gamer_id, number, ignore_list):
        if gamer_id == 1:
            for index, num in enumerate(self.player1_board):
                if num == number and not ignore_list.__contains__(index):
                    return True, index
        elif gamer_id == 2:
            for index, num in enumerate(self.player2_board):
                if num == number and not ignore_list.__contains__(index):
                    return True, index
        return False, 0

    def check_player1(self, data):
        result = []
        ignores_list = []
        for index, number in enumerate(data):
            if number == self.player1_board[index]:
                result.append(2)
                ignores_list.append(index)
                continue
            contains_number, number_index = self.board_contains_number(1, number, ignores_list)
            if contains_number:
                result.append(1)
                ignores_list.append(number_index)
        return result

    def check_player2(self, data):
        result = []
        ignores_list = []
        for index, number in enumerate(data):
            if number == self.player2_board[index]:
                result.append(2)
                ignores_list.append(index)
                continue
            contains_number, number_index = self.board_contains_number(2, number, ignores_list)
            if contains_number:
                result.append(1)
                ignores_list.append(number_index)
        return result

    def submit_data(self, data, gamer_id):
        if gamer_id == 1:
            self.player1_choices.append(data)
            result = self.check_player1(data)
            self.player1_results.append(result)
            is_finished = True
            for data in result:
                if data != 2:
                    is_finished = False
                    break
            self.player1_finished = is_finished
        else:
            self.player2_choices.append(data)
            result = self.check_player2(data)
            self.player2_results.append(result)
            is_finished = True
            for data in result:
                if data != 2:
                    is_finished = False
                    break
            self.player2_finished = is_finished

    def save_board(self, data, gamer_id):
        if gamer_id == 1:
            self.player1_board = data
            self.player1_board_rdy = True
        else:
            self.player2_board = data
            self.player2_board_rdy = True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            # print("not turn of : ", gamer_id)
            return False
        peace_number = data
        if self.is_game_finished:
            return False
        return True

    def check_save_peace_authority(self, data, gamer_id: int):
        if gamer_id == 1 and self.player1_board_rdy:
            return False
        if gamer_id == 2 and self.player2_board_rdy:
            return False
        if len(data.keys()) != 4:
            return False
        return True
