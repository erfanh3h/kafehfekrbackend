import asyncio

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Lobby import LobbyModel
from Models.Queuer import QueuerModel


class LobbySession:
    def __init__(self):
        self.game_score_type = GameScoreTypesEnum.LOBBY
        self.lobbies: list[LobbyModel] = []
        self.free_queuers: list[QueuerModel] = []
        self.socketid_lobbyid_pairs = {}

    def get_lobbies_data(self):
        lobbies_data = []
        for lobby in self.lobbies:
            lobbies_data.append(lobby.to_json())
        return lobbies_data

    def get_lobby_data(self, lobby_id):
        for lobby in self.lobbies:
            if lobby.lobby_id == lobby_id:
                return lobby.to_complete_json()
        return {}

    def find_lobby_from_id(self, lobby_id):
        for lobby in self.lobbies:
            if lobby.lobby_id == lobby_id:
                return lobby
        return None

    def find_gamer_from_user_id(self, lobby_id, user_id):
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return None
        for queuer in lobby.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def find_free_gamer_from_user_id(self, user_id):
        for queuer in self.free_queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def find_free_gamer_from_socket_id(self, socket_id):
        for queuer in self.free_queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def find_gamer_from_socket_id(self, lobby_id, socket_id):
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return None
        for queuer in lobby.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def find_lobbyid_from_socketid(self, socket_id):
        for raw_socket_id in self.socketid_lobbyid_pairs.keys():
            if raw_socket_id == socket_id:
                return self.socketid_lobbyid_pairs[raw_socket_id]
        return None

    async def start_new_game(self, lobby_id):
        lobby_data = self.find_lobby_from_id(lobby_id)
        if lobby_data is None:
            return
        queuers_idis = [lobby_data.queuers[0].user_id, lobby_data.queuers[0].user_id]
        queuers = [lobby_data.queuers[0], lobby_data.queuers[1]]
        from Entities.SocketIOManagerClass import send_lobby_command
        game_id = static_functions.create_random_game_id()
        # mix_game_type = []
        # mix_game_type.extend(queuers[0].game_types)
        # mix_game_type.extend(queuers[1].game_types)
        final_game_types = [lobby_data.game_type]
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        await send_lobby_command(command=make_command_json(id=commands.Start_Game, data=game_data), lobby_id=lobby_id)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)
        await self.delete_lobby(lobby_id, ignores_id=queuers_idis, need_send_message=False)

    async def create_lobby(self, user_id, game_type, lobby_name, lobby_password, lobby_count):
        user_data = self.find_free_gamer_from_user_id(user_id)
        if user_data is None:
            return
        lobby_id = static_functions.create_random_game_id(length=6)
        new_lobby = LobbyModel(lobby_id=lobby_id, creator_id=user_data.user_id, game_type=game_type,
                               lobby_name=lobby_name, lobby_count=lobby_count, lobby_password=lobby_password)
        self.lobbies.append(new_lobby)
        from Entities.SocketIOManagerClass import send_global_lobby_command, send_private_lobby_command
        await send_global_lobby_command(command=make_command_json(id=commands.Lobby_Created, data=new_lobby.to_json()))
        await send_private_lobby_command(
            command=make_command_json(id=commands.Your_Lobby_Created, data={'lobby_id': lobby_id}),
            socket_id=user_data.socket_id)
        await self.join_lobby(user_data, lobby_id)

    async def join_queuers_list(self, user_data: QueuerModel):
        self.free_queuers.append(user_data)
        from Entities.SocketIOManagerClass import send_private_lobby_command
        await send_private_lobby_command(
            command=make_command_json(id=commands.Lobby_List, data=self.get_lobbies_data()),
            socket_id=user_data.socket_id)

    async def join_lobby(self, user_data: QueuerModel, lobby_id):
        self.socketid_lobbyid_pairs[user_data.socket_id] = lobby_id
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return
        lobby.add_queuer(user_data)
        from Entities.SocketIOManagerClass import send_lobby_command, enter_lobby
        await enter_lobby(socket_id=user_data.socket_id, lobby_id=lobby_id)
        await send_lobby_command(command=make_command_json(id=commands.Lobby_Data, data=self.get_lobby_data(lobby_id)),
                                 lobby_id=lobby_id)
        self.free_queuers.remove(user_data)

    async def command_received(self, data, socket_id):
        print(data)
        gamer_data = self.find_free_gamer_from_socket_id(socket_id)
        if gamer_data is None:
            lobby_id = self.find_lobbyid_from_socketid(socket_id)
            if lobby_id is None:
                return
            gamer_data = self.find_gamer_from_socket_id(lobby_id, socket_id)
            if gamer_data is None:
                return
        user_id = gamer_data.user_id
        if data['id'] == commands.Lobby_Create:
            lobby_data = data['data']
            lobby_name = lobby_data['lobby_name']
            lobby_count = lobby_data.get('lobby_count', 2)
            # lobby_password = lobby_data['lobby_password']
            lobby_password = ""
            game_type = lobby_data.get('game_type', None)
            if game_type is None:
                return
            if lobby_count != 2 and GameTypesEnum.is_in_two_players(
                    game_type):  # prevent more then 2 players for unmultiGames
                lobby_count = 2
            await self.create_lobby(user_id, game_type, lobby_name, lobby_password, lobby_count)
        if data['id'] == commands.Lobby_Request_Data:
            from Entities.SocketIOManagerClass import send_private_lobby_command
            await send_private_lobby_command(
                command=make_command_json(id=commands.Lobby_List, data=self.get_lobbies_data()),
                socket_id=gamer_data.socket_id)
        if data['id'] == commands.Lobby_Player_Ready:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            user_data = self.find_gamer_from_user_id(lobby_id, user_id)
            if user_data is None:
                return
            user_data.is_rdy = True
            from Entities.SocketIOManagerClass import send_lobby_command
            await send_lobby_command(
                command=make_command_json(id=commands.Lobby_Player_Ready, data={'user_id': user_data.user_id}),
                lobby_id=lobby_id)
        if data['id'] == commands.Lobby_Join:
            lobby_id = data['data']['lobby_id']
            lobby_data = self.find_lobby_from_id(lobby_id)
            from Entities.SocketIOManagerClass import send_private_lobby_command
            if lobby_data is None:
                await send_private_lobby_command(
                    command=make_command_json(id=commands.Lobby_Not_Exists, data={'lobby_id': lobby_id}),
                    socket_id=socket_id)
                return
            if len(lobby_data.queuers) < 2:
                await self.join_lobby(gamer_data, lobby_id)
            else:
                await send_private_lobby_command(
                    command=make_command_json(id=commands.Lobby_Full, data={}), socket_id=socket_id)
        if data['id'] == commands.Lobby_Start_Game:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby_data = self.find_lobby_from_id(lobby_id)
            if lobby_data is None or lobby_data.creator_id != user_id or len(
                    lobby_data.queuers) != lobby_data.lobby_count:
                return
            await self.start_new_game(lobby_id)
        if data['id'] == commands.Lobby_Delete:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby_data = self.find_lobby_from_id(lobby_id)
            if lobby_data is None or lobby_data.creator_id != user_id:
                return
            await self.delete_lobby(lobby_id)
        if data['id'] == commands.Lobby_Kick:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby_data = self.find_lobby_from_id(lobby_id)
            if lobby_data is None or lobby_data.creator_id != user_id:
                return
            target_user_id = data['data']['user_id']
            if target_user_id == user_id:
                return
            gamer_data = self.find_gamer_from_user_id(lobby_id, target_user_id)
            if gamer_data is None:
                return
            lobby = self.find_lobby_from_id(lobby_id)
            if lobby is None:
                return
            del self.socketid_lobbyid_pairs[gamer_data.socket_id]
            lobby.remove_queuer(gamer_data.user_id)
            gamer_data.is_rdy = False
            self.free_queuers.append(gamer_data)
            from Entities.SocketIOManagerClass import send_private_lobby_command
            await send_private_lobby_command(
                command=make_command_json(id=commands.Lobby_Kick, data=self.get_lobbies_data()),
                socket_id=gamer_data.socket_id)
        if data['id'] == commands.Lobby_Quit:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby = self.find_lobby_from_id(lobby_id)
            if lobby is None:
                return
            from Entities.SocketIOManagerClass import send_private_lobby_command, send_lobby_command, leave_lobby
            del self.socketid_lobbyid_pairs[socket_id]
            lobby.remove_queuer(gamer_data.user_id)
            await leave_lobby(gamer_data.socket_id, lobby_id)
            gamer_data.is_rdy = False
            self.free_queuers.append(gamer_data)
            await send_private_lobby_command(
                command=make_command_json(id=commands.Lobby_List, data=self.get_lobbies_data()),
                socket_id=gamer_data.socket_id)
            await send_lobby_command(
                command=make_command_json(id=commands.Lobby_Data, data=self.get_lobby_data(lobby_id)),
                lobby_id=lobby_id)

    async def reaction_received(self, data, socket_id):
        lobby_id = self.find_lobbyid_from_socketid(socket_id)
        if lobby_id is None:
            return
        gamer_data = self.find_gamer_from_socket_id(lobby_id, socket_id)
        if gamer_data is None:
            return
        gamer_id = gamer_data.user_id
        from Entities.SocketIOManagerClass import send_lobby_reaction
        await send_lobby_reaction(reaction_id=data, player_id=gamer_id, lobby_id=lobby_id)

    async def disconnect_user(self, socket_id):
        lobby_id = self.find_lobbyid_from_socketid(socket_id)
        if lobby_id is not None:
            lobby = self.find_lobby_from_id(lobby_id)
            if lobby is None:
                return
            gamer_data = self.find_gamer_from_socket_id(lobby_id, socket_id)
            if gamer_data is None:
                return
            if lobby.creator_id == gamer_data.user_id:
                await self.delete_lobby(lobby_id, ignores_id=[gamer_data.user_id])
            else:
                del self.socketid_lobbyid_pairs[socket_id]
                lobby.remove_queuer(gamer_data.user_id)
                from Entities.SocketIOManagerClass import send_lobby_command
                await send_lobby_command(
                    command=make_command_json(id=commands.Lobby_Data, data=self.get_lobby_data(lobby_id)),
                    lobby_id=lobby_id)

        else:
            gamer = self.find_free_gamer_from_socket_id(socket_id)
            if gamer is not None:
                self.free_queuers.remove(gamer)

    async def delete_lobby(self, lobby_id, ignores_id=None, need_send_message=True):
        if ignores_id is None:
            ignores_id = []
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return
        from Entities.SocketIOManagerClass import send_lobby_command, leave_lobby, send_private_lobby_command
        self.lobbies.remove(lobby)
        lobbies_data = self.get_lobbies_data()
        if need_send_message:
            await send_lobby_command(command=make_command_json(id=commands.Lobby_Deleted, data={'lobby_id': lobby_id}),
                                     lobby_id=lobby_id)
        for user_data in lobby.queuers:
            await leave_lobby(user_data.socket_id, lobby_id)
            del self.socketid_lobbyid_pairs[user_data.socket_id]
            if ignores_id.__contains__(user_data.user_id):
                continue
            user_data.is_rdy = False
            self.free_queuers.append(user_data)
            await send_private_lobby_command(command=make_command_json(id=commands.Lobby_List, data=lobbies_data),
                                             socket_id=user_data.socket_id)
