import pymongo

from Entities.Database.users_collection import UsersCollectionManager


class DataBaseManager:
    def __init__(self):
        self.db_client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.base_db = self.db_client["KafehFekrDB"]
        self.users_manager = UsersCollectionManager(self.base_db['users'])


game_databasae = DataBaseManager()
# print(game_databasae.users_manager.create_user("1221234567", "Erfan"))
# game_databasae.users_manager.update_user("K2dWiy", xp=120, score=100)
