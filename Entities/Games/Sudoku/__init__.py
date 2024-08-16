import random

from Entities.Games.Sudoku.board_spot import BoardSpotClass
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


def get_coordinate_of_peace(peace_number):
    x = peace_number % 9
    y = int(peace_number / 9)
    return x, y


def get_peace_of_coordinate(x, y):
    peace_number = y * 9 + x
    return peace_number


class SudokuGameClass(BaseGameClass):
    def __init__(self, send_data_function, send_private_data_function):
        super().__init__(send_data_function)
        self.send_private_data_function = send_private_data_function
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.player1_board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.player2_board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.make_board()
        self.make_players_board()
        self.winner_id = 0
        self.player1_solve_limit = 2
        self.player2_solve_limit = 2

    def get_game_data_sudoku(self, gamer_id):
        board_peaces_data = []
        if gamer_id == 1:
            for j in range(9):
                for i in range(9):
                    board_peaces_data.append(self.player1_board[i][j].to_json())
        else:
            for j in range(9):
                for i in range(9):
                    board_peaces_data.append(self.player2_board[i][j].to_json())
        data = {"board": board_peaces_data}
        return data

    def make_board(self):
        base = 3
        side = base * base

        def pattern(r, c): return (base * (r % base) + r // base + c) % side

        def shuffle(s): return random.sample(s, len(s))

        rBase = range(base)
        rows = [g * base + r for g in shuffle(rBase) for r in shuffle(rBase)]
        cols = [g * base + c for g in shuffle(rBase) for c in shuffle(rBase)]
        nums = shuffle(range(1, base * base + 1))
        self.board = [[BoardSpotClass(number=nums[pattern(r, c)]) for c in cols] for r in rows]
        self.player1_board = [[BoardSpotClass(number=nums[pattern(r, c)]) for c in cols] for r in rows]
        self.player2_board = [[BoardSpotClass(number=nums[pattern(r, c)]) for c in cols] for r in rows]

    def make_players_board(self):
        base = 3
        side = base * base
        squares = side * side
        empties = 45
        for p in random.sample(range(squares), empties):
            self.player1_board[p // side][p % side].clear_number()
            self.player2_board[p // side][p % side].clear_number()

    def submit_piece(self, position, gamer_id, number):
        if gamer_id == 1:
            if not self.player1_board[position[1]][position[0]].is_base_number:
                self.player1_board[position[1]][position[0]].set_number(number)
        else:
            if not self.player2_board[position[1]][position[0]].is_base_number:
                self.player2_board[position[1]][position[0]].set_number(number)

    async def recieve_data(self, command_id, data, gamer_id):
        print(command_id, data, gamer_id)
        if command_id == commands.Select_Peace:
            piece_id = data['piece_id']
            row_index, column_index = get_coordinate_of_peace(piece_id)
            number = data['number']
            self.submit_piece((column_index, row_index), gamer_id, number)
        elif command_id == commands.Remove_Peace:
            piece_id = data['piece_id']
            row_index, column_index = get_coordinate_of_peace(piece_id)
            self.submit_piece((column_index, row_index), gamer_id, 0)
        elif command_id == commands.Solve:
            is_win_happened = self.check_win_happened(gamer_id)
            if not self.is_game_finished and is_win_happened:
                self.finish_game()
                self.winner_id = gamer_id
                await self.send_data_function(commands.Finish_Game, {"Winner": gamer_id})
                return True
            else:
                await self.send_private_data_function(commands.Wrong_Solve, None, gamer_id)
        return False

    def check_game_ended(self):
        return False

    def get_game_winner(self):
        winner = self.winner_id
        if self.leaver_id != 0:
            winner = self.get_opponent_id(self.leaver_id)
        return winner

    def finish_game(self):
        self.is_game_finished = True

    def check_authority(self, data, gamer_id: int):
        piece_id = data['piece_id']
        row_index, column_index = get_coordinate_of_peace(piece_id)
        if gamer_id == 1 and self.player1_board[row_index][column_index].is_base_number:
            return False
        if gamer_id == 2 and self.player2_board[row_index][column_index].is_base_number:
            return False
        if self.is_game_finished:
            return False
        return True

    def check_solve_authority(self, gamer_id):
        if self.is_game_finished:
            return False
        return True

    def check_win_happened(self, gamer_id):
        if gamer_id == 1:
            board = self.player1_board
        else:
            board = self.player2_board
        is_win = True
        row_list = []
        for i in range(9):
            check_list = []
            for j in range(9):
                check_list.append(board[i][j].number)
            row_list.append(check_list)
        col_list = [[] for i in range(9)]
        for data in row_list:
            for i in range(9):
                col_list[i].append(data[i])
        for data in row_list:
            if not is_win:
                break
            for i in range(1, 10):
                if not data.__contains__(i):
                    is_win = False
        for data in col_list:
            if not is_win:
                break
            for i in range(1, 10):
                if not data.__contains__(i):
                    is_win = False
        return is_win

    def show_player1_board(self, player_board):
        board = """"""
        board += '____0___1___2___3___4___5___6___7___8__\n'
        for i in range(9):
            board += f'{i} |'
            for j in range(9):
                board += f' {player_board[i][j].number} '
                if j != 8:
                    board += '|'
            board += '|'
            board += '\n'
            if i != 8:
                board += '_______________________________________\n'
        board += '______________________________________\n'
        print(board)
