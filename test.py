import random
import string

import pymongo


def user_json(name, email, phone, score=0) -> dict:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, 6))
    return {'_id': result, 'phone': phone, 'username': name, "email": email, "score": score}


class DataBaseManager:
    def __init__(self):
        self.db_client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.base_db = self.db_client["KafehFekrDB"]
        self.user_col = self.base_db['users']

    def create_user(self, phone, name, email=""):
        query = {'phone': phone}
        if self.user_col.find_one(query) is None:
            self.user_col.insert_one(user_json(phone=phone, name=name, email=email))
            return True
        else:
            print("bad number")
            return False

    def read_user(self, user_id):
        query = {'_id': user_id}
        user_Data = self.user_col.find_one(query)
        return user_Data

    def update_user(self, user_id):
        query = {'_id': user_id}
        self.user_col.find_one_and_update(query, {'$set': {"score": 15}})

    def delete_user(self, user_id):
        query = {'_id': user_id}
        self.user_col.delete_one(query)


database = DataBaseManager()
# database.create_user("989121234567","Erfan")
# print(database.read_user("JzX935"))
# database.update_user("JzX935")
# database.delete_user("JzX935")


# myclient = pymongo.MongoClient("mongodb://localhost:27017/")
# base_db = myclient["KafehFekrDB"]
# user_col = base_db['users']

# query = {'phone': '989128791034'}
# if user_col.find_one(query) is None:
#     user_col.insert_one(user_json(phone="989128791034", name="erfan3", email="erfanhayatbakhsh3@gmail.com"))
# else:
#     print("bad number")

# for data in user_col.find({}, {'_id': 0, "username": 1}):
#     print(data)

# query = {'_id': '989377804649'}
# print(user_col.find_one(query))
# query = {'score': {"$gt": 3}}
# for raw_data in user_col.find(query):
#     print(raw_data)

# query = {'_id': "989128791034"}
# print(user_col.find_one_and_update(query, {'$set': {"score": 15}}))
# user_col.update_one(query, {'$set': {"score": 12}})

# query = {'_id': "989128791034"}
# user_col.delete_one(query)

# for raw_data in user_col.find().sort([('score', pymongo.DESCENDING)]).limit(2):
#     print(raw_data)

# user_col.drop()
