import socketio
from Commons import commands
from Commons.static_functions import is_user_banned
from Controllers.SocialSession import social_session
from Entities.Database import game_database
from Entities.Security import check_is_token_valid


class SocialSocketNameSpace(socketio.AsyncNamespace):
    """Socket.IO /social namespace for presence, DMs, clan chat, notifications, and invitations."""

    async def on_connect(self, socket_id, environ, auth):
        token_data = await check_is_token_valid(auth)
        if not token_data:
            await self.emit("command", {"id": commands.Logout}, to=socket_id, namespace="/social")
            await self.disconnect(socket_id, namespace="/social")
            return
        user_id = str(token_data["id"])
        user_data = game_database.users_manager.read_user(user_id)
        if not user_data or is_user_banned(user_data):
            await self.emit("command", {"id": commands.Logout, "data": {"reason": "banned", "message": "حساب کاربری شما توسط مدیریت مسدود شده است."}}, to=socket_id, namespace="/social")
            await self.disconnect(socket_id, namespace="/social")
            return
        await social_session.connect_user(socket_id, user_data, self)

    async def on_disconnect(self, socket_id):
        await social_session.disconnect_user(socket_id, self)

    async def on_user_command(self, socket_id, data):
        await social_session.handle_command(socket_id, data, self)
