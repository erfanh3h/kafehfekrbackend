import random

MOVE_DIRS = [(-1, 0), (0, -1), (0, +1), (+1, 0), ]


def is_valid_coord(col, row):
    if 0 <= row < 5 and 0 <= col < 5:
        return True
    return False


class BoardSpotClass:

    def __init__(self):
        self.value = 0
        self.equipped_user = 0

    def set_value(self, value: int, equipped_user: int):
        self.value = value
        self.equipped_user = equipped_user

    def __str__(self):
        return str(self.value)


class BoxFourGameClass:
    def __init__(self):
        self.board = [[BoardSpotClass() for i in range(5)] for j in range(5)]
        self.player1_score = 1
        self.player2_score = 1
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.current_turn = 1
        self.init_board()

    def init_board(self):
        self.board[2][1].set_value(3, 1)
        self.board[1][2].set_value(3, 2)

    def is_peace_available(self, position: tuple):
        return self.board[position[0]][position[1]].equipped_user == 0

    def is_peace_have_selection(self, position: tuple):
        return self.board[position[0]][position[1]].equipped_user != 0

    def change_active_player(self):
        if self.current_turn == 1:
            self.current_turn += 1
        else:
            self.current_turn = 1

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
        if self.player1_score > self.player2_score:
            return self.symbol_1
        elif self.player2_score > self.player1_score:
            return self.symbol_2
        else:
            return 0

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
            return True
        if not player2_exists:
            return True
        return False

    def get_player_score(self, gamer_id):
        count = 0
        for i in range(5):
            for j in range(5):
                if self.board[i][j].equipped_user == gamer_id:
                    count += 1
        return count

    def print_game(self):
        board = """"""
        board += '____0___1___2___3___4__\n'
        for i in range(5):
            board += f'{i} |'
            for j in range(5):
                board += f' {self.board[i][j]} '
                if j != 4:
                    board += '|'
            board += '|'
            board += '\n'
            if i != 7:
                board += '_______________________\n'
        board += '________________________\n'
        return board

    def print_equippes(self):
        board = """"""
        board += '____0___1___2___3___4__\n'
        for i in range(5):
            board += f'{i} |'
            for j in range(5):
                board += f' {self.board[i][j].equipped_user} '
                if j != 4:
                    board += '|'
            board += '|'
            board += '\n'
            if i != 7:
                board += '_______________________\n'
        board += '________________________\n'
        return board

    def play_game(self):
        print(self.print_game())
        # print(self.print_equippes())
        self.submit_piece_for_user((2, 1))
        print(self.print_game())

        self.submit_piece_for_user((2, 2))
        print(self.print_game())
        self.submit_piece_for_user((2, 2))
        # print(self.print_game())

        # self.submit_piece_for_user((2, 2))
        print(self.print_game())
        print(self.get_player_score(1))
        print(self.get_player_score(2))
        # print(self.print_equippes())


boxFourClass = BoxFourGameClass()
boxFourClass.play_game()
