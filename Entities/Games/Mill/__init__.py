from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class MillGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [0 for i in range(24)]
        self.current_round = 1
        self.player1_peaces = 10
        self.player2_peaces = 10
        self.player1_played_peaces = 0
        self.player2_played_peaces = 0
        self.player1_removed_peaces = 0
        self.player2_removed_peaces = 0
        self.current_remover = 0  # if user successfully removed a peace , he can remove peace now
        self.win_conditions = [[0, 1, 2], [0, 9, 21], [21, 22, 23], [23, 14, 2], [1, 4, 7], [9, 10, 11], [22, 19, 16],
                               [14, 13, 12], [3, 4, 5], [3, 10, 18], [18, 19, 20], [20, 13, 5], [6, 7, 8], [6, 1, 15],
                               [15, 16, 17],
                               [17, 12, 8], ]
        self.pieces_neighbors = {0: [1, 9], 1: [0, 2, 4], 2: [1, 14], 3: [4, 10], 4: [1, 3, 5, 7], 5: [4, 13],
                                 6: [7, 11],
                                 7: [4, 6, 8], 8: [7, 12], 9: [0, 10, 21], 10: [3, 9, 11, 18], 11: [6, 10, 15],
                                 12: [8, 13, 17],
                                 13: [5, 12, 14, 20], 14: [2, 13, 23], 15: [11, 16], 16: [15, 17, 19], 17: [12, 16],
                                 18: [10, 19],
                                 19: [16, 18, 20, 22], 20: [13, 19], 21: [9, 22], 22: [19, 21, 23], 23: [14, 22]}

    def get_game_data(self):
        data = {"board": self.board, "played_peaces": [self.player1_played_peaces, self.player2_played_peaces],
                "removed_peaces": [self.player1_removed_peaces, self.player2_removed_peaces],
                "current_turn": self.current_turn, "current_remover": self.current_remover}
        return data

    def change_round(self):
        pass

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            peace_number = data
            if gamer_id == 1:
                self.board[peace_number] = self.symbol_1
                self.player1_played_peaces += 1
            else:
                self.board[peace_number] = self.symbol_2
                self.player2_played_peaces += 1
            await self.send_data_function(commands.Peace_Selected, {'user': gamer_id, 'target_peace': peace_number})
            result = self.check_all_match_three_conditions(peace_number, gamer_id)
            if result:
                self.current_remover = gamer_id
        elif command_id == commands.Swap_Peace:
            source_peace_number = data["data"]["source"]
            target_peace_number = data["data"]["target"]
            self.board[source_peace_number] = 0
            self.board[target_peace_number] = gamer_id
            await self.send_data_function(commands.Peace_Swaped, {'user': gamer_id, 'source_peace': source_peace_number,
                                                                  'target_peace': target_peace_number})
            result = self.check_all_match_three_conditions(target_peace_number, gamer_id)
            if result:
                self.current_remover = gamer_id
        elif command_id == commands.Select_Remove_Peace:
            peace_number = data
            self.board[peace_number] = 0
            if gamer_id == 1:
                self.player2_removed_peaces += 1
            else:
                self.player1_removed_peaces += 1
            self.current_remover = 0
            await self.send_data_function(commands.Peace_Removed, {'user': gamer_id, 'target_peace': peace_number})
            is_game_ended = self.check_game_ended()
            if is_game_ended:
                # winner = self.get_game_winner()
                # await self.send_data_function(commands.Finish_Game, {"Winner": winner})
                self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        return True

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_peaces - self.player1_removed_peaces < 3:
                winner = self.symbol_2
            elif self.player2_peaces - self.player2_removed_peaces < 3:
                winner = self.symbol_1
        return winner

    def check_game_ended(self):
        if self.player1_peaces - self.player1_removed_peaces < 3:
            return True
        elif self.player2_peaces - self.player2_removed_peaces < 3:
            return True
        return False

    def change_turn(self):
        self.current_remover = 0
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    def check_all_match_three_conditions(self, user_input, gamer_id):
        temp_list = []
        for raw_data in self.win_conditions:
            if raw_data.__contains__(user_input):
                temp_list.append(raw_data)

        for raw_data in temp_list:
            raw_result = self.check_match_three(raw_data, gamer_id)
            if raw_result:
                return True
        return False

    def check_match_three(self, raw_data, user_label) -> bool:
        for data in raw_data:
            if self.board[data] != user_label:
                return False
        return True

    def check_player_all_pieces_placed(self, gamer_id) -> bool:
        if gamer_id == 1:
            if self.player1_played_peaces < self.player1_peaces:
                return False
            else:
                return True
        else:
            if self.player2_played_peaces < self.player2_peaces:
                return False
            else:
                return True

    def check_select_authority(self, data, gamer_id):
        if not self.check_authority(data, gamer_id):
            return False
        peace_number = data
        if self.board[peace_number] != 0:
            return False
        if self.check_player_all_pieces_placed(gamer_id):
            return False
        return True

    def check_swap_authority(self, data, gamer_id):
        if not self.check_authority(data, gamer_id):
            return False
        if not self.check_player_all_pieces_placed(gamer_id):
            return False
        source_peace_number = data["source"]
        target_peace_number = data["target"]
        if self.board[source_peace_number] != gamer_id:
            return False
        if self.board[target_peace_number] != 0:
            return False
        if gamer_id == 1:
            current_peace_count = self.player1_peaces - self.player1_removed_peaces
        else:
            current_peace_count = self.player2_peaces - self.player2_removed_peaces
        # if user have 3 peace , can swap to any place
        if current_peace_count != 3 and target_peace_number not in self.pieces_neighbors[source_peace_number]:
            return False
        return True

    def check_remove_authority(self, data, gamer_id):
        if not self.check_authority(data, gamer_id):
            return False
        if self.current_remover != gamer_id:
            return False
        peace_number = data
        if self.board[peace_number] == 0 or self.board[peace_number] == gamer_id:
            return False
        return True
