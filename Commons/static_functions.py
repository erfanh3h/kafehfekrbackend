import string, random

from Entities.Games.game_difficulty import GameDifficultyEnum
from Entities.Games.game_types import GameTypesEnum


def make_command_json(id, data=None):
    return {'id': id, 'data': data}


def create_random_name() -> str:
    char_set = string.ascii_uppercase + string.digits
    random_name = ''.join(random.sample(char_set * 6, 6))
    return random_name


def create_random_game_id(length=7) -> str:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, length))
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
    if game_type == GameTypesEnum.DOTBOX.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.LUDO.value:
        return GameDifficultyEnum.Easy
    if game_type == GameTypesEnum.FEKRBEKR.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.PENTAGO.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.MSweeper.value:
        return GameDifficultyEnum.Normal
    if game_type == GameTypesEnum.MNUMBERS.value:
        return GameDifficultyEnum.Easy
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
    if game_type == GameTypesEnum.YINSH.value:
        return GameDifficultyEnum.Hard
    if game_type == GameTypesEnum.MILL.value:
        return GameDifficultyEnum.Hard


main_loop = None


def set_main_loop(loop):
    global main_loop
    main_loop = loop


def get_main_loop():
    global main_loop
    return main_loop


def safe_run_async(coro):
    import asyncio
    global main_loop
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        if main_loop is not None and main_loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, main_loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
