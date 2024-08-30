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
        self.board_size = 8
        self.num_mines = 10
        self.board = [[boardSpot() for i in range(self.board_size)] for j in range(self.board_size)]
        self.player1_board = [[boardSpot() for i in range(self.board_size)] for j in range(self.board_size)]
        self.player2_board = [[boardSpot() for i in range(self.board_size)] for j in range(self.board_size)]
        self.player1_selectable_spots = self.board_size * self.board_size - self.num_mines
        self.player2_selectable_spots = self.board_size * self.board_size - self.num_mines
        self.player1_selectable_mines = self.num_mines
        self.player2_selectable_mines = self.num_mines
        self.player1_score = 0
        self.player2_score = 0
        self.is_player1_tapped_mine = False
        self.is_player2_tapped_mine = False
        i = 0
        while i < self.num_mines:
            x = random.randint(0, self.board_size - 1)
            y = random.randint(0, self.board_size - 1)
            if not self.board[x][y].mine:
                self.add_mine(x, y)
                i += 1
            else:
                i -= 1
        print(self.show_board())

    def get_game_data_msweeper(self, gamer_id):
        board_peaces_data = []
        if gamer_id == 1:
            remaining_selectable_mines = self.player1_selectable_mines
            remaining_selectable_peaces = self.player1_selectable_spots
            is_tapped_mine = self.is_player1_tapped_mine
            for j in range(self.board_size):
                for i in range(self.board_size):
                    board_peaces_data.append(self.player1_board[i][j].to_json())
        else:
            remaining_selectable_mines = self.player2_selectable_mines
            remaining_selectable_peaces = self.player2_selectable_spots
            is_tapped_mine = self.is_player2_tapped_mine
            for j in range(self.board_size):
                for i in range(self.board_size):
                    board_peaces_data.append(self.player2_board[i][j].to_json())
        data = {"board": board_peaces_data, "scores": [self.player1_score, self.player2_score],
                "remaining_selectable_mines": remaining_selectable_mines,
                "remaining_selectable_peaces": remaining_selectable_peaces, "is_tapped_mine": is_tapped_mine}
        return data

    def add_mine(self, x, y):
        self.board[x][y].value = -1
        self.board[x][y].mine = True
        for i in range(x - 1, x + 2):
            if 0 <= i < self.board_size:
                if y - 1 >= 0 and not self.board[i][y - 1].mine:
                    self.board[i][y - 1].value += 1
                if y + 1 < self.board_size and not self.board[i][y + 1].mine:
                    self.board[i][y + 1].value += 1
        if x - 1 >= 0 and not self.board[x - 1][y].mine:
            self.board[x - 1][y].value += 1
        if x + 1 < self.board_size and not self.board[x + 1][y].mine:
            self.board[x + 1][y].value += 1

    async def select_peace(self, x, y, gamer_id):
        if gamer_id == 1:
            self.player1_board[x][y].selected = True
            self.player1_board[x][y].value = self.board[x][y].value
            self.player1_selectable_spots -= 1
        else:
            self.player2_board[x][y].selected = True
            self.player2_board[x][y].value = self.board[x][y].value
            self.player2_selectable_spots -= 1
        if self.board[x][y].value == -1:
            return False
        else:
            peace_number = get_peace_of_coordinate(x, y)
            await self.send_private_data_function(commands.Select_Peace_Result,
                                                  {"peace_number": peace_number, "value": self.board[x][y].value},
                                                  gamer_id)
        if self.board[x][y].value == 0:
            if gamer_id == 1:
                spot = self.player1_board
            else:
                spot = self.player2_board
            for i in range(x - 1, x + 2):
                if 0 <= i < self.board_size:
                    if y - 1 >= 0 and not spot[i][y - 1].selected:
                        await self.select_peace(i, y - 1, gamer_id)
                    if y + 1 < self.board_size and not spot[i][y + 1].selected:
                        await self.select_peace(i, y + 1, gamer_id)
            if x - 1 >= 0 and not spot[x - 1][y].selected:
                await self.select_peace(x - 1, y, gamer_id)
            if x + 1 < self.board_size and not spot[x + 1][y].selected:
                await self.select_peace(x + 1, y, gamer_id)
            return True
        else:
            return True

    async def select_mine(self, x, y, gamer_id):
        if gamer_id == 1:
            self.player1_selectable_mines -= 1
        else:
            self.player2_selectable_mines -= 1
        if self.is_peace_mine(x, y):
            if gamer_id == 1:
                self.player1_board[x][y].correctly_selected_mine = True
                self.player1_score += 1
                self.player1_board[x][y].value = self.board[x][y].value
                self.player1_board[x][y].mine = True
                score = self.player1_score
            else:
                self.player2_board[x][y].correctly_selected_mine = True
                self.player2_score += 1
                self.player2_board[x][y].value = self.board[x][y].value
                self.player2_board[x][y].mine = True
                score = self.player2_score
            peace_number = get_peace_of_coordinate(x, y)
            await self.send_private_data_function(commands.Select_Mine_Correct, {"peace_number": peace_number},
                                                  gamer_id)
            await self.send_data_function(commands.Player_Score, {"gamer_id": gamer_id, "value": score})
        else:
            if gamer_id == 1:
                self.player1_board[x][y].wrongly_selected_mine = True
            else:
                self.player2_board[x][y].wrongly_selected_mine = True
            peace_number = get_peace_of_coordinate(x, y)
            await self.send_private_data_function(commands.Select_Mine_Wrong, {"peace_number": peace_number},
                                                  gamer_id)

    def is_peace_mine(self, x, y):
        return self.board[x][y].value == -1

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        peace_number = data
        x, y = get_coordinate_of_peace(peace_number)
        if command_id == commands.Select_Peace:
            await self.select_peace(x, y, gamer_id)
            if self.is_peace_mine(x, y):
                await self.send_private_data_function(commands.Mine_Selected, {"peace_number": peace_number}, gamer_id)
                if gamer_id == 1:
                    self.player1_selectable_mines = 0
                    self.player1_selectable_spots = 0
                    self.is_player1_tapped_mine = True
                    self.player1_board[x][y].hitted_mine = True
                    self.player1_board[x][y].mine = True
                else:
                    self.player2_selectable_mines = 0
                    self.player2_selectable_spots = 0
                    self.is_player2_tapped_mine = True
                    self.player2_board[x][y].hitted_mine = True
                    self.player2_board[x][y].mine = True
            is_game_finished = self.check_end_game()
            if is_game_finished:
                self.is_game_finished = True
                # game_winner = self.get_game_winner()
                # await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
                return True
        elif command_id == commands.Select_Mine:
            await self.select_mine(x, y, gamer_id)
            is_game_finished = self.check_end_game()
            if is_game_finished:
                self.is_game_finished = True
                # game_winner = self.get_game_winner()
                # await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
                return True
        return False

    def check_end_game(self):
        if self.player1_selectable_mines == 0 and self.player2_selectable_mines == 0:
            return True
        if self.player1_selectable_mines == 0 and self.player1_score == self.num_mines:
            return True
        if self.player2_selectable_mines == 0 and self.player2_score == self.num_mines:
            return True
        if self.player1_selectable_mines == 0 and self.player2_score > self.player1_score:
            return True
        if self.player2_selectable_mines == 0 and self.player1_score > self.player2_score:
            return True
        return False

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            if self.player1_score > self.player2_score:
                winner = self.symbol_1
            elif self.player2_score > self.player1_score:
                winner = self.symbol_2
        return winner

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
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
        if gamer_id == 1 and self.player1_selectable_mines == 0:
            return False
        if gamer_id == 2 and self.player2_selectable_mines == 0:
            return False
        return True

    def show_board(self):
        returnString = " "
        divider = "\n---"

        for i in range(0, self.board_size):
            returnString += " | " + str(i)
            divider += "----"
        divider += "\n"

        returnString += divider
        for y in range(0, self.board_size):
            returnString += str(y)
            for x in range(0, self.board_size):
                returnString += " |" + str(self.board[x][y].value)
            returnString += " |"
            returnString += divider
        return returnString

    def show_player1_board(self):
        returnString = " "
        divider = "\n---"

        for i in range(0, self.board_size):
            returnString += " | " + str(i)
            divider += "----"
        divider += "\n"

        returnString += divider
        for y in range(0, self.board_size):
            returnString += str(y)
            for x in range(0, self.board_size):
                if self.player1_board[x][y].mine and self.player1_board[x][y].selected:
                    returnString += " |" + str(self.player1_board[x][y].value)
                elif self.player1_board[x][y].selected:
                    returnString += " | " + str(self.player1_board[x][y].value)
                else:
                    returnString += " |  "
            returnString += " |"
            returnString += divider
        return returnString
