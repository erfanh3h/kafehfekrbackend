from datetime import datetime


def create_game_history_json(game_id, user1_id, user2_id, game_type, game_score_type) -> dict:
    return {'_id': game_id, 'user1_id': user1_id, 'user2_id': user2_id, "game_type": game_type,
            "game_score_type": game_score_type, "is_finished": False, "start_date": datetime.now(), }


class GameHistoryCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def create_game_history(self, game_id, user1_id, user2_id, game_type, game_score_type):
        game_data = create_game_history_json(game_id, user1_id, user2_id, game_type, game_score_type)
        self.collection.insert_one(game_data)
        return game_data

    def read_game_history(self, game_id):
        query = {'_id': game_id}
        game_Data = self.collection.find_one(query)
        return game_Data

    def update_game_history(self, game_id, winner_id):
        query = {'_id': game_id}
        update_data = {"finish_data": datetime.now(), "is_finished": True, "winner_id": winner_id}
        self.collection.find_one_and_update(query, {'$set': update_data})

    def delete_game_history(self, game_id):
        query = {'_id': game_id}
        self.collection.delete_one(query)
