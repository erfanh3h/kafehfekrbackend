import asyncio

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
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

    def start_new_game(self, lobby_id):
        lobby_data = self.find_lobby_from_id(lobby_id)
        if lobby_data is None:
            return
        queuers_idis = [lobby_data.queuers[0].user_id, lobby_data.queuers[0].user_id]
        queuers = []
        from Entities.SocketIOManagerClass import send_queue_command
        for queuer_id in queuers_idis:
            queuer_data = self.find_gamer_from_user_id(queuer_id)
            if queuer_data is None:
                return False
            queuers.append(queuer_data)
        game_id = static_functions.create_random_game_id()
        mix_game_type = []
        mix_game_type.extend(queuers[0].game_types)
        mix_game_type.extend(queuers[1].game_types)
        final_game_types = list(set(mix_game_type))
        # game_id = 'testgame'
        game_data = {'game_id': game_id}
        if len(queuers) == 2:
            for queuer_data in queuers:
                asyncio.new_event_loop().run_until_complete(
                    send_queue_command(command=make_command_json(id=commands.Start_Game, data=game_data),
                                       socket_id=queuer_data.socket_id))
                self.queuers.remove(queuer_data)
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

    async def create_lobby(self, user_id, game_types, lobby_name, lobby_password):
        user_data = self.find_free_gamer_from_user_id(user_id)
        if user_data is None:
            return
        lobby_id = static_functions.create_random_game_id(length=6)
        self.socketid_lobbyid_pairs[lobby_id] = user_data.socket_id
        new_lobby = LobbyModel(lobby_id=lobby_id, creator_id=user_data.user_id, game_types=game_types,
                               lobby_name=lobby_name, lobby_password=lobby_password)
        new_lobby.add_queuer(user_data)
        self.lobbies.append(new_lobby)
        self.free_queuers.remove(user_data)
        from Entities.SocketIOManagerClass import send_global_lobby_command
        await send_global_lobby_command(command=make_command_json(id=commands.Lobby_Created, data=new_lobby.to_json()))

    async def join_queuers_list(self, user_data: QueuerModel):
        self.free_queuers.append(user_data)
        from Entities.SocketIOManagerClass import send_private_lobby_command
        await send_private_lobby_command(
            command=make_command_json(id=commands.Lobby_List, data=self.get_lobbies_data()),
            socket_id=user_data.socket_id)

    def join_lobby(self, user_data: QueuerModel, lobby_id):
        self.socketid_lobbyid_pairs[lobby_id] = user_data.user_id
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return
        lobby.add_queuer(user_data)
        self.free_queuers.remove(user_data)

    async def command_received(self, data, socket_id):
        gamer_data = self.find_free_gamer_from_socket_id(socket_id)
        if gamer_data is None:
            lobby_id = self.find_lobbyid_from_socketid(socket_id)
            if lobby_id is None:
                return
            gamer_data = self.find_gamer_from_socket_id(socket_id, lobby_id)
            if gamer_data is None:
                return
        user_id = gamer_data.user_id
        if data['id'] == commands.Lobby_Create:
            lobby_data = data['data']
            lobby_name = lobby_data['lobby_name']
            lobby_password = lobby_data['lobby_password']
            game_types = lobby_data['game_types']
            await self.create_lobby(user_id, game_types, lobby_name, lobby_password)
        if data['id'] == commands.Lobby_Player_Ready:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            user_data = self.find_gamer_from_user_id(lobby_id, user_id)
            if user_data is None:
                return
            user_data.is_rdy = True
        if data['id'] == commands.Lobby_Join:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            self.join_lobby(gamer_data, lobby_id)
        if data['id'] == commands.Lobby_Start_Game:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby_data = self.find_lobby_from_id(lobby_id)
            if lobby_data is None or lobby_data.creator_id != user_id or len(lobby_data.queuers) != 2:
                return
            self.start_new_game(lobby_id)
        if data['id'] == commands.Lobby_Delete:
            lobby_id = self.socketid_lobbyid_pairs[socket_id]
            lobby_data = self.find_lobby_from_id(lobby_id)
            if lobby_data is None or lobby_data.creator_id != user_id:
                return
            self.delete_lobby(lobby_id)

    async def reaction_received(self, data, socket_id):
        lobby_id = self.find_lobbyid_from_socketid(socket_id)
        if lobby_id is None:
            return
        gamer_data = self.find_gamer_from_socket_id(socket_id, lobby_id)
        if gamer_data is None:
            return
        gamer_id = gamer_data.user_id
        from Entities.SocketIOManagerClass import send_lobby_reaction
        await send_lobby_reaction(reaction_id=data, player_id=gamer_id, lobby_id=lobby_id)

    async def disconnect_user(self, socket_id):
        lobby_id = self.find_lobbyid_from_socketid(socket_id)
        if lobby_id is not None:
            del self.socketid_lobbyid_pairs[lobby_id]
            lobby = self.find_lobby_from_id(lobby_id)
            if lobby is None:
                return
            gamer_data = self.find_gamer_from_socket_id(lobby_id, socket_id)
            if gamer_data is None:
                return
            if lobby.creator_id == gamer_data.user_id:
                try:
                    await self.disconnect_user(lobby.queuers[1].socket_id)
                except:
                    pass
                lobby.remove_queuer(gamer_data.user_id)
                from Entities.SocketIOManagerClass import send_lobby_command
                await send_lobby_command(command=make_command_json(id=commands.Lobby_Deleted, data={}),
                                         lobby_id=lobby_id)
                self.delete_lobby(lobby_id)
            else:
                lobby.remove_queuer(gamer_data.user_id)

        else:
            gamer = self.find_free_gamer_from_user_id(socket_id)
            if gamer is not None:
                self.free_queuers.remove(gamer)

    def delete_lobby(self, lobby_id):
        lobby = self.find_lobby_from_id(lobby_id)
        if lobby is None:
            return
        self.lobbies.remove(lobby)
