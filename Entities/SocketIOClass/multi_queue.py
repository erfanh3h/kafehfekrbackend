import socketio
from Commons import static_functions, commands
from Controllers.QueueSession.multi_rank import MultiRankQueueSession
from Entities.SocketIOClass._auth_guard import authenticate_namespace_user
from Models.Queuer import QueuerModel

multi_rank_queue_session = MultiRankQueueSession()
multi_rank_queue_session.init_session()


class MultiQueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        auth_res = await authenticate_namespace_user(
            self,
            socket_id,
            auth,
            "/multi-queue",
            require_dict_auth=True,
            check_maintenance=True,
            check_version=True,
            check_queue=True,
        )
        if auth_res is None:
            return
        token_data, user_data, _is_bot = auth_res
        user_id = token_data['id']
        raw_game_type = auth.get('game_type')
        if raw_game_type is None:
            await self.disconnect(socket_id, namespace="/multi-queue")
            return
        game_type = multi_rank_queue_session.normalize_game_type(raw_game_type)
        if not multi_rank_queue_session.can_user_join_queue(user_id, socket_id):
            print(f"[MultiQueue] Duplicate queue join rejected for user {user_id} (socket {socket_id})")
            await self.disconnect(socket_id, namespace="/multi-queue")
            return
        if not user_data:
            user_data = {"username": "Gamer", "image": 1, "coin": 1000, "score": 1000, "profile_frame": 1}
        await self.enter_room(socket_id, socket_id, namespace="/multi-queue")
        queuer_data = QueuerModel(
            user_id,
            user_data["username"],
            socket_id=socket_id,
            user_image=user_data['image'],
            user_coin=user_data['coin'],
            user_score=user_data['score'],
        )
        if not multi_rank_queue_session.join_user(queuer_data, game_type):
            await self.leave_room(socket_id, socket_id, namespace="/multi-queue")
            await self.disconnect(socket_id, namespace="/multi-queue")
            return

    async def on_disconnect(self, socket_id):
        await multi_rank_queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        await multi_rank_queue_session.command_received(data, socket_id)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
