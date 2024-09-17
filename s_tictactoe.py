class TicTacToeGameClass:
    def __init__(self):
        self.board = [" " for i in range(9)]
        self.win_conditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]
        self.current_turn = 1
        self.symbol_1 = "1"
        self.symbol_2 = "2"

    def start_game(self):
        count = 0
        winner = None
        # This function check if the board is full
        while count < 9 and winner is None:
            self.current_turn = count % 2
            self.play_round()
            self.printPretty()
            if count == 8:
                #print("The board is full. Game over.")
                if winner:
                    pass
                    #print("There is a tie. ")

            # Check if here is a winner
            winner = self.check_winner()
            count += 1
        if not winner:
            pass
            #print("Game over.")
        self.report(winner)

    def play_round(self):
        # This function starts the game.

        # Decides the turn
        if self.current_turn % 2 == 0:
            player = self.symbol_1
        elif self.current_turn % 2 == 1:
            player = self.symbol_2
        #print("Player " + player + ", it is your turn. ")
        peace_number = int(input("Pick a peace number : "))

        # Check if players' selection is out of range
        while peace_number < 0 or peace_number > 8:
            #print("Out of boarder. Pick another one. ")
            peace_number = int(input("Pick a peace number : "))

            # Check if the square is already filled
        while (self.board[peace_number] == self.symbol_1) or (self.board[peace_number] == self.symbol_2):
            #print("The square you picked is already filled. Pick another one.")
            peace_number = int(input("Pick a peace number : "))

            # Locates player's symbol on the board
        if player == self.symbol_1:
            self.board[peace_number] = self.symbol_1
        else:
            self.board[peace_number] = self.symbol_2

    def printPretty(self):
        # This function prints the board nice!
        print("---+---+---")
        for r in range(3):
            print(self.board[r * 3], " |", self.board[r * 3 + 1], "|", self.board[r * 3 + 2])
            print("---+---+---")

    def check_winner(self):
        winner = None
        for condition in self.win_conditions:
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_1:
                winner = self.symbol_1
                #print("Player " + self.symbol_1 + ", you won!")
                break
            if self.board[condition[0]] == self.board[condition[1]] == self.board[condition[2]] == self.symbol_2:
                winner = self.symbol_2
                print("Player " + self.symbol_2 + ", you won!")
                break
        return winner

    def report(self, winner):
        print("\n")
        input("Press enter to see the game summary. ")
        if winner is None:
            print("There is a tie. ")
        else:
            print("Winner : Player " + winner + ".")


game = TicTacToeGameClass()
game.start_game()
