from Commons.static_functions import safe_run_async
from Commons import commands
from Commons.static_functions import make_command_json
from Models.Chat_User import ChatUserModel


class ChatSession:
    def __init__(self):
        self.users: list[ChatUserModel] = []

    def find_user_from_user_id(self, user_id):
        for queuer in self.users:
            if queuer.user_id == user_id:
                return queuer
        return None

    def find_user_from_socket_id(self, socket_id):
        for queuer in self.users:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    async def command_received(self, data, socket_id):
        if not isinstance(data, dict) or 'id' not in data:
            return
        gamer_data = self.find_user_from_socket_id(socket_id)
        if gamer_data is None:
            return
        if data['id'] == commands.Message:
            content = str(data.get('content') or '').strip()[:500]
            if not content:
                return
            from Entities.SocketIOManagerClass import send_global_command
            send_data = {'name': gamer_data.username, 'content': content, 'id': gamer_data.user_id}
            await send_global_command(
                command=make_command_json(id=commands.Message, data=send_data), namespace='/chat')

    def join_user(self, user_data: ChatUserModel):
        from Entities.SocketIOManagerClass import send_global_command
        import asyncio
        self.users.append(user_data)
        safe_run_async(
            send_global_command(command=make_command_json(id=commands.Users_Count, data=len(self.users)),
                                namespace='/chat'))

    async def disconnect_user(self, socket_id):
        from Entities.SocketIOManagerClass import send_global_command
        import asyncio
        for user_data in self.users:
            if socket_id == user_data.socket_id:
                self.users.remove(user_data)
                safe_run_async(
                    send_global_command(command=make_command_json(id=commands.Users_Count, data=len(self.users)),
                                        namespace='/chat'))
                break
