# base_self.board = np.array([['0', ' ', ' ', '1', ' ', ' ', '2'],
#                        [' ', '3', ' ', '4', ' ', '5', ' '],
#                        [' ', ' ', '6', '7', '8', ' ', ' '],
#                        ['9', '10', '11', ' ', '12', '13', '14'],
#                        [' ', ' ', '15', '16', '17', ' ', ' '],
#                        [' ', '18', ' ', '19', ' ', '20', ' '],
#                        ['21', ' ', ' ', '22', ' ', ' ', '23']
#                        ])

class MillGameClass:
    def __init__(self):
        self.board = [0 for i in range(24)]
        self.player1_peaces = 10
        self.player2_peaces = 10
        self.player1_played_peaces = 0
        self.player2_played_peaces = 0
        self.player1_removed_peaces = 0
        self.player2_removed_peaces = 0
        self.player1Label = 1
        self.player2Label = 2
        self.current_turn = 1

        self.win_conditions = [[0, 1, 2], [0, 9, 21], [21, 22, 23], [23, 14, 2], [1, 4, 7], [9, 10, 11], [22, 19, 16],
                               [14, 13, 12], [3, 4, 5], [3, 10, 18], [18, 19, 20], [20, 13, 5], [6, 7, 8], [6, 11, 15],
                               [15, 16, 17],
                               [17, 12, 8], ]

        self.pieces_neighbors = {0: [1, 9], 1: [0, 2, 4], 2: [1, 14], 3: [4, 10], 4: [1, 3, 5, 7], 5: [4, 13],
                                 6: [7, 11],
                                 7: [4, 6, 8], 8: [7, 12], 9: [0, 10, 21], 10: [3, 9, 11, 18], 11: [6, 10, 15],
                                 12: [8, 13, 17],
                                 13: [5, 12, 14, 20], 14: [2, 13, 23], 15: [11, 16], 16: [15, 17, 19], 17: [12, 16],
                                 18: [10, 19],
                                 19: [16, 18, 20, 22], 20: [13, 19], 21: [9, 22], 22: [19, 21, 23], 23: [14, 22]}

    def is_peace_available(self, index):
        return self.board[index] == 0

    def is_peace_have_selection(self, index):
        return self.board[index] != 0

    # this function uses to see user need to move piece or enter one piece on self.board
    def check_player_all_pieces_placed(self) -> bool:

        if self.current_turn == 1:
            if self.player1_played_peaces < self.player1_peaces:
                return False
            else:
                return True
        else:
            if self.player2_played_peaces < self.player2_peaces:
                return False
            else:
                return True

    # this function uses to change active user index
    def change_active_player(self):
        if self.current_turn == 1:
            self.current_turn += 1
        else:
            self.current_turn = 1

    def get_value_of_location(self, input_value):
        return self.board[input_value]

    # this function uses to swap desired piece on self.board with a neighbor empty place
    def swap_pieces_values(self, old_location, new_location, user_label):
        self.board[int(old_location)] = 00
        self.board[int(new_location)] = user_label

    def get_user_input(self, user_label) -> int:
        x1 = input(f"player{user_label} , enter your move : ")
        while not self.is_peace_available(int(x1)):
            print('invalid move . please enter again : ')
            x1 = input(f"player{user_label} , enter your move : ")
        return int(x1)

    # this function uses to move user piece on the self.board
    def move_user_input(self, user_label) -> str:

        input_value = input(f"player{user_label} , enter your piece : ")
        while not self.is_peace_have_selection(int(input_value)):
            print('Invalid piece . please enter again : ')
            input_value = input(f"player{user_label} , enter your piece : ")
        location_label = self.get_value_of_location(int(input_value))
        if location_label == user_label:
            return self.swap_peaces_input_action(int(input_value), user_label)
        else:
            print('invalid piece . please enter again. ')
            return self.move_user_input(user_label)

    def swap_peaces_input_action(self, input_value, user_label):
        target_location = input("Enter target location : ")
        while int(target_location) not in self.pieces_neighbors[input_value]:
            print('Invalid location . please enter again : ')
            target_location = input("Enter target location : ")
        if self.is_peace_available(int(target_location)):
            self.swap_pieces_values(input_value, target_location, user_label)
        else:
            print('Invalid empty location . please enter again : ')
            return self.swap_peaces_input_action(input_value, user_label)
        return int(target_location)

    # this function uses to submit user desired location on self.board
    def submit_new_place(self, input_value):
        if self.current_turn == 1:
            if self.is_peace_available(input_value):
                self.board[input_value] = self.player1Label
                self.player1_played_peaces += 1
        else:
            if self.is_peace_available(input_value):
                self.board[input_value] = self.player2Label
                self.player2_played_peaces += 1

    # this function uses to check whether user have a win condition or not
    def check_win(self, userInput, user_label):
        temp_list = []
        for raw_data in self.win_conditions:
            if raw_data.__contains__(userInput):
                temp_list.append(raw_data)

        for raw_data in temp_list:
            raw_result = self.check_match_three(raw_data, user_label)
            if raw_result:
                self.remove_peace_from_board()

    # this function uses to check each win condition accorded or nor according to win condition
    def check_match_three(self, raw_data, user_label) -> bool:
        for data in raw_data:
            if self.board[data] != user_label:
                return False
        return True

    # this function uses to remove one of opponent pieces after win 3
    def remove_peace_from_board(self):
        if self.current_turn == 1:
            self.remove_piece_from_board(self.player2Label)
            self.player2_removed_peaces += 1
        else:
            self.remove_piece_from_board(self.player1Label)
            self.player2_removed_peaces += 1

    # this function uses to remove one piece of opponent from self.board
    def remove_piece_from_board(self, possible_pieces_label):
        target_location = input("Remove one of opponent pieces from self.board:")
        while not self.is_peace_have_selection(int(target_location)):
            print('Invalid piece .')
            target_location = input("Please remove one of opponent pieces from board:")

        if self.board[int(target_location)] == possible_pieces_label:
            self.board[int(target_location)] = 0
        else:
            print('Invalid piece .')
            self.remove_piece_from_board(possible_pieces_label)

    def check_end_game(self) -> int:
        if self.player1_peaces - self.player1_removed_peaces < 3:
            print(f"Player{self.player2Label} win game.")
            return 2
        elif self.player2_peaces - self.player2_removed_peaces < 3:
            print(f"Player{self.player1Label} win game.")
            return 1
        else:
            return 0

    def print_game(self):
        print(f"""
        {self.board[0]}      {self.board[1]}      {self.board[2]}
          {self.board[3]}    {self.board[4]}    {self.board[5]}  
            {self.board[6]}  {self.board[7]}  {self.board[8]}    
        {self.board[9]} {self.board[10]} {self.board[11]}     {self.board[12]} {self.board[13]} {self.board[14]}
            {self.board[15]}  {self.board[16]}  {self.board[17]}    
          {self.board[18]}    {self.board[19]}    {self.board[20]}  
        {self.board[21]}      {self.board[22]}      {self.board[23]}
        """)
        print(self.player1_peaces, self.player1_played_peaces, self.player1_removed_peaces)
        print(self.player2_peaces, self.player2_played_peaces, self.player2_removed_peaces)

    def play_game(self):
        self.print_game()
        winner_label = 0
        while 1:
            if self.current_turn == 1:
                activeuser_label = self.player1Label
            else:
                activeuser_label = self.player2Label

            if self.check_player_all_pieces_placed():
                player_input = self.move_user_input(activeuser_label)
            else:
                player_input = self.get_user_input(activeuser_label)
                self.submit_new_place(player_input)

            self.check_win(player_input, activeuser_label)
            self.change_active_player()
            self.print_game()
            winner_label = self.check_end_game()
            if winner_label != 0:
                break


millClass = MillGameClass()
millClass.play_game()
