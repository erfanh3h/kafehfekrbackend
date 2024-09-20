import string, random

from Entities.Games.game_difficulty import GameDifficultyEnum
from Entities.Games.game_types import GameTypesEnum


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


def gametype_to_difficulty(game_type):
    if game_type == GameTypesEnum.TIC_TAC_TOE.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.RPC.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.TEN.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.DOTBOX.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.FEKRBEKR.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.PENTAGO.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.MSweeper.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.MNUMBERS.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.BATTLESHIP.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.FOURINROW.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.BOXFOUR.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.SUDOKU.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.YATZY.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.CHESS.value:
        return GameDifficultyEnum.Hard
    if game_type == GameTypesEnum.CHECKERS.value:
        return GameDifficultyEnum.Hard
    if game_type == GameTypesEnum.OTHELLO.value:
        return GameDifficultyEnum.Hard
    if game_type == GameTypesEnum.BACKGAMMON.value:
        return GameDifficultyEnum.Hard
    if game_type == GameTypesEnum.MILL.value:
        return GameDifficultyEnum.Hard



