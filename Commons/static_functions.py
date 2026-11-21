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
        if is_user_banned(user):
            return None
        return user
    else:
        return None


def gametype_to_difficulty(game_type):
    val = game_type.value if hasattr(game_type, "value") else str(game_type)
    val_norm = val.lower().replace("_", "").replace("-", "")

    easy_types = (GameTypesEnum.TIC_TAC_TOE, GameTypesEnum.RPC, GameTypesEnum.DOTBOX, GameTypesEnum.LUDO, GameTypesEnum.MNUMBERS, GameTypesEnum.UNO)
    for gt in easy_types:
        if val_norm == gt.value.lower().replace("_", "").replace("-", ""):
            return GameDifficultyEnum.Easy

    hard_types = (GameTypesEnum.CHESS, GameTypesEnum.CHECKERS, GameTypesEnum.OTHELLO, GameTypesEnum.BACKGAMMON, GameTypesEnum.YINSH, GameTypesEnum.MILL, GameTypesEnum.QUORIDOR)
    for gt in hard_types:
        if val_norm == gt.value.lower().replace("_", "").replace("-", ""):
            return GameDifficultyEnum.Hard

    return GameDifficultyEnum.Normal


main_loop = None


def parse_version(ver_str: str) -> tuple:
    """Parses a version string like '2.0.1' into a tuple of ints (2, 0, 1)."""
    try:
        parts = []
        for segment in str(ver_str or "").strip().split("."):
            digits = "".join(ch for ch in segment if ch.isdigit())
            parts.append(int(digits) if digits else 0)
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def is_version_allowed(current_ver: str, allowed_ver: str) -> bool:
    """Returns True if current_ver is greater than or equal to allowed_ver."""
    if not allowed_ver or not str(allowed_ver).strip():
        return True
    return parse_version(current_ver) >= parse_version(allowed_ver)


def is_user_banned(user_data: dict | None) -> bool:
    """Returns True if the user account is inactive or flagged as banned."""
    if not user_data or not isinstance(user_data, dict):
        return False
    if user_data.get("is_active") is False:
        return True
    if user_data.get("is_banned") is True:
        return True
    return False


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
