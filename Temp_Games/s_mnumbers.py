import random


class boardSpot:

    def __init__(self):
        self.value = 0
        self.equipped_user = 0

    def __str__(self):
        return str(self.value)


class MNumbersGameClass:
    def __init__(self):
        self.board = [boardSpot() for i in range(36)]
        self.player1_score = 0
        self.player2_score = 0
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.current_turn = 1
        self.init_board()

    def init_board(self):
        for i in range(18):
            index = i * 2
            value = i + 1
            self.board[index].value = value
            self.board[index + 1].value = value
        random.shuffle(self.board)
        random.shuffle(self.board)

    def is_peace_available(self, index):
        return self.board[index].equipped_user == 0

    def is_peace_have_selection(self, index):
        return self.board[index].equipped_user != 0

    def change_active_player(self):
        if self.current_turn == 1:
            self.current_turn += 1
        else:
            self.current_turn = 1

    def get_value_of_location(self, input_value):
        return self.board[input_value]

    def get_user_input(self):
        x1 = input(f"player{self.current_turn} , enter your first peace : ")
        while not self.is_peace_available(int(x1)):
            print('invalid peace .')
            x1 = input(f"player{self.current_turn} , enter your first peace : ")
        x2 = input(f"player{self.current_turn} , enter your second peace : ")
        while not self.is_peace_available(int(x2)):
            print('invalid peace .')
            x2 = input(f"player{self.current_turn} , enter your second peace : ")
        return int(x1), int(x2)

    def check_match_two(self, index1, index2) -> bool:
        if self.board[index1].value == self.board[index2].value:
            return True
        else:
            return False

    def submit_peaces_for_user(self, index1, index2):
        if self.current_turn == 1:
            user_label = self.symbol_1
            self.player1_score += 1
        else:
            user_label = self.symbol_2
            self.player2_score += 1
        self.board[index1].equipped_user = user_label
        self.board[index2].equipped_user = user_label

    def get_game_winner(self):
        if self.player1_score > self.player2_score:
            return self.symbol_1
        elif self.player2_score > self.player1_score:
            return self.symbol_2
        else:
            return 0

    def check_end_game(self):
        is_game_finished = True
        for index in range(0, len(self.board)):
            if self.is_peace_available(index):
                is_game_finished = False
                break
        if not is_game_finished:
            return is_game_finished
        else:
            return True

    def print_game(self):
        print(f"""
        {self.board[0]}-{self.board[1]}-{self.board[2]}-{self.board[3]}-{self.board[4]}-{self.board[5]}
        {self.board[6]}-{self.board[7]}-{self.board[8]}-{self.board[9]}-{self.board[10]}-{self.board[11]}
        {self.board[12]}-{self.board[13]}-{self.board[14]}-{self.board[15]}-{self.board[16]}-{self.board[17]}
        {self.board[18]}-{self.board[19]}-{self.board[20]}-{self.board[21]}-{self.board[22]}-{self.board[23]}
        {self.board[24]}-{self.board[25]}-{self.board[26]}-{self.board[27]}-{self.board[28]}-{self.board[29]}
        {self.board[30]}-{self.board[31]}-{self.board[32]}-{self.board[33]}-{self.board[34]}-{self.board[35]}
        """)

    def print_equippes(self):
        print(f"""
        {self.board[0].equipped_user}-{self.board[1].equipped_user}-{self.board[2].equipped_user}-{self.board[3].equipped_user}-{self.board[4].equipped_user}-{self.board[5].equipped_user}
        {self.board[6].equipped_user}-{self.board[7].equipped_user}-{self.board[8].equipped_user}-{self.board[9].equipped_user}-{self.board[10].equipped_user}-{self.board[11].equipped_user}
        {self.board[12].equipped_user}-{self.board[13].equipped_user}-{self.board[14].equipped_user}-{self.board[15].equipped_user}-{self.board[16].equipped_user}-{self.board[17].equipped_user}
        {self.board[18].equipped_user}-{self.board[19].equipped_user}-{self.board[20].equipped_user}-{self.board[21].equipped_user}-{self.board[22].equipped_user}-{self.board[23].equipped_user}
        {self.board[24].equipped_user}-{self.board[25].equipped_user}-{self.board[26].equipped_user}-{self.board[27].equipped_user}-{self.board[28].equipped_user}-{self.board[29].equipped_user}
        {self.board[30].equipped_user}-{self.board[31].equipped_user}-{self.board[32].equipped_user}-{self.board[33].equipped_user}-{self.board[34].equipped_user}-{self.board[35].equipped_user}
        """)

    def play_game(self):
        while 1:
            self.print_game()
            self.print_equippes()
            user_peaces = self.get_user_input()
            if self.check_match_two(user_peaces[0], user_peaces[1]):
                self.submit_peaces_for_user(user_peaces[0], user_peaces[1])
                if self.check_end_game():
                    print(f"player {self.get_game_winner()} won .")
                    break
            else:
                print("Wrong selections")
            self.change_active_player()


mNumberClass = MNumbersGameClass()
mNumberClass.play_game()
