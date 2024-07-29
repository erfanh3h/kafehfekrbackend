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
        i = 0
        while i < self.num_mines:
            x = random.randint(0, self.board_size - 1)
            y = random.randint(0, self.board_size - 1)
            if not self.board[x][y].mine:
                self.add_mine(x, y)
                i += 1
            else:
                i -= 1
        self.player1_score = 0
        self.player2_score = 0
        self.is_player1_tapped_mine = False
        self.is_player2_tapped_mine = False
        print(self.show_board())

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
            self.player1_board[x][y].select_mine = True
            self.player1_selectable_mines -= 1
        else:
            self.player2_board[x][y].select_mine = True
            self.player2_selectable_mines -= 1
        if self.is_peace_mine(x, y):
            if gamer_id == 1:
                self.player1_score += 1
                self.player1_board[x][y].value = self.board[x][y].value
                score = self.player1_score
            else:
                self.player2_score += 1
                self.player2_board[x][y].value = self.board[x][y].value
                score = self.player2_score
            peace_number = get_peace_of_coordinate(x, y)
            await self.send_private_data_function(commands.Select_Mine_Correct, {"peace_number": peace_number},
                                                  gamer_id)
            await self.send_data_function(commands.Player_Score, {"gamer_id": gamer_id, "value": score})
        else:
            peace_number = get_peace_of_coordinate(x, y)
            await self.send_private_data_function(commands.Select_Mine_Wrong, {"peace_number": peace_number},
                                                  gamer_id)

    def is_peace_mine(self, x, y):
        return self.board[x][y].value == -1

    def get_game_data(self):
        return {}
        # data = {"board": self.board, "scores": [self.player1_score, self.player2_score],
        #         "current_turn": self.current_turn}
        # return data

    def change_round(self):
        pass

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
                else:
                    self.player2_selectable_mines = 0
                    self.player2_selectable_spots = 0
                    self.is_player2_tapped_mine = True
            is_game_finished = self.check_end_game()
            if is_game_finished:
                self.finish_game()
                game_winner = self.get_game_winner()
                await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
            print(self.show_board())
            print(self.show_player1_board())
        elif command_id == commands.Select_Mine:
            await self.select_mine(x, y, gamer_id)
            is_game_finished = self.check_end_game()
            if is_game_finished:
                self.finish_game()
                game_winner = self.get_game_winner()
                await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
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
        if self.player1_score > self.player2_score:
            return self.symbol_1
        elif self.player2_score > self.player1_score:
            return self.symbol_2
        else:
            return 0

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

    async def surrender(self, gamer_id):
        self.is_game_finished = True
        if gamer_id == 1:
            game_winner = 2
        else:
            game_winner = 1
        await self.send_data_function(commands.Surrender, {"gamer_id": gamer_id})
