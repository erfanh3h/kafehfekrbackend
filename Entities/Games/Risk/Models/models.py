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

    @classmethod
    def all(cls) -> List["RiskStrategyModel"]:
        return list(cls)

    @classmethod
    def data_to_model(cls, data):
        if isinstance(data, cls):
            return data
        s = str(data).strip().lower()
        for member in cls:
            if member.value.lower() == s or member.name.lower() == s:
                return member
        return None


class RiskContinentModel(Enum):
    ASIA = "Asia"
    AFRICA = "Africa"
    EUROPE = "Europe"
    NORTHAMERICA = "NorthAmerica"
    SOUTHAMERICA = "SouthAmerica"
    AUSTRALIA = "Australia"

    @classmethod
    def all(cls) -> List["RiskContinentModel"]:
        return list(cls)

    @classmethod
    def data_to_model(cls, data):
        if isinstance(data, cls):
            return data
        s = str(data).strip().lower().replace("_", "").replace(" ", "")
        if s == "asia":
            return cls.ASIA
        elif s == "africa":
            return cls.AFRICA
        elif s == "europe":
            return cls.EUROPE
        elif s in ("northamerica", "na"):
            return cls.NORTHAMERICA
        elif s in ("southamerica", "sa"):
            return cls.SOUTHAMERICA
        elif s == "australia":
            return cls.AUSTRALIA
        return None


class RiskGameState(Enum):
    STARTGAME = "StartGame"
    DRAW = "Draw"
    DRAWRESULT = "DrawResult"
    SELECTACTION = "SelectAction"
    DECLAREATTACK = "DeclareAttack"
    SELECTCONTINENTS = "SelectContinents"
    ACTIONRESULT = "ActionResult"
    ATTACKERARMY = "AttackerArmy"
    DEFENDERARMY = "DefenderArmy"
    QUESTARMY = "QuestArmy"
