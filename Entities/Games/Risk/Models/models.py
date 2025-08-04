from enum import Enum
from typing import List


class RiskStrategyModel(Enum):
    ARMY = "Army"
    BACKUP = "Backup"
    BOMB = "Bomb"
    DESTROY = "Destroy"
    CANCEL = "Cancel"
    CANON = "Canon"
    EXPAND = "Expand"
    SPY = "Spy"


class RiskContinentModel(Enum):
    ASIA = "Asia"
    AFRICA = "Africa"
    EUROPE = "Europe"
    NORTHAMERICA = "NorthAmerica"
    SOUTHAMERICA = "SouthAmerica"
    AUSTRALIA = "Australia"

    @classmethod
    def all(cls) -> List[Enum]:
        return list(cls)

    @classmethod
    def data_to_model(cls, data):
        if data == "Asia":
            return cls.ASIA
        if data == "Africa":
            return cls.AFRICA
        if data == "Europe":
            return cls.EUROPE
        if data == "NorthAmerica":
            return cls.NORTHAMERICA
        if data == "SouthAmerica":
            return cls.SOUTHAMERICA
        else:
            return cls.AUSTRALIA
