import random

from Entities.Games.MSweeper.board_spot import boardSpot
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def get_coordinate_of_peace(peace_number):
    x = peace_number % 8
    y = int(peace_number / 8)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 8 + x
    return peace_number


class MSweeperGameClass(BaseGameClass):
    def __init__(self, send_data_function, send_private_data_function):
        super().__init__(send_data_function)
        self.send_private_data_function = send_private_data_function
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.boardSize = 8
        self.numMines = 12
        self.board = [[boardSpot() for i in range(self.boardSize)] for j in range(self.boardSize)]
        self.player1_board = self.board.copy()
        self.player2_board = self.board.copy()
        self.player1_selectable_spots = self.boardSize * self.boardSize - self.numMines
        self.player2_selectable_spots = self.boardSize * self.boardSize - self.numMines
        self.player1_selectable_mines = self.numMines
        self.player2_selectable_mines = self.numMines
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

    def select_peace(self, x, y, gamer_id):
        if gamer_id == 1:
            self.player1_board[x][y].selected = True
            self.player1_selectable_spots -= 1
        else:
            self.player2_board[x][y].selected = True
            self.player2_selectable_spots -= 1
        if self.board[x][y].value == -1:
            return False
        else:
            peace_number = get_peace_of_coordinate(x, y)
            self.send_private_data_function(commands.Select_Peace_Result,
                                            {"peace_number": peace_number, "value": self.board[x][y].value})
        if self.board[x][y].value == 0:
            if gamer_id == 1:
                spot = self.player1_board
            else:
                spot = self.player2_board
            for i in range(x - 1, x + 2):
                if 0 <= i < self.boardSize:
                    if y - 1 >= 0 and not spot[i][y - 1].selected:
                        self.select_peace(i, y - 1, gamer_id)
                    if y + 1 < self.boardSize and not spot[i][y + 1].selected:
                        self.select_peace(i, y + 1, gamer_id)
            if x - 1 >= 0 and not spot[x - 1][y].selected:
                self.select_peace(x - 1, y, gamer_id)
            if x + 1 < self.boardSize and not spot[x + 1][y].selected:
                self.select_peace(x + 1, y, gamer_id)
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
        x, y = get_coordinate_of_peace(peace_number)
        if command_id == commands.Select_Peace:
            self.select_peace(x, y, gamer_id)
            if self.hit_mine(x, y):
                self.send_private_data_function(commands.Mine_Selected, {"peace_number": peace_number})
                if gamer_id == 1:
                    self.player1_selectable_mines = 0
                    self.player1_selectable_spots = 0
                else:
                    self.player2_selectable_mines = 0
                    self.player2_selectable_spots = 0
            else:
                is_game_finished = self.check_end_game()
                if is_game_finished:
                    self.finish_game()
                    game_winner = self.get_game_winner()
                    await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
        elif command_id == commands.Select_Mine:
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

    def check_end_game(self):
        return (self.player1_selectable_spots == 0 and self.player2_selectable_spots == 0 and
                self.player1_selectable_mines == 0 and self.player2_selectable_mines == 0)

    def get_game_winner(self):
        if self.gamer1_score > self.gamer2_score:
            return self.symbol_1
        elif self.gamer2_score > self.gamer1_score:
            return self.symbol_2
        else:
            return 0

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        peace_number = data
        x, y = get_coordinate_of_peace(peace_number)
        if gamer_id == 1 and self.player1_board[x][y].selected:
            return False
        if gamer_id == 2 and self.player2_board[x][y].selected:
            return False
        if self.is_game_finished:
            return False
        return True

    def check_select_peace_authority(self, data, gamer_id: int):
        if not self.check_authority(data, gamer_id):
            return False
        if gamer_id == 1 and self.player1_selectable_spots == 0:
            return False
        if gamer_id == 2 and self.player2_selectable_spots == 0:
            return False
        return True

    def check_select_mine_authority(self, data, gamer_id: int):
        if not self.check_authority(data, gamer_id):
            return False
        if gamer_id == 1 and self.player2_selectable_mines == 0:
            return False
        if gamer_id == 2 and self.player2_selectable_mines == 0:
            return False
        return True

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        if gamer_id == 1:
            game_winner = 2
        else:
            game_winner = 1
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})
