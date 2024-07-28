import random

from Entities.Games.MSweeper.board_spot import boardSpot
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class MSweeperGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.boardSize = 8
        self.numMines = 12
        self.board = [[boardSpot() for i in range(self.boardSize)] for j in range(self.boardSize)]
        self.player1_board = self.board.copy()
        self.player2_board = self.board.copy()
        self.player1_selectable_spots = self.boardSize * self.boardSize - self.numMines
        self.player2_selectable_spots = self.boardSize * self.boardSize - self.numMines
        i = 0
        while i < self.numMines:
            x = random.randint(0, self.boardSize - 1)
            y = random.randint(0, self.boardSize - 1)
            if not self.board[x][y].mine:
                self.add_mine(x, y)
                i += 1
            else:
                i -= 1
        self.gamer1_score = 0
        self.gamer2_score = 0

    def add_mine(self, x, y):
        self.board[x][y].value = -1
        self.board[x][y].mine = True
        for i in range(x - 1, x + 2):
            if 0 <= i < self.boardSize:
                if y - 1 >= 0 and not self.board[i][y - 1].mine:
                    self.board[i][y - 1].value += 1
                if y + 1 < self.boardSize and not self.board[i][y + 1].mine:
                    self.board[i][y + 1].value += 1
        if x - 1 >= 0 and not self.board[x - 1][y].mine:
            self.board[x - 1][y].value += 1
        if x + 1 < self.boardSize and not self.board[x + 1][y].mine:
            self.board[x + 1][y].value += 1

    def make_move(self, x, y, gamer_id):
        if gamer_id == 1:
            self.player1_board[x][y].selected = True
            self.player1_selectable_spots -= 1
        else:
            self.player2_board[x][y].selected = True
            self.player2_selectable_spots -= 1
        if self.board[x][y].value == -1:
            return False
        if self.board[x][y].value == 0:
            for i in range(x - 1, x + 2):
                if 0 <= i < self.boardSize:
                    if y - 1 >= 0 and not self.board[i][y - 1].selected:
                        self.make_move(i, y - 1, gamer_id)
                    if y + 1 < self.boardSize and not self.board[i][y + 1].selected:
                        self.make_move(i, y + 1, gamer_id)
            if x - 1 >= 0 and not self.board[x - 1][y].selected:
                self.make_move(x - 1, y, gamer_id)
            if x + 1 < self.boardSize and not self.board[x + 1][y].selected:
                self.make_move(x + 1, y, gamer_id)
            return True
        else:
            return True

    def hit_mine(self, x, y):
        return self.board[x][y].value == -1

    def get_game_data(self):
        data = {"board": self.board, "scores": [self.gamer1_score, self.gamer2_score],
                "current_turn": self.current_turn}
        return data

    def change_round(self):
        pass

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        peace_number = data
        x = peace_number % 8
        y = int(peace_number / 8)
        self.make_move(x, y, gamer_id)
        if self.hit_mine(x, y):
            pass
        # await self.send_data_function(commands.Peace_Selected, {'user': gamer_id, 'target_peace': peace_number})
        # winner = self.check_winner()
        # if winner is not None or self.counter == 9:
        #     if self.current_round == self.round_count:
        #         game_winner = self.get_game_winner()
        #         await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
        #         self.is_game_finished = True
        #     else:
        #         self.is_round_finished = True
        #         await self.send_data_function(commands.Finish_Round, {"Winner": winner})

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        peace_number = data
        # Check if players' selection is out of range
        if peace_number < 0 or peace_number > 8:
            return False
            # Check if the square is already filled
        if (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
            return False

        if self.is_game_finished or self.is_round_finished:
            return False
        return True

    def check_winner(self):
        winner = None
        # for condition in self.win_conditions:
        #     if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_1:
        #         winner = self.symbol_1
        #         self.gamer1_score += 1
        #         break
        #     if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_2:
        #         winner = self.symbol_2
        #         self.gamer2_score += 1
        #         break
        return winner

    def get_game_winner(self):
        if self.gamer1_score > self.gamer2_score:
            return self.symbol_1
        elif self.gamer2_score > self.gamer1_score:
            return self.symbol_2
        else:
            return None

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = 2
        else:
            self.current_turn = 1

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        if gamer_id == 1:
            game_winner = 2
        else:
            game_winner = 1
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})
