from enum import Enum
from typing import List


class GameTypesEnum(Enum):
    TIC_TAC_TOE = "TicTacToe"
    RPC = "RPC"
    DOTBOX = "DotBox"
    TEN = "Ten"
    MNUMBERS = "MNumbers"
    MSweeper = "MSweeper"
    FEKRBEKR = "FekrBekr"
    YATZY = "Yatzy"
    PENTAGO = "Pentago"
    FOURINROW = "FourInRow"
    SUDOKU = "Sudoku"
    BATTLESHIP = "BattleShip"
    BOXFOUR = "BoxFour"
    YINSH = "Yinsh"
    CHESS = "Chess"
    CHECKERS = "Checkers"
    OTHELLO = "Othello"
    MILL = "Mill"
    LUDO = "Ludo"
    # RISK = "Risk"
    BACKGAMMON = "BackGammon"

    @classmethod
    def all(cls) -> List[Enum]:
        return list(cls)

    @classmethod
    def multi_players_games(cls, ) -> List[Enum]:
        return [cls.LUDO]

    @classmethod
    def two_players_games(cls, ) -> List[Enum]:
        data = list(cls)
        data.remove(cls.LUDO)
        return data

    @classmethod
    def is_in_two_players(cls, value) -> bool:
        data = list(cls)
        data.remove(cls.LUDO)
        for member in data:
            if member.value == value:
                return True
        return False
