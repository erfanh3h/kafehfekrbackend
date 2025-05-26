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
