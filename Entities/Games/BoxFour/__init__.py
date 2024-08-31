from Entities.Games.BoxFour.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands

MOVE_DIRS = [(-1, 0), (0, -1), (0, +1), (+1, 0), ]


def get_coordinate_of_peace(peace_number):
    x = peace_number % 5
    y = int(peace_number / 5)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 5 + x
    return peace_number


def is_valid_coord(col, row):
    if 0 <= row < 5 and 0 <= col < 5:
        return True
    return False


class BoxFourGameClass(BaseGameClass):
    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.board = [[BoardSpotClass() for i in range(5)] for j in range(5)]
        self.player1_score = 1
        self.player2_score = 1
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.game_winner = 0
        self.init_board()

    def init_board(self):
        self.board[2][1].set_value(3, 1)
        self.board[2][3].set_value(3, 2)

    def get_game_data(self):
        board_pieces_data = []
        for i in range(5):
            for j in range(5):
                board_pieces_data.append(self.board[i][j].to_json())
        data = {"board": board_pieces_data, "scores": [self.player1_score, self.player2_score],
                "current_turn": self.current_turn}
        return data

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            c_index = data['c_index']
            r_index = data['r_index']
            self.submit_piece_for_user((c_index, r_index))
            self.player1_score = self.get_player_score(1)
            self.player2_score = self.get_player_score(2)
            await self.send_data_function(commands.Peace_Selected,
                                          {'gamer_id': gamer_id, 'c_index': c_index, 'r_index': r_index})
            is_game_finished = self.check_game_ended()
            if is_game_finished:
                self.finish_game()

    def check_authority(self, data, gamer_id: int):
        if (self.current_turn == 1 and gamer_id != 1) or (self.current_turn == 2 and gamer_id != 2):
            print("not turn of : ", gamer_id)
            return False
        if self.is_game_finished:
            return False
        c_index = data['c_index']
        r_index = data['r_index']
        if not self.is_peace_mine((c_index , r_index) , gamer_id):
            return False
        return True

    def change_turn(self):
        if self.current_turn == 1:
            self.current_turn = self.symbol_2
        else:
            self.current_turn = self.symbol_1

    def is_peace_available(self, position: tuple):
        return self.board[position[0]][position[1]].equipped_user == 0

    def is_peace_mine(self, position: tuple , gamer_id):
        return self.board[position[0]][position[1]].equipped_user == gamer_id

    def get_value_of_location(self, input_value):
        return self.board[input_value]

    def spread_number(self, position: tuple, gamer_id: int):
        self.board[position[0]][position[1]].set_value(0, 0)
        for direction_move in MOVE_DIRS:
            y = position[0] + direction_move[0]
            x = position[1] + direction_move[1]
            if is_valid_coord(y, x):
                current_value = self.board[y][x].value
                if current_value < 3:
                    self.board[y][x].set_value(current_value + 1, gamer_id)
                else:
                    self.spread_number((y, x), gamer_id)

    def submit_piece_for_user(self, position: tuple):
        if self.current_turn == 1:
            gamer_id = self.symbol_1
        else:
            gamer_id = self.symbol_2
        current_value = self.board[position[0]][position[1]].value
        if current_value < 3:
            self.board[position[0]][position[1]].set_value(current_value + 1, gamer_id)
        else:
            self.spread_number(position, gamer_id)

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            winner = self.game_winner
        return winner

    def check_game_ended(self):
        player1_exists = False
        player2_exists = False
        for i in range(5):
            for j in range(5):
                if self.board[i][j].equipped_user == 1:
                    player1_exists = True
                if self.board[i][j].equipped_user == 2:
                    player2_exists = True
        if not player1_exists:
            self.game_winner = 2
            return True
        if not player2_exists:
            self.game_winner = 1
            return True
        return False

    def get_player_score(self, gamer_id):
        count = 0
        for i in range(5):
            for j in range(5):
                if self.board[i][j].equipped_user == gamer_id:
                    count += 1
        return count
