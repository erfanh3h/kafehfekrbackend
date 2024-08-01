from math import inf
from time import time
from copy import deepcopy


class Color(object):
    BLACK = "\u001b[30m"
    RED = "\u001b[1;31m"
    WHITE = "\u001b[37m"
    RESET = "\u001b[0m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    PURPLE = "\033[1;35m"
    BOLD = "\033[1m"
    BLUE = "\033[1;36m"
    PURPLE_BACKGROUND = "\u001b[45;1m"


class State(object):
    def __init__(self, board, move=None):
        self.board = board
        self.move = move

    def get_children(self, mandatory_jump, player_turn):
        current_state = deepcopy(self.board)
        children = []
        available_moves = Checkers.find_moves(current_state, mandatory_jump, player_turn)
        for i in range(len(available_moves)):
            state = deepcopy(current_state)
            Checkers.make_a_move(state, available_moves[i])
            children.append(State(state, available_moves[i]))
        return children

    def get_board(self):
        return self.board

    def set_board(self, board):
        self.board = board

    def get_move(self):
        return self.move

    def set_move(self, move):
        self.move = move


class Checkers(object):
    def __init__(self):
        self.matrix = [[], [], [], [], [], [], [], []]
        self.player_pieces = 12
        self.computer_pieces = 12
        self.player_turn = True
        self.mandatory_jump = False

        for row in self.matrix:
            for i in range(8):
                row.append(" . ")
        self.position_computer()
        self.position_player()

    def position_computer(self):
        for i in range(3):
            for j in range(8):
                if (i + j) % 2 == 0:
                    self.matrix[i][j] = "b" + str(i) + str(j)

    def position_player(self):
        for i in range(5, 8):
            for j in range(8):
                if (i + j) % 2 == 0:
                    self.matrix[i][j] = "w" + str(i) + str(j)

    @staticmethod
    def print_matrix(board, player_turn, mandatory_jump):
        available_moves = []
        if player_turn:
            available_moves = Checkers.find_moves(board, mandatory_jump, True)
        k = 0
        print()
        for i in range(8):
            if i == 0:
                print("     0", end="   ")
            else:
                print(i, end="   ")
        print()
        for row in board:
            print(k, end="  |")
            k += 1
            j = 0
            for elem in row:
                j += 1
                if player_turn and Checkers.is_movable(board, k - 1, j - 1, available_moves):
                    print(Color.BLUE + elem + Color.RESET, end=" ")
                else:
                    print(elem, end=" ")
            print("| ", k - 1)
        for i in range(8):
            if i == 0:
                print("     0", end="   ")
            else:
                print(i, end="   ")
        print("\n")

    @staticmethod
    def print_second_matrix(board, moves, pawn):
        k = 0
        print()
        for i in range(8):
            if i == 0:
                print("     0", end="   ")
            else:
                print(i, end="   ")
        print()
        for row in board:
            print(k, end="  |")
            k += 1
            j = 0
            for elem in row:
                j += 1
                if pawn in elem:
                    print(Color.BLUE + pawn + Color.RESET, end="  ")
                else:
                    for move in moves:
                        if move[3] == k - 1 and move[4] == j - 1:
                            print(Color.PURPLE_BACKGROUND + str(k - 1) + str(j - 1) + Color.RESET, end="  ")
                            break
                    else:
                        print(elem, end=" ")
            print("| ", k - 1)
        for i in range(8):
            if i == 0:
                print("     0", end="   ")
            else:
                print(i, end="   ")
        print("\n")

    @staticmethod
    def is_movable(board, m, n, available_moves):
        for move in available_moves:
            if board[m][n] == move[0]:
                return True
        return False

    @staticmethod
    def get_depth(available_moves):
        if len(available_moves) == 1:
            return 0
        elif len(available_moves) > 6:
            return 3
        else:
            return 5

    def computer_move(self):
        t1 = time()
        current_state = State(self.matrix)
        available_moves = current_state.get_children(self.mandatory_jump, False)
        if len(available_moves) == 0:
            print(Color.GREEN + "Computer has no moves available! YOU WIN!" + Color.RESET)
            game_over()
        depth = Checkers.get_depth(available_moves)
        dictionary = {}
        for i in range(len(available_moves)):
            child = available_moves[i]
            value = Checkers.minimax(child.get_board(), -inf, inf, depth, False, self.mandatory_jump)
            dictionary[value] = child
        new_board = dictionary[max(dictionary.keys())].get_board()
        self.matrix = new_board
        t2 = time()
        time_taken = t2 - t1
        move = dictionary[max(dictionary.keys())].get_move()
        print("Computer moved ", move[0], " from ", move[1], move[2], " to ", move[3], move[4])
        if abs(move[1] - move[3]) >= 2:
            self.player_pieces -= abs(move[1] - move[3]) // 2
            print(Color.BOLD + "Computer took your pawn!" + Color.RESET)
        print("The move took %.6f seconds" % time_taken)

    def player_move(self):
        available_moves = Checkers.find_moves(self.matrix, self.mandatory_jump, self.player_turn)
        if len(available_moves) == 0:
            print(Color.RED + "No moves available! YOU LOSE!" + Color.RESET)
            game_over()
        move = Checkers.choose_move(self.matrix, available_moves, False)
        pawn = move[0]
        move = move[1]
        for moves in available_moves:
            if pawn in moves[0] and move == str(moves[3]) + str(moves[4]):
                Checkers.make_a_move(self.matrix, moves)
                if Checkers.is_jump(available_moves, move, pawn):
                    self.computer_pieces -= 1
                    while True:
                        jump = Checkers.double_jump(self.matrix, moves, self.mandatory_jump)
                        if jump:
                            Checkers.make_a_move(self.matrix, jump)
                            self.computer_pieces -= 1
                            continue
                        break
                break

    @staticmethod
    def double_jump(board, move, mandatory_jump):
        available_jumps = []
        if Checkers.available_jump(board, "w", move[3], move[4],
                                   move[3] - 1, move[4] - 1, move[3] - 2, move[4] - 2):
            available_jumps.append([board[move[3]][move[4]], move[3], move[4], move[3] - 2, move[4] - 2])
        if Checkers.available_jump(board, "w", move[3], move[4],
                                   move[3] - 1, move[4] + 1, move[3] - 2, move[4] + 2):
            available_jumps.append([board[move[3]][move[4]], move[3], move[4], move[3] - 2, move[4] + 2])
        if board[move[3]][move[4]][0] == "W":
            if Checkers.available_jump(board, "w", move[3], move[4],
                                       move[3] + 1, move[4] - 1, move[3] + 2, move[4] - 2):
                available_jumps.append([board[move[3]][move[4]], move[3], move[4], move[3] + 2, move[4] - 2])
            if Checkers.available_jump(board, "w", move[3], move[4],
                                       move[3] + 1, move[4] + 1, move[3] + 2, move[4] + 2):
                available_jumps.append([board[move[3]][move[4]], move[3], move[4], move[3] + 2, move[4] + 2])
        if len(available_jumps) == 0:
            return False
        state = deepcopy(board)
        Checkers.print_second_matrix(state, available_jumps, str(move[3]) + str(move[4]))
        if not mandatory_jump:
            while True:
                choice = input("Do you want to make another jump? [Y/N]: ")
                if choice.lower() == "y":
                    break
                elif choice.lower() == "n":
                    return False
                elif choice == "":
                    print(Color.YELLOW + "Game ended!" + Color.RESET)
                    game_over()
                elif choice.lower() == "s":
                    while True:
                        choice = input("Are you sure you want to surrender? [Y/N]: ")
                        if choice.lower() == "y":
                            print(Color.RED + "You surrendered! Coward move..." + Color.RESET)
                            game_over()
                        elif choice.lower() == "n":
                            break
                        else:
                            print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
                else:
                    print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
        pawn = str(move[3]) + str(move[4])
        jump = Checkers.choose_move(board, available_jumps, True)
        for moves in available_jumps:
            if pawn == str(moves[1]) + str(moves[2]) and jump == str(moves[3]) + str(moves[4]):
                return moves

    @staticmethod
    def is_jump(available_moves, move, pawn):
        for moves in available_moves:
            if pawn in moves[0] and move == str(moves[3]) + str(moves[4]):
                if abs(moves[1] - moves[3]) == 2:
                    return True
                return False

    @staticmethod
    def choose_pawn(board, available_moves):
        while True:
            pawn = input("Choose a pawn you want to move [format [row column] no spaces]: ")
            if Checkers.is_valid_pawn(available_moves, pawn):
                break
        if pawn == "":
            print(Color.YELLOW + "Game ended!" + Color.RESET)
            game_over()
        new_board = deepcopy(board)
        pawn_moves = []
        for moves in available_moves:
            if pawn in moves[0]:
                pawn_moves.append(moves)
        Checkers.print_second_matrix(new_board, pawn_moves, pawn)
        return pawn

    @staticmethod
    def choose_move(board, available_moves, double_jump):
        pawn = None
        while True:
            if not double_jump:
                pawn = Checkers.choose_pawn(board, available_moves)
            while True:
                move = input("Choose a move [format [row column] no spaces] [x to choose another pawn]: ")
                if Checkers.is_valid_move(available_moves, move):
                    break
            if move.lower() == "x":
                Checkers.print_matrix(board, True, False)
                continue
            break
        if double_jump:
            return move
        return [pawn, move]

    @staticmethod
    def is_valid_pawn(available_moves, pawn):
        for moves in available_moves:
            if len(pawn) == 2 and pawn in moves[0]:
                return True
        else:
            if Checkers.is_enter(pawn):
                return True
            if Checkers.is_surrender(pawn):
                if Checkers.to_surrender():
                    game_over()
                return False
            print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
            return False

    @staticmethod
    def is_valid_move(available_moves, move):
        for moves in available_moves:
            if move == str(moves[3]) + str(moves[4]):
                return True
        else:
            if Checkers.is_enter(move):
                print(Color.YELLOW + "Game ended!" + Color.RESET)
                game_over()
            if Checkers.is_surrender(move):
                if Checkers.to_surrender():
                    game_over()
                return False
            if Checkers.is_exchange(move):
                return True
            print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
            return False

    @staticmethod
    def is_enter(prompt):
        return prompt == ""

    @staticmethod
    def is_surrender(prompt):
        return prompt.lower() == "s"

    @staticmethod
    def to_surrender():
        while True:
            choice = input("Are you sure you want to surrender? [Y/N]: ")
            if choice.lower() == "y":
                print(Color.RED + "You surrendered! Coward move..." + Color.RESET)
                return True
            elif choice.lower() == "n":
                return False
            else:
                print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)

    @staticmethod
    def is_exchange(prompt):
        return prompt.lower() == "x"

    @staticmethod
    def find_moves(board, mandatory_jump, player_turn):
        if player_turn:
            letter = "w"
        else:
            letter = "b"
        available_moves = []
        available_jumps = []
        for m in range(8):
            for n in range(8):
                if (player_turn and board[m][n][0].lower() == "w") or (not player_turn and board[m][n][0] == "B"):
                    if Checkers.available_move(board, letter, m, n, m - 1, n + 1):
                        available_moves.append([board[m][n], m, n, m - 1, n + 1])
                    if Checkers.available_move(board, letter, m, n, m - 1, n - 1):
                        available_moves.append([board[m][n], m, n, m - 1, n - 1])
                    if Checkers.available_jump(board, letter, m, n, m - 1, n + 1, m - 2, n + 2):
                        available_jumps.append([board[m][n], m, n, m - 2, n + 2])
                    if Checkers.available_jump(board, letter, m, n, m - 1, n - 1, m - 2, n - 2):
                        available_jumps.append([board[m][n], m, n, m - 2, n - 2])
                if (player_turn and board[m][n][0] == "W") or (not player_turn and board[m][n][0].lower() == "b"):
                    if Checkers.available_move(board, letter, m, n, m + 1, n - 1):
                        available_moves.append([board[m][n], m, n, m + 1, n - 1])
                    if Checkers.available_move(board, letter, m, n, m + 1, n + 1):
                        available_moves.append([board[m][n], m, n, m + 1, n + 1])
                    if Checkers.available_jump(board, letter, m, n, m + 1, n - 1, m + 2, n - 2):
                        available_jumps.append([board[m][n], m, n, m + 2, n - 2])
                    if Checkers.available_jump(board, letter, m, n, m + 1, n + 1, m + 2, n + 2):
                        available_jumps.append([board[m][n], m, n, m + 2, n + 2])
        if mandatory_jump is False:
            available_moves += available_jumps
            return available_moves
        else:
            if len(available_jumps) == 0:
                return available_moves
            return available_jumps

    @staticmethod
    def available_move(board, letter, m, n, new_m, new_n):
        if new_m < 0 or new_m > 7 or new_n < 0 or new_n > 7:
            return False
        if board[m][n][0].lower() != letter:
            return False
        if board[new_m][new_n] != " . ":
            return False
        return True

    @staticmethod
    def available_jump(board, letter, m, n, by_m, by_n, new_m, new_n):
        if letter.lower() == "w":
            opponent_letter = "b"
        else:
            opponent_letter = "w"
        if new_m < 0 or new_m > 7 or new_n < 0 or new_n > 7:
            return False
        if board[m][n][0].lower() != letter:
            return False
        if board[by_m][by_n][0].lower() != opponent_letter:
            return False
        if board[new_m][new_n] != " . ":
            return False
        return True

    @staticmethod
    def make_a_move(board, move):
        letter = board[move[1]][move[2]][0]
        if letter == "w" and move[3] == 0:
            letter = "W"
        elif letter == "b" and move[3] == 7:
            letter = "B"
        board[move[3]][move[4]] = letter + move[0][1] + move[0][2]
        if abs(move[1] - move[3]) == 2:
            board[(move[1] + move[3]) // 2][(move[2] + move[4]) // 2] = " . "
        board[move[1]][move[2]] = " . "

    def play(self):
        print(Color.PURPLE + "Welcome to Checkers!" + Color.RESET)
        print("""
        First, a few rules:
        1. You select pieces by typing it's name without the letter 'w' or 'b'
        2. You move pieces by typing the row and column of the destination
        3. You can quit the game at any moment by pressing ENTER
        4. You can surrender the game at any moment by pressing 's'
        """)
        while True:
            choice = input("Is jumping mandatory? [Y/N]: ")
            if choice.lower() == "y":
                self.mandatory_jump = True
                break
            elif choice.lower() == "n":
                self.mandatory_jump = False
                break
            elif choice == "":
                print(Color.YELLOW + "Game ended!" + Color.RESET)
                game_over()
            elif choice.lower() == "s":
                while True:
                    choice = input("Are you sure you want to surrender? [Y/N]: ")
                    if choice.lower() == "y":
                        print(Color.RED + "You surrendered before the game even started!" + Color.RESET)
                        game_over()
                    elif choice.lower() == "n":
                        break
                    else:
                        print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
            else:
                print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)
        while True:
            Checkers.print_matrix(self.matrix, self.player_turn, self.mandatory_jump)
            print("MY PIECES: %d\tCOMPUTER'S PIECES: %d" % (self.player_pieces, self.computer_pieces))
            if self.player_turn:
                print(Color.PURPLE + "Player's turn!" + Color.RESET)
                self.player_move()
            else:
                print(Color.PURPLE + "Computer's turn!" + Color.RESET)
                print("Thinking...")
                self.computer_move()
            if self.player_pieces == 0:
                print(Color.RED + "You have no pieces left! YOU LOSE!" + Color.RESET)
                game_over()
            elif self.computer_pieces == 0:
                print(Color.GREEN + "Computer has no pieces left! YOU WIN!" + Color.RESET)
                game_over()
            self.player_turn = not self.player_turn

    @staticmethod
    def minimax(board, alfa, beta, depth, maximizing_player, mandatory_jump):
        if depth == 0:
            return Checkers.heuristic(board)
        current_state = State(board)
        if maximizing_player:
            max_eval = -inf
            for child in current_state.get_children(mandatory_jump, True):
                ev = Checkers.minimax(child.get_board(), alfa, beta, depth - 1, False, mandatory_jump)
                max_eval = max(max_eval, ev)
                alfa = max(alfa, ev)
                if beta <= alfa:
                    break
            return max_eval
        else:
            min_eval = inf
            for child in current_state.get_children(mandatory_jump, False):
                ev = Checkers.minimax(child.get_board(), alfa, beta, depth - 1, True, mandatory_jump)
                min_eval = min(min_eval, ev)
                beta = min(beta, ev)
                if beta <= alfa:
                    break
            return min_eval

    @staticmethod
    def heuristic(board):
        result = 0
        computer = 0
        opponent = 0
        for i in range(8):
            for j in range(8):
                if board[i][j][0].lower() == "w":
                    opponent += 1
                elif board[i][j][0] == "W":
                    opponent += 5
                else:
                    computer += 1
                    if board[i][j][0] == "b":
                        result += 5
                    if board[i][j][0] == "B":
                        result += 10
                    if i == 0 or i == 7 or j == 0 or j == 7:
                        result += 10
                    if 3 <= i <= 4 and 2 <= j <= 5:
                        if board[i][j][0].lower() == "b":
                            result += 5
                        if board[i][j][0].lower() == "w":
                            result -= 5
                    if 3 <= i <= 4 and (j < 2 or j > 5):
                        if board[i][j][0].lower() == "b":
                            result += 3
                        if board[i][j][0].lower() == "w":
                            result -= 3
                    if i + 1 > 7:
                        continue
                    if j + 1 > 7:
                        continue
                    if board[i][j][0].lower() == "b" and board[i + 1][j + 1][0].lower() == "b":
                        result += 3
                    if j - 1 < 0:
                        continue
                    if board[i][j][0].lower() == "b" and board[i + 1][j - 1][0].lower() == "b":
                        result += 3
                    if i - 1 < 0:
                        continue
                    if board[i][j][0].lower() == "b" and board[i - 1][j + 1][0].lower() == " . ":
                        result -= 3
                    if board[i + 1][j - 1][0].lower() == "w":
                        result -= 3
                    if board[i][j][0].lower() == "b" and board[i - 1][j - 1][0].lower() == " . ":
                        result -= 3
                    if board[i + 1][j + 1][0].lower() == "w":
                        result -= 3

        return result + (computer - opponent) * 1000


def game_over():
    while True:
        new_game = input(Color.BOLD + "Do you want to play again? (Y/N): " + Color.RESET)
        if new_game.lower() == "y":
            main()
        elif new_game.lower() == "n":
            print(Color.YELLOW + "Thanks for playing! :)" + Color.RESET)
            exit()
        else:
            print(Color.BOLD + "Invalid choice! Please try again." + Color.RESET)


def main():
    game = Checkers()
    game.play()


if __name__ == "__main__":
    main()
