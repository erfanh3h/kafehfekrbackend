import asyncio
import socketio
from Commons import static_functions
from Controllers.QueueSession.rank import RankQueueSession
from Entities.Security import check_is_token_valid
from Models.Queuer import QueuerModel
from Commons import commands

rank_queue_session = RankQueueSession()
rank_queue_session.init_session()


class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if not isinstance(auth, dict):
            await self.disconnect(socket_id, namespace="/queue")
            return
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.emit("command", {"id": commands.Logout}, to=socket_id, namespace="/queue")
            await self.disconnect(socket_id, namespace="/queue")
            return
        user_id = token_data["id"]
        pre_game_id = auth.get("pre_game_id")

        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id)
        if user_data is None:
            await self.disconnect(socket_id, namespace="/queue")
            return

        queuer_data = QueuerModel(
            user_id,
            user_data.get("username", "Gamer"),
            socket_id=socket_id,
            user_image=user_data.get("image", 1),
            user_coin=user_data.get("coin", 1000),
            user_score=user_data.get("score", 1000),
        )

        # Determine if user is attempting to reconnect to an active pre-game
        target_pre_game_id = pre_game_id
        if not target_pre_game_id:
            open_pre_id = user_data.get("open_pre_game_id", "") if isinstance(user_data, dict) else ""
            if open_pre_id and open_pre_id in rank_queue_session.active_pre_games:
                target_pre_game_id = open_pre_id
            elif open_pre_id:
                game_database.users_manager.update_user(user_id, open_pre_game_id="")

        if target_pre_game_id:
            if target_pre_game_id not in rank_queue_session.active_pre_games:
                game_database.users_manager.update_user(user_id, open_pre_game_id="")
                await self.emit("command", {"id": commands.Game_Finished, "data": {}}, to=socket_id, namespace="/queue")
                await self.disconnect(socket_id, namespace="/queue")
                return
            if not rank_queue_session.can_user_reconnect_pre_game(target_pre_game_id, user_id, socket_id):
                print(f"[Queue] Duplicate pre-game connection rejected for user {user_id} (socket {socket_id}) in {target_pre_game_id}")
                await self.disconnect(socket_id, namespace="/queue")
                return
            await self.enter_room(socket_id, socket_id, namespace="/queue")

            async def _delayed_pre_game_reconn():
                await asyncio.sleep(0.05)
                rank_queue_session.reconnect_queuer(target_pre_game_id, queuer_data)

            asyncio.create_task(_delayed_pre_game_reconn())
            return

        # Clear stale open_game_id if that game is no longer in memory
        open_game_id = user_data.get("open_game_id", "") if isinstance(user_data, dict) else ""
        if open_game_id:
            from Entities.SocketIOClass.game import games
            if open_game_id not in games or getattr(games[open_game_id], "is_game_finished", False) or getattr(games[open_game_id], "is_game_terminated", False):
                game_database.users_manager.update_user(user_id, open_game_id="")
                open_game_id = ""
            else:
                print(f"[Queue] User {user_id} has active ongoing game ({open_game_id}). Rejecting /queue join.")
                await self.disconnect(socket_id, namespace="/queue")
                return

        # Reject queue join if player does not meet the minimum XP threshold (Level 3 / 160 XP)
        MIN_RANKED_XP = 160
        user_xp = int(user_data.get("xp", 0))
        if user_xp < MIN_RANKED_XP:
            print(f"[Queue] User {user_id} does not have required XP ({user_xp} < {MIN_RANKED_XP}). Rejecting /queue join.")
            await self.emit("command", {
                "id": getattr(commands, "Rank_Locked", "RankLocked"),
                "data": {
                    "min_xp": MIN_RANKED_XP,
                    "min_level": 3,
                    "current_xp": user_xp,
                    "message": "برای شرکت در مسابقات رده‌بندی باید حداقل به سطح ۳ (۱۶۰ XP) برسید."
                }
            }, to=socket_id, namespace="/queue")
            await self.disconnect(socket_id, namespace="/queue")
            return

        if not rank_queue_session.can_user_join_queue(user_id, socket_id):
            print(f"[Queue] Duplicate queue join rejected for user {user_id} (socket {socket_id})")
            await self.disconnect(socket_id, namespace="/queue")
            return

        await self.enter_room(socket_id, socket_id, namespace="/queue")
        rank_queue_session.join_queuer(queuer_data)

    async def on_disconnect(self, socket_id):
        await rank_queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print("User Sent command ", data)
        await rank_queue_session.command_received(data, socket_id)


def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
