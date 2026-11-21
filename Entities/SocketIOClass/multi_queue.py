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
        from Commons.static_functions import is_user_banned, is_version_allowed
        is_bot = bool(token_data.get('is_bot')) or str(user_id).startswith("bot_")
        user_data = None
        if not is_bot:
            user_data = game_database.users_manager.read_user(user_id)
            if not user_data or is_user_banned(user_data):
                await self.emit('command', {'id': commands.Logout, 'data': {'reason': 'banned', 'message': 'حساب کاربری شما توسط مدیریت مسدود شده است.'}}, to=socket_id, namespace="/multi-queue")
                await self.disconnect(socket_id, namespace="/multi-queue")
                return

            client_ver = str(auth.get("version", "")).strip() if isinstance(auth, dict) else ""
            if client_ver:
                config_data = game_database.config_manager.read_config() or {}
                allowed_ver = str(config_data.get("allowed_version", "")).strip()
                if allowed_ver and not is_version_allowed(client_ver, allowed_ver):
                    await self.emit('command', {'id': commands.Logout, 'data': {'reason': 'force_update', 'message': f'نسخه بازی شما ({client_ver}) قدیمی است. حداقل نسخه مجاز {allowed_ver} می‌باشد.'}}, to=socket_id, namespace="/multi-queue")
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
