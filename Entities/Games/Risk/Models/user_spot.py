from Entities.Games.Risk import RiskStrategyModel, RiskContinentModel


class UserSpotClass:

    def __init__(self, index):
        self.index = index
        self.strategies: list[RiskStrategyModel] = []
        self.continents: dict[RiskContinentModel: int] = {}
        self.tokens: list[RiskContinentModel] = []
        for continet in RiskContinentModel.all():
            self.continents[continet.value] = 0

    def __str__(self):
        return str(self.index)

    def add_strategy(self, card: RiskStrategyModel):
        self.strategies.append(card)

    def remove_strategy(self, card: RiskStrategyModel):
        self.strategies.remove(card)

    def add_continent(self, card: RiskContinentModel):
        self.continents[card.value] += 1

    def remove_continent(self, card: RiskContinentModel):
        self.continents[card.value] -= 1

    def add_token(self, card: RiskContinentModel):
        self.tokens.append(card)

    def remove_token(self, card: RiskContinentModel):
        self.tokens.remove(card)

    def to_private_json(self):
        strategies: list[str] = []
        for strategy in self.strategies:
            strategies.append(strategy.value)
        return {"index": self.index, "continents": self.continents, "strategies": strategies, 'tokens': self.tokens}

    def to_global_json(self):
        return {"index": self.index, "continents": self.continents, "strategies_count": len(self.strategies),
                'tokens': self.tokens}
