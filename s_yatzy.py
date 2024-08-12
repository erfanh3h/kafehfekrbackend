import random


class boardSpot:
    def __init__(self, index, gamer_id):
        self.index = index
        self.gamer_id = gamer_id
        self.is_selected = False
        self.score = 0

    def __str__(self):
        return str(self.score)

    def select(self, score):
        self.score = score
        self.is_selected = True


def roll_dices(count):
    result = []
    for i in range(count):
        result.append(random.randint(1, 6))
    return result


class YatzyGameClass:
    def __init__(self):
        self.player1_board = [boardSpot(index, 1) for index in range(12)]
        self.player2_board = [boardSpot(index, 2) for index in range(12)]

    def play_game(self):
        print(roll_dices(5))

    def __str__(self):
        return ""


game_class = YatzyGameClass()

game_class.play_game()
