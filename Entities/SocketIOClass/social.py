import socketio
from Controllers.SocialSession import social_session
from Entities.SocketIOClass._auth_guard import authenticate_namespace_user


class SocialSocketNameSpace(socketio.AsyncNamespace):
    """Socket.IO /social namespace for presence, DMs, clan chat, notifications, and invitations."""

    async def on_connect(self, socket_id, environ, auth):
        auth_res = await authenticate_namespace_user(
            self,
            socket_id,
            auth,
            "/social",
            require_dict_auth=False,
            disconnect_bot=True,
        )
        if auth_res is None:
            return
        _token_data, user_data, _is_bot = auth_res
        await social_session.connect_user(socket_id, user_data, self)

    async def on_disconnect(self, socket_id):
        await social_session.disconnect_user(socket_id, self)

    async def on_user_command(self, socket_id, data):
        await social_session.handle_command(socket_id, data, self)
