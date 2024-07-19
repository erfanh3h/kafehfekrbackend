import string, random


def make_command_json(id, data=None):
    return {'id': id, 'data': data}


def create_random_name() -> str:
    char_set = string.ascii_uppercase + string.digits
    random_name = ''.join(random.sample(char_set * 6, 6))
    return random_name
