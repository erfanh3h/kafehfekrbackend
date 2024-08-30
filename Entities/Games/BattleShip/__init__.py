from Entities.Games.BattleShip.board_spot import boardSpot
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def get_coordinate_of_peace(peace_number):
    x = peace_number % 8
    y = int(peace_number / 8)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 8 + x
    return peace_number


class BattleShipGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.player1_board = [[boardSpot() for i in range(8)] for j in range(8)]
        self.player2_board = [[boardSpot() for i in range(8)] for j in range(8)]
        self.player1_ships = []
        self.player2_ships = []
        self.player1_score = 0
        self.player2_score = 0
        self.player1_board_rdy = False
        self.player2_board_rdy = False
        self.is_play_phase = False
        self.current_turn = 1
        self.is_current_turn_played = False  # this field use for when user win a selection and wana to not layed next choice
        self.is_turn_win_happened = False
        self.init_boards()

    def init_boards(self):
        self.player1_ships = [0, 1, 2, 3, 8, 9, 10, 11, 16, 17, 18, 24, 25, 32]
        self.player2_ships = [0, 1, 2, 3, 8, 9, 10, 11, 16, 17, 18, 24, 25, 32]
        for ship_index in [0, 8, 16, 24, 32]:
            y, x = get_coordinate_of_peace(ship_index)
            self.player1_board[y][x].set_number(5)
            self.player2_board[y][x].set_number(5)
        for ship_index in [1, 9, 17, 25]:
            y, x = get_coordinate_of_peace(ship_index)
            self.player1_board[y][x].set_number(4)
            self.player2_board[y][x].set_number(4)
        for ship_index in [2, 10, 18]:
            y, x = get_coordinate_of_peace(ship_index)
            self.player1_board[y][x].set_number(3)
            self.player2_board[y][x].set_number(3)
        for ship_index in [3, 11]:
            y, x = get_coordinate_of_peace(ship_index)
            self.player1_board[y][x].set_number(2)
            self.player2_board[y][x].set_number(2)

    def get_game_data_battleship(self, gamer_id):
        player1_board_data = []
        player2_board_data = []
        for j in range(8):
            for i in range(8):
                player1_board_data.append(self.player1_board[i][j].to_json())
        for j in range(8):
            for i in range(8):
                player2_board_data.append(self.player2_board[i][j].to_json())
        if gamer_id == 1:
            is_player_rdy = self.player1_board_rdy
        else:
            is_player_rdy = self.player2_board_rdy
        data = {"player1_board": player1_board_data, "player2_board": player2_board_data,
                "scores": [self.player1_score, self.player2_score],
                "is_play_phase": self.is_play_phase, "is_player_rdy": is_player_rdy, "current_turn": self.current_turn}
        return data

    def select_piece(self, index, gamer_id):
        self.is_turn_win_happened = False
        self.is_current_turn_played = True
        if gamer_id == 1:
            y, x = get_coordinate_of_peace(index)
            self.player2_board[y][x].select()
            number = self.player2_board[y][x].number
            if self.player2_board[y][x].is_ship():
                self.player2_ships.remove(index)
                self.player1_score += 1
                self.is_turn_win_happened = True
        else:
            y, x = get_coordinate_of_peace(index)
            self.player1_board[y][x].select()
            number = self.player1_board[y][x].number
            if self.player1_board[y][x].is_ship():
                self.player1_ships.remove(index)
                self.player2_score += 1
                self.is_turn_win_happened = True
        return number

    def save_board(self, data, gamer_id):
        if gamer_id == 1:
            self.player1_ships.clear()
            self.player1_board = [[boardSpot() for i in range(8)] for j in range(8)]
            for raw_key in data.keys():
                for raw_data in data[raw_key]:
                    y, x = get_coordinate_of_peace(raw_data)
                    self.player1_board[y][x].set_number(int(raw_key))
                    self.player1_ships.append(raw_data)
            self.player1_board_rdy = True
        else:
            self.player2_ships.clear()
            self.player2_board = [[boardSpot() for i in range(8)] for j in range(8)]
            for raw_key in data.keys():
                for raw_data in data[raw_key]:
                    y, x = get_coordinate_of_peace(raw_data)
                    self.player2_board[y][x].set_number(int(raw_key))
                    self.player2_ships.append(raw_data)
            self.player2_board_rdy = True

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Save_Board:
            self.save_board(data, gamer_id)
            if self.player1_board_rdy and self.player2_board_rdy:
                return True
            return False
        elif command_id == commands.Select_Peace:
            number = self.select_piece(data, gamer_id)
            await self.send_data_function(commands.Peace_Selected, {
                "select_data": {'index': data, 'gamer_id': gamer_id, 'number': number,
                                'is_turn_win_happened': self.is_turn_win_happened}})
            is_game_finished = self.check_end_game()
            if is_game_finished:
                self.is_turn_win_happened = False
                self.is_game_finished = True
                # game_winner = self.get_game_winner()
                # await self.send_data_function(commands.Finish_Game, {"Winner": game_winner})
                return True
        return False

    def change_turn(self):
        self.is_play_phase = True
        self.is_turn_win_happened = False
        self.is_current_turn_played = False
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    def check_end_game(self):
        if len(self.player1_ships) == 0 or len(self.player2_ships) == 0:
            return True
        return False

    def get_game_winner(self):
        winner = 0
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        elif self.player1_score > self.player2_score:
            winner = self.symbol_1
        elif self.player2_score > self.player1_score:
            winner = self.symbol_2
        return winner

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        peace_number = data
        x, y = get_coordinate_of_peace(peace_number)
        if gamer_id == 1 and self.player2_board[x][y].is_selected:
            return False
        if gamer_id == 2 and self.player1_board[x][y].is_selected:
            return False
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
