import socketio

from Commons import static_functions
from Commons import commands
from Controllers.GamePlay import BaseGamePlayClass
from Controllers.GameSession.ludo_game_session import LudoGameSession
from Entities.Database import game_database
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Entities.Security import check_is_token_valid
from Models.Gamer import GamerModel
from Models.Queuer import QueuerModel

games = {}
game_idies = []
socketid_gameid_pairs = {}
socketid_userid_pairs = {}

def start_new_test_game():
    user1 = QueuerModel("NHD6bL", username="Windows", user_image=60,
                        user_score=1000, user_coin=1000)
    user2 = QueuerModel("kFIrrF", username="Mobile", user_image=60,
                        user_score=1000, user_coin=1000)
    queuers = [user1, user2]
    final_game_types = [GameTypesEnum.LUDO.value]
    game_id = 'testgame'
    add_new_game(game_id, queuers, final_game_types, GameScoreTypesEnum.LOBBY)


def add_new_game(game_id, queuers, game_types, game_score_type):
    game_play = BaseGamePlayClass(game_id, queuers, game_types, game_score_type)
    game_play.start_game_timer()
    games[game_id] = game_play
    game_idies.append(game_id)


# start_new_test_game()
# print(games)
def finish_single_game(game_id, user_id):
    games[game_id].finish_current_game(user_id)

def finish_multiplayer_game(game_id, rank1_id , rank2_id):
    games[game_id].finish_multiplayer_game(rank1_id , rank2_id)
def delete_game(game_id):
    # try:
    del games[game_id]
    game_idies.remove(game_id)
    # except:
    #     pass


class GameSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        import asyncio
        from Commons.static_functions import set_main_loop
        set_main_loop(asyncio.get_running_loop())
        print('connect ', socket_id)
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.emit('command', {'id': commands.Logout}, to=socket_id, namespace="/game")
            return
        user_id = token_data['id']
        user_game_id = auth['game_id']
        if is_game_id_valid(user_game_id):
            if games[user_game_id].is_user_id_valid(user_id):
                await self.enter_room(socket_id, user_game_id, namespace="/game")
                await self.enter_room(socket_id, socket_id, namespace="/game")
                socketid_gameid_pairs[socket_id] = user_game_id
                socketid_userid_pairs[socket_id] = user_id
                games[user_game_id].change_gamer_socket_id(user_id, socket_id)
                
                async def _delayed_join():
                    await asyncio.sleep(0.05)
                    try:
                        if user_game_id in games:
                            games[user_game_id].join_gamer(user_id, socket_id)
                    except Exception as e:
                        print(f"[GameSocket] Error in join_gamer: {e}")
                asyncio.create_task(_delayed_join())
            else:
                await self.disconnect(socket_id, namespace="/game")
                return
        else:
            await self.emit('command', {'id': commands.Game_Finished}, to=socket_id, namespace="/game")
            game_database.users_manager.update_user(user_id, open_game_id="")
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
        socketid_userid_pairs.pop(socket_id, None)
        print('disconnect ', socket_id)

    async def on_user_command(self, socket_id, data):
        game_id = return_gameid_from_socketid(socket_id)
        if game_id is not None and game_id in games:
            cmd_id = data.get('id') if isinstance(data, dict) else ""
            if cmd_id in ["RequestReconnectData", commands.Reconnect_Data, "reconnect_data"]:
                print(f"[GameSocket] Explicit RequestReconnectData from {socket_id} for game {game_id}")
                uid = socketid_userid_pairs.get(socket_id)
                if uid is not None and hasattr(games[game_id], 'change_gamer_socket_id'):
                    games[game_id].change_gamer_socket_id(uid, socket_id)
                if hasattr(games[game_id], 'send_game_play_data') and getattr(games[game_id], 'is_game_started', False):
                    games[game_id].send_game_play_data(socket_id)
                if hasattr(games[game_id], 'game_session') and games[game_id].game_session is not None:
                    if getattr(games[game_id].game_session, 'is_game_running', False):
                        games[game_id].game_session.send_reconnect_data(socket_id)
                elif hasattr(games[game_id], 'send_reconnect_data'):
                    games[game_id].send_reconnect_data(socket_id)
                return
            await games[game_id].command_received(data, socket_id)
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
