import string, random


def make_command_json(id, data=None):
    return {'id': id, 'data': data}


def create_random_name() -> str:
    char_set = string.ascii_uppercase + string.digits
    random_name = ''.join(random.sample(char_set * 6, 6))
    return random_name


def create_random_game_id() -> str:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, 7))
    return result


def create_random_user_id() -> str:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, 6))
    return result


async def get_current_user(token: str):
    from Entities import Security
    user_token_data = await Security.extract_token(token)
    if user_token_data is not None:
        from Entities.Database import game_database
        user = game_database.users_manager.read_user(user_token_data['id'])
        return user
    else:
        return None
