import random


def roll_dices():
    result = []
    for i in range(2):
        result.append(random.randint(1, 6))
    if result[0] == result[1]:
        result.append(result[0])
        result.append(result[0])
    print(result)
    return result


class BoardSpotClass:

    def __init__(self):
        self.count = 0
        self.equipped_user = 0

    def __str__(self):
        return str(self.count)

    def add_piece(self, equipped_user, count=1):
        self.count += count
        self.equipped_user = equipped_user

    def remove_piece(self, count=1):
        self.count -= count
        if self.count == 0:
            self.equipped_user = 0

    def clear(self):
        self.count = 0
        self.equipped_user = 0

    def is_single(self):
        return self.count == 1

    def is_gamer_id_spot(self, gamer_id):
        return self.equipped_user == gamer_id

    def is_enemy_spot(self, gamer_id):
        return self.equipped_user != 0 and self.equipped_user != gamer_id


class BackGammonGameClass:
    def __init__(self, ):
        super().__init__()
        self.board = [BoardSpotClass() for i in range(24)]
        self.player1_score = 0
        self.player2_score = 0
        self.symbol_1 = 1
        self.symbol_2 = 2
        self.current_turn = 1
        self.init_board()
        self.current_dices = []
        self.player1_out_pieces = 0
        self.player2_out_pieces = 0

    def init_board(self):
        self.board[0].add_piece(1, 2)
        self.board[23].add_piece(2, 2)
        self.board[5].add_piece(2, 5)
        self.board[18].add_piece(1, 5)
        self.board[7].add_piece(2, 3)
        self.board[16].add_piece(1, 3)
        self.board[11].add_piece(1, 5)
        self.board[12].add_piece(2, 5)

    def is_peace_available(self, index):
        return self.board[index].count == 0

    def is_peace_have_selection(self, index):
        return self.board[index].count != 0

    def change_active_player(self):
        if self.current_turn == 1:
            self.current_turn += 1
        else:
            self.current_turn = 1

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
        {self.board[0]}----------{self.board[23]}
        {self.board[1]}----------{self.board[22]}
        {self.board[2]}----------{self.board[21]}
        {self.board[3]}----------{self.board[20]}
        {self.board[4]}----------{self.board[19]}
        {self.board[5]}----------{self.board[18]}
        {self.board[6]}----------{self.board[17]}
        {self.board[7]}----------{self.board[16]}
        {self.board[8]}----------{self.board[15]}
        {self.board[9]}----------{self.board[14]}
        {self.board[10]}----------{self.board[13]}
        {self.board[11]}----------{self.board[12]}
        """)

    def print_equippes(self):
        print(f"""
        {self.board[0].equipped_user}----------{self.board[23].equipped_user}
        {self.board[1].equipped_user}----------{self.board[22].equipped_user}
        {self.board[2].equipped_user}----------{self.board[21].equipped_user}
        {self.board[3].equipped_user}----------{self.board[20].equipped_user}
        {self.board[4].equipped_user}----------{self.board[19].equipped_user}
        {self.board[5].equipped_user}----------{self.board[18].equipped_user}
        {self.board[6].equipped_user}----------{self.board[17].equipped_user}
        {self.board[7].equipped_user}----------{self.board[16].equipped_user}
        {self.board[8].equipped_user}----------{self.board[15].equipped_user}
        {self.board[9].equipped_user}----------{self.board[14].equipped_user}
        {self.board[10].equipped_user}----------{self.board[13].equipped_user}
        {self.board[11].equipped_user}----------{self.board[12].equipped_user}
        """)

    def move_piece(self, index, dice, gamer_id):
        self.board[index].remove_piece()
        target_index = index + dice
        if self.board[target_index].is_enemy_spot(gamer_id):
            if self.board[target_index].is_single():
                if gamer_id == 1:
                    self.player2_out_pieces += 1
                else:
                    self.player1_out_pieces += 1
                self.board[target_index].remove_piece()
                self.board[target_index].add_piece(gamer_id)
        else:
            self.board[target_index].add_piece(gamer_id)

    def get_my_piece_indexes(self,gamer_id):
        result = []
        for index in range(0, len(self.board)):
            if self.board[index].equipped_user == gamer_id:
                result.append(index)
        return result

    def play_game(self):
        self.print_game()
        self.print_equippes()
        dices = roll_dices()
        print(self.get_my_piece_indexes(2))
        # self.move_piece(0, 6, self.symbol_1)
        # self.print_game()
        # self.print_equippes()
        # self.move_piece(5, 1, self.symbol_2)
        # self.print_game()
        # self.print_equippes()
        # print(self.player1_out_pieces, self.player2_out_pieces)


backGommonClass = BackGammonGameClass()
backGommonClass.play_game()
