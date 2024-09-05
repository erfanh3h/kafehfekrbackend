import socketio

from Commons import static_functions
# from Entities.SocketIOClass import Socket_Server, return_random_idies
from Controllers.GameSession.box_four_game_session import BoxFourGameSession
from Controllers.GameSession.backgammon_game_session import BackGammonGameSession
from Controllers.GameSession.battleship_game_session import BattleShipGameSession
from Controllers.GameSession.checkers_game_session import CheckersGameSession
from Controllers.GameSession.chess_game_session import ChessGameSession
from Controllers.GameSession.dotbox_game_session import DotBoxGameSession
from Controllers.GameSession.four_in_row_game_session import FourInRowGameSession
from Controllers.GameSession.mill_game_session import MillGameSession
from Controllers.GameSession.mnumbers_game_session import MNumbersGameSession
from Controllers.GameSession.msweeper_game_session import MSweeperGameSession
from Controllers.GameSession.othello_game_session import OthelloGameSession
from Controllers.GameSession.rpc_game_session import RPCGameSession
from Controllers.GameSession.sudoku_game_session import SudokuGameSession
from Controllers.GameSession.ten_game_session import TenGameSession
from Controllers.GameSession.tictactoe_game_session import TicTacToeGameSession
from Controllers.GameSession.yatzy_game_session import YatzyGameSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Gamer import GamerModel

# current_game_id = "gameId"
# gameSession = MillGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = MNumbersGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = CheckersGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = TenGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = ChessGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = YatzyGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = FourInRowGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = SudokuGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = BattleShipGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = BoxFourGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = BackGammonGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = TicTacToeGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = RPCGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = OthelloGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = DotBoxGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)
# gameSession = MSweeperGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL)

# gameSession.add_gamer(GamerModel(user_id="0", username='test'))
# gameSession.add_gamer(GamerModel(user_id="1", username='mobile'))
# gameSession.start_game_timer()

# games = {current_game_id: gameSession}
# game_idies = [current_game_id]
# socketid_gameid_pairs = {}

games = {}
game_idies = []
socketid_gameid_pairs = {}

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
                         GameTypesEnum.BACKGAMMON.value: BackGammonGameSession}


def add_new_game(game_id, queuers, game_type, game_score_type):
    gameSession = game_type_class_pairs[game_type.value](game_id=game_id, game_type=game_type,
                                                         game_score_type=game_score_type)
    gameSession.add_gamer(
        GamerModel(user_id=queuers[0].user_id, username=queuers[0].username, user_image=queuers[0].user_image))
    gameSession.add_gamer(
        GamerModel(user_id=queuers[1].user_id, username=queuers[1].username, user_image=queuers[1].user_image))
    gameSession.start_game_timer()
    games[game_id] = gameSession
    game_idies.append(game_id)


def delete_game(game_id):
    try:
        del games[game_id]
        game_idies.remove(game_id)
    except:
        pass


class GameSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        print('connect ', socket_id)
        if auth is not None:
            try:
                # user_id = auth['user_id']
                user_game_id = auth['game_id']
                from Entities.Security import extract_token
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                else:
                    await self.disconnect(socket_id, namespace="/game")
                    return
            except:
                await self.disconnect(socket_id, namespace="/game")
                return
        else:
            await self.disconnect(socket_id, namespace="/game")
            return
        # print(Socket_Server.namespaces)
        #     await my_message(socket_id, {'Test': f'{socket_id}'})

        if is_game_id_valid(user_game_id):
            if games[user_game_id].gamer_idies.__contains__(user_id):
                await self.enter_room(socket_id, user_game_id, namespace="/game")
                games[user_game_id].join_gamer(user_id, socket_id)
                socketid_gameid_pairs[socket_id] = user_game_id
            else:
                await self.disconnect(socket_id, namespace="/game")
                return
        else:
            await self.emit('command', {'id': 'GameFinished'}, to=socket_id, namespace="/game")
            # await self.disconnect(socket_id, namespace="/game")

    async def on_disconnect(self, socket_id):
        game_id = return_gameid_from_socketid(socket_id)
        if game_id is not None:
            await self.leave_room(socket_id, game_id, namespace="/game")
            try:
                games[game_id].disconnect_user(socket_id)
            except KeyError:
                pass
            del socketid_gameid_pairs[socket_id]
        print('disconnect ', socket_id)

    async def on_user_command(self, socket_id, data):
        game_id = return_gameid_from_socketid(socket_id)
        if game_id is not None:
            try:
                await games[game_id].command_received(data, socket_id)
            except:
                pass
            print('User Sended command ', data)

    async def on_user_reaction(self, socket_id, data):
        game_id = return_gameid_from_socketid(socket_id)
        if game_id is not None:
            try:
                await games[game_id].reaction_received(data, socket_id)
            except:
                pass
            print('User Sended command ', data)


def is_game_id_valid(recived_game_id):
    for game_id in game_idies:
        if game_id == recived_game_id:
            return True
    return False


def return_gameid_from_socketid(socket_id):
    for raw_socket_id in socketid_gameid_pairs.keys():
        if raw_socket_id == socket_id:
            return socketid_gameid_pairs[raw_socket_id]
    return None


def return_random_idies():
    user_id = static_functions.create_random_name()
    user_game_id = static_functions.create_random_name()
    return user_id, user_game_id
