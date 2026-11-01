import socketio

from Commons import static_functions
from Controllers.QueueSession.rank import RankQueueSession
from Models.Queuer import QueuerModel
from Commons import commands

rank_queue_session = RankQueueSession()
rank_queue_session.init_session()


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if auth is not None:
            try:
                from Entities.Security import extract_token
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                    pre_game_id = auth.get('pre_game_id')
                    await self.enter_room(socket_id, socket_id, namespace="/queue")
                else:
                    await self.disconnect(socket_id, namespace="/queue")
                    return
            except Exception:
                await self.disconnect(socket_id, namespace="/queue")
                return
        else:
            await self.disconnect(socket_id, namespace="/queue")
            return
        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        if user_data is None:
            user_data = {
                "username": token_data.get("username", "Gamer"),
                "image": token_data.get("user_image", 1),
                "coin": 1000,
                "score": token_data.get("user_score", 1000),
            }
        queuer_data = QueuerModel(user_id, user_data.get("username", "Gamer"), socket_id=socket_id,
                                  user_image=user_data.get('image', 1), user_coin=user_data.get('coin', 1000),
                                  user_score=user_data.get('score', 1000))
        if pre_game_id is None:
            open_pre_id = user_data.get('open_pre_game_id', '') if isinstance(user_data, dict) else ''
            if open_pre_id and open_pre_id in rank_queue_session.active_pre_games:
                rank_queue_session.reconnect_queuer(open_pre_id, queuer_data)
            else:
                # Do NOT auto-join matchmaking queue if user already has an active ongoing game!
                open_game_id = user_data.get('open_game_id', '') if isinstance(user_data, dict) else ''
                if not open_game_id:
                    rank_queue_session.join_queuer(queuer_data)
                else:
                    print(f"[Queue] User {user_id} has active ongoing game ({open_game_id}). Ignoring /queue auto-join.")
        else:
            rank_queue_session.reconnect_queuer(pre_game_id, queuer_data)

    async def on_disconnect(self, socket_id):
        await rank_queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sent command ', data)
        await rank_queue_session.command_received(data, socket_id)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
