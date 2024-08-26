import random
import string


def user_json(name, email, phone, score=0) -> dict:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, 6))
    return {'_id': result, 'phone': phone, 'username': name, "email": email, "score": score}


class UsersCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def create_user(self, phone, name, email=""):
        query = {'phone': phone}
        if self.collection.find_one(query) is None:
            self.collection.insert_one(user_json(phone=phone, name=name, email=email))
            return True
        else:
            print("bad number")
            return False

    def read_user(self, user_id):
        query = {'_id': user_id}
        user_Data = self.collection.find_one(query)
        return user_Data

    def update_user(self, user_id):
        query = {'_id': user_id}
        self.collection.find_one_and_update(query, {'$set': {"score": 15}})

    def delete_user(self, user_id):
        query = {'_id': user_id}
        self.user_col.delete_one(query)
