from random import sample


class BoardSpotClass:
    def __init__(self, number=0):
        self.number = number
        self.is_base_number = True

    def set_number(self, number):
        self.number = number

    def clear_number(self):
        self.number = 0
        self.is_base_number = False

    def __str__(self):
        return self.number.__str__()


class SudokuGameClass:
    def __init__(self):
        self.board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.player1_board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.player2_board = [[BoardSpotClass() for i in range(9)] for j in range(9)]
        self.make_board()
        self.make_players_board()

    def make_board(self):
        base = 3
        side = base * base

        def pattern(r, c): return (base * (r % base) + r // base + c) % side

        def shuffle(s): return sample(s, len(s))

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
        empties = 50
        for p in sample(range(squares), empties):
            self.player1_board[p // side][p % side].clear_number()
            self.player2_board[p // side][p % side].clear_number()

        # numSize = len(str(side))
        # for line in board:
        #     print(*(f"{n or '.':{numSize}} " for n in line))

    def print(self, player_board):
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

    def submit_piece(self, position, gamer_id, number):
        if gamer_id == 1:
            if not self.player1_board[position[0]][position[1]].is_base_number:
                self.player1_board[position[0]][position[1]].set_number(number)
        else:
            if not self.player2_board[position[0]][position[1]].is_base_number:
                self.player2_board[position[0]][position[1]].set_number(number)

    def check_win(self, gamer_id):
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


sudokoGame = SudokuGameClass()
sudokoGame.print(sudokoGame.board)
print(sudokoGame.check_win(1))
# sudokoGame.submit_piece((8, 8), 1, 8)
# sudokoGame.print(sudokoGame.player1_board)
