from Models.Queuer import QueuerModel


class LobbyModel:
    def __init__(self, lobby_id: str, creator_id: str, game_type, lobby_name, lobby_count, lobby_password=""):
        self.lobby_id: str = lobby_id
        self.lobby_name: str = lobby_name
        self.lobby_password: str = lobby_password
        self.creator_id: str = creator_id
        self.game_type = game_type
        self.queuers: list[QueuerModel] = []
        self.lobby_count = lobby_count

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
                'game_type': self.game_type, 'queuers_length': len(self.queuers), 'lobby_count': self.lobby_count}
        return data

    def to_complete_json(self):
        data = {'lobby_id': self.lobby_id, 'lobby_name': self.lobby_name, 'creator_id': self.creator_id,
                'game_type': self.game_type, 'lobby_count': self.lobby_count, 'queuers_length': len(self.queuers), }
        queuer_data = []
        for queuer in self.queuers:
            queuer_data.append(queuer.to_lobby_json())
        data['queuers'] = queuer_data
        return data
