import socketio

from Commons import static_functions
from Controllers.QueueSession import BaseQueueSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

normal_queue_session = BaseQueueSession(GameScoreTypesEnum.NORMAL)
normal_queue_session.init_session()

# rank_queue_session = BaseQueueSession(GameScoreTypesEnum.RANK)
# rank_queue_session.init_session()
game_types = [game.value for game in GameTypesEnum]
normal_socketid_game_type_pairs: dict[str, str] = {}


# rank_socketid_game_type_pairs: dict[str, str] = {}


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        print('connect ', socket_id)
        if auth is not None:
            try:
                from Entities.Security import extract_token
                # user_id = auth['user_id']
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                    if auth['game_type'] in game_types:
                        game_type = auth['game_type']
                        game_score_type = "Normal"
                    else:
                        game_type = None
                        game_score_type = "Normal"
                else:
                    await self.disconnect(socket_id, namespace="/queue")
                    return
            except:
                await self.disconnect(socket_id, namespace="/queue")
                return
        else:
            await self.disconnect(socket_id, namespace="/queue")
            return
        if game_type is None:
            await self.disconnect(socket_id, namespace="/queue")
        else:
            from Entities.Database import game_database
            user_data = game_database.users_manager.read_user(user_id)
            queuer_data = QueuerModel(user_id, user_data["username"], socket_id=socket_id,
                                      user_image=user_data['image'])
            if game_score_type == "Normal":
                normal_queue_session.join_queuer(queuer_data, game_type)
                normal_socketid_game_type_pairs[socket_id] = game_type

    async def on_disconnect(self, socket_id):
        game_type = return_game_type_from_socketid(socket_id)
        if game_type is not None:
            normal_queue_session.disconnect_user(socket_id, game_type)
            del normal_socketid_game_type_pairs[socket_id]
        print('disconnect ', socket_id)

    async def on_user_command(self, socket_id, data):
        # game_id = return_gameid_from_socketid(socket_id)
        # if game_id is not None:
        #     await games[game_id].command_received(data, socket_id)
        #     print('User Sended command ', data)
        print('User Sended command ', data)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id


def return_game_type_from_socketid(socket_id):
    for raw_socket_id in normal_socketid_game_type_pairs.keys():
        if raw_socket_id == socket_id:
            return normal_socketid_game_type_pairs[raw_socket_id]
    return None
