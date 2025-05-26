from Entities.Games.Risk import RiskGameClass


class RiskDrawHandler:
    def __init__(self, game: RiskGameClass):
        self.game: RiskGameClass = game

    def draw_card(self, draw_type):
        if draw_type == 1:
            continent1 = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent1)
            continent2 = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent2)
            return [continent1.value, continent2.value]
        elif draw_type == 2:
            strategy1 = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy1)
            strategy2 = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy2)
            return [strategy1.value, strategy2.value]
        elif draw_type == 3:
            continent = self.game.continents.pop()
            self.game.players_data[self.game.current_turn - 1].add_continent(continent)
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
            return [continent.value, strategy.value]
        elif draw_type == 4:  # for pass turn
            strategy = self.game.strategies.pop()
            self.game.players_data[self.game.current_turn - 1].add_strategy(strategy)
            return [strategy.value]
        return None
