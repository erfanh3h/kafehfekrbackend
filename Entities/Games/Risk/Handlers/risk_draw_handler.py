from Entities.Games.Risk import RiskGameClass


class RiskDrawHandler:
    def __init__(self, game: RiskGameClass):
        self.game: RiskGameClass = game

    def draw_card(self, draw_type):
        if draw_type == 1:
            continent = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent)
            continent = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent)
        elif draw_type == 2:
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
        elif draw_type == 3:
            continent = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent)
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
        elif draw_type == 4:  # for pass turn
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
