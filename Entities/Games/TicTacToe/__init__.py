from Entities.Games.base_game_class import BaseGameClass
from Controllers.GameSession.commands import Finish_Game


class TicTacToeGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.board = [" " for i in range(9)]
        self.win_conditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]
        self.counter = 0

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if self.current_turn == 0 and gamer_id != 0 or self.current_turn == 1 and gamer_id != 1:
            return
        peace_number = data
        is_peace_corrected = self.check_authority(peace_number)
        if is_peace_corrected:
            self.counter += 1
            if gamer_id == 0:
                self.board[peace_number] = self.symbol_1
                self.current_turn = 1
            else:
                self.board[peace_number] = self.symbol_2
                self.current_turn = 0
            winner = self.check_winner()
            if winner is not None:
                await self.send_data_function(Finish_Game, {"Winner": winner})
                self.printPretty()

    def check_authority(self, peace_number: int):
        # Check if players' selection is out of range
        if peace_number < 0 or peace_number > 8:
            return False
            # Check if the square is already filled
        if (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
            return False
        return True

    def printPretty(self):
        # This function prints the board nice!
        print("---+---+---")
        for r in range(3):
            print(self.board[r * 3], " |", self.board[r * 3 + 1], "|", self.board[r * 3 + 2])
            print("---+---+---")

    def check_winner(self):
        winner = None
        for condition in self.win_conditions:
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_1:
                winner = self.symbol_1
                print("Player " + self.symbol_1 + ", you won!")
                break
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_2:
                winner = self.symbol_2
                print("Player " + self.symbol_2 + ", you won!")
                break
        return winner
