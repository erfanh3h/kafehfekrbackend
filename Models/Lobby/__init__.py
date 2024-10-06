from Models.Queuer import QueuerModel


class LobbyModel:
    def __init__(self, lobby_id: str, creator_id: str, game_types, lobby_name, lobby_password=""):
        self.lobby_id: str = lobby_id
        self.lobby_name: str = lobby_name
        self.lobby_password: str = lobby_password
        self.creator_id: str = creator_id
        self.game_types = game_types
        self.queuers: list[QueuerModel] = []

    def find_free_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def add_queuer(self, queuer: QueuerModel):
        self.queuers.append(queuer)

    def remove_queuer(self, user_id):
        queuer = self.find_free_gamer_from_user_id(user_id)
        if queuer is not None:
            self.queuers.remove(queuer)

    def to_json(self):
        data = {'lobby_id': self.lobby_id, 'lobby_name': self.lobby_name, 'creator_id': self.creator_id,
                'game_types': self.game_types, 'queuers_length': len(self.queuers)}
        return data

    def to_complete_json(self):
        data = {'lobby_id': self.lobby_id, 'lobby_name': self.lobby_name, 'creator_id': self.creator_id,
                'game_types': self.game_types, }
        queuer_data = []
        for queuer in self.queuers:
            queuer_data.append(queuer.to_lobby_json())
        data['queuers'] = queuer_data
        return data
