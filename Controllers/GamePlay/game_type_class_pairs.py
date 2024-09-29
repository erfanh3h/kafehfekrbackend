from Entities.Games.game_types import GameTypesEnum
from Controllers.GameSession.box_four_game_session import BoxFourGameSession
from Controllers.GameSession.backgammon_game_session import BackGammonGameSession
from Controllers.GameSession.battleship_game_session import BattleShipGameSession
from Controllers.GameSession.checkers_game_session import CheckersGameSession
from Controllers.GameSession.chess_game_session import ChessGameSession
from Controllers.GameSession.dotbox_game_session import DotBoxGameSession
from Controllers.GameSession.fekrbekr_game_session import FekrBekrGameSession
from Controllers.GameSession.four_in_row_game_session import FourInRowGameSession
from Controllers.GameSession.mill_game_session import MillGameSession
from Controllers.GameSession.mnumbers_game_session import MNumbersGameSession
from Controllers.GameSession.msweeper_game_session import MSweeperGameSession
from Controllers.GameSession.othello_game_session import OthelloGameSession
from Controllers.GameSession.pentago_game_session import PentagoGameSession
from Controllers.GameSession.rpc_game_session import RPCGameSession
from Controllers.GameSession.sudoku_game_session import SudokuGameSession
from Controllers.GameSession.ten_game_session import TenGameSession
from Controllers.GameSession.tictactoe_game_session import TicTacToeGameSession
from Controllers.GameSession.yatzy_game_session import YatzyGameSession
from Controllers.GameSession.yinsh_game_session import YinshGameSession

game_type_class_pairs = {GameTypesEnum.TIC_TAC_TOE.value: TicTacToeGameSession,
                         GameTypesEnum.CHECKERS.value: CheckersGameSession, GameTypesEnum.CHESS.value: ChessGameSession,
                         GameTypesEnum.OTHELLO.value: OthelloGameSession, GameTypesEnum.MILL.value: MillGameSession,
                         GameTypesEnum.MNUMBERS.value: MNumbersGameSession,
                         GameTypesEnum.MSweeper.value: MSweeperGameSession,
                         GameTypesEnum.RPC.value: RPCGameSession, GameTypesEnum.TEN.value: TenGameSession,
                         GameTypesEnum.DOTBOX.value: DotBoxGameSession, GameTypesEnum.YATZY.value: YatzyGameSession,
                         GameTypesEnum.FOURINROW.value: FourInRowGameSession,
                         GameTypesEnum.SUDOKU.value: SudokuGameSession,
                         GameTypesEnum.BATTLESHIP.value: BattleShipGameSession,
                         GameTypesEnum.BOXFOUR.value: BoxFourGameSession,
                         GameTypesEnum.FEKRBEKR.value: FekrBekrGameSession,
                         GameTypesEnum.PENTAGO.value: PentagoGameSession,
                         GameTypesEnum.YINSH.value: YinshGameSession,
                         GameTypesEnum.BACKGAMMON.value: BackGammonGameSession}
