import socketio

from Commons import static_functions
from Commons import commands
from Controllers.GamePlay import BaseGamePlayClass
from Entities.Database import game_database

# current_game_id = "gameId"
# gameSession = YinshGameSession(game_id=current_game_id, game_score_type=GameScoreTypesEnum.NORMAL,
#                                game_type=GameTypesEnum.YINSH)

# # gameSession.add_gamer(
# #     GamerModel("kC8GgJ", username="test", user_image=64,
# #                user_score=1000, user_coin=1000))
# gameSession.add_gamer(
#     GamerModel("NHD6bL", username="windows", user_image=60,
#                user_score=1000, user_coin=1000))
# gameSession.add_gamer(
#     GamerModel("kFIrrF", username="mobile", user_image=62,
#                user_score=1000, user_coin=1000))
# gameSession.start_game_timer()
#
# games = {current_game_id: gameSession}
# game_idies = [current_game_id]
# socketid_gameid_pairs = {}

games = {}
game_idies = []
socketid_gameid_pairs = {}


def add_new_game(game_id, queuers, game_types, game_score_type):
    game_play = BaseGamePlayClass(game_id, queuers, game_types, game_score_type)
    game_play.start_game_timer()
    games[game_id] = game_play
    game_idies.append(game_id)


def finish_single_game(game_id, user_id):
    games[game_id].finish_current_game(user_id)


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
            if games[user_game_id].is_user_id_valid(user_id):
                await self.enter_room(socket_id, user_game_id, namespace="/game")
                games[user_game_id].join_gamer(user_id, socket_id)
                socketid_gameid_pairs[socket_id] = user_game_id
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
