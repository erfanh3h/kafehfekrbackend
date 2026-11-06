from Entities.Games.Risk.Models.models import RiskStrategyModel, RiskContinentModel


class UserSpotClass:
    def __init__(self, index: int):
        self.index: int = index
        self.strategies: list[RiskStrategyModel] = []
        self.continents: dict[str, int] = {}
        self.tokens: list[str] = []
        for continent in RiskContinentModel.all():
            self.continents[continent.value] = 0

    def __str__(self):
        return str(self.index)

    def add_strategy(self, card: RiskStrategyModel):
        if isinstance(card, str):
            card = RiskStrategyModel.data_to_model(card)
        if card is not None:
            self.strategies.append(card)

    def remove_strategy(self, card: RiskStrategyModel) -> bool:
        if isinstance(card, str):
            card = RiskStrategyModel.data_to_model(card)
        if card in self.strategies:
            self.strategies.remove(card)
            return True
        return False

    def has_strategy(self, card: RiskStrategyModel) -> bool:
        if isinstance(card, str):
            card = RiskStrategyModel.data_to_model(card)
        return card in self.strategies

    def count_strategy(self, card: RiskStrategyModel) -> int:
        if isinstance(card, str):
            card = RiskStrategyModel.data_to_model(card)
        return sum(1 for c in self.strategies if c == card)

    def add_continent(self, card, count: int = 1):
        c_model = RiskContinentModel.data_to_model(card)
        if c_model is not None and count > 0:
            self.continents[c_model.value] = self.continents.get(c_model.value, 0) + int(count)

    def remove_continent(self, card, count: int = 1) -> int:
        c_model = RiskContinentModel.data_to_model(card)
        if c_model is None or count <= 0:
            return 0
        cur = self.continents.get(c_model.value, 0)
        removed = min(cur, int(count))
        self.continents[c_model.value] = cur - removed
        return removed

    def total_continents(self) -> int:
        return sum(self.continents.values())

    def add_token(self, card):
        c_name = card.value if isinstance(card, RiskContinentModel) else str(card)
        if c_name not in self.tokens:
            self.tokens.append(c_name)

    def remove_token(self, card):
        c_name = card.value if isinstance(card, RiskContinentModel) else str(card)
        if c_name in self.tokens:
            self.tokens.remove(c_name)

    def clear(self):
        self.strategies.clear()
        for k in list(self.continents.keys()):
            self.continents[k] = 0
        self.tokens.clear()

    def to_private_json(self):
        strategies = [strategy.value for strategy in self.strategies]
        return {
            "index": self.index,
            "continents": dict(self.continents),
            "strategies": strategies,
            "tokens": list(self.tokens),
        }

    def to_global_json(self):
        return {
            "index": self.index,
            "continents": dict(self.continents),
            "strategies_count": len(self.strategies),
            "tokens": list(self.tokens),
        }
