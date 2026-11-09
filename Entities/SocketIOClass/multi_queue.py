import socketio
from Commons import static_functions
from Controllers.QueueSession.multi_rank import MultiRankQueueSession
from Entities.Security import check_is_token_valid
from Models.Queuer import QueuerModel
from Commons import commands

multi_rank_queue_session = MultiRankQueueSession()
multi_rank_queue_session.init_session()


class MultiQueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if not isinstance(auth, dict):
            await self.disconnect(socket_id, namespace="/multi-queue")
            return
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.emit('command', {'id': commands.Logout}, to=socket_id, namespace="/multi-queue")
            await self.disconnect(socket_id, namespace="/multi-queue")
            return
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
        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        if not user_data:
            await self.disconnect(socket_id, namespace="/multi-queue")
            return
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
