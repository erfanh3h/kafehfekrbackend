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
        user_id = user_token_data.get('id')
        is_bot = bool(user_token_data.get('is_bot')) or str(user_id).startswith("bot_")
        if is_bot:
            return {"_id": user_id, "id": user_id, "username": "Bot", "is_active": True, "is_banned": False}
        from Entities.Database import game_database
        user = game_database.users_manager.read_user(user_id)
        if check_ban_and_auto_unban(user, game_database.users_manager):
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

    hard_types = (GameTypesEnum.CHESS, GameTypesEnum.CHECKERS, GameTypesEnum.OTHELLO, GameTypesEnum.BACKGAMMON, GameTypesEnum.YINSH, GameTypesEnum.MILL, GameTypesEnum.RISK, GameTypesEnum.QUORIDOR)
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


def _parse_utc_datetime(val):
    """Parses a datetime or ISO string into a timezone-aware UTC datetime, or None."""
    from datetime import datetime, timezone
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def is_ban_expired(user_data: dict | None) -> bool:
    """Returns True if the user has a temporary ban whose ban_until timestamp is in the past."""
    if not user_data or not isinstance(user_data, dict):
        return False
    ban_until = _parse_utc_datetime(user_data.get("ban_until"))
    if ban_until is None:
        return False
    from datetime import datetime, timezone
    return datetime.now(timezone.utc) >= ban_until


def is_user_banned(user_data: dict | None) -> bool:
    """Returns True if the user account is inactive or banned (respecting temporary ban_until expiry)."""
    if not user_data or not isinstance(user_data, dict):
        return False
    if str(user_data.get("_id", "")).startswith("bot_") or user_data.get("is_bot") is True:
        return False
    flagged = (user_data.get("is_active") is False) or (user_data.get("is_banned") is True)
    if not flagged:
        return False
    if is_ban_expired(user_data):
        return False
    return True


def check_ban_and_auto_unban(user_data: dict | None, users_manager=None) -> bool:
    """Checks ban status and auto-clears expired temporary bans in MongoDB when encountered."""
    if not user_data or not isinstance(user_data, dict):
        return False
    if str(user_data.get("_id", "")).startswith("bot_") or user_data.get("is_bot") is True:
        return False
    flagged = (user_data.get("is_active") is False) or (user_data.get("is_banned") is True)
    if not flagged:
        return False
    if is_ban_expired(user_data):
        uid = user_data.get("_id")
        if uid and users_manager is not None and hasattr(users_manager, "collection"):
            try:
                users_manager.collection.update_one(
                    {"_id": uid},
                    {
                        "$set": {"is_active": True, "is_banned": False},
                        "$unset": {"ban_until": "", "ban_reason": "", "banned_at": ""},
                    },
                )
            except Exception as e:
                print(f"[auto_unban] Failed to clear expired ban for {uid}: {e}")
        user_data["is_active"] = True
        user_data["is_banned"] = False
        user_data.pop("ban_until", None)
        return False
    return True


def get_maintenance_block(config_data: dict | None) -> str | None:
    """Returns maintenance message if maintenance mode is active, otherwise None."""
    if not isinstance(config_data, dict):
        return None
    if bool(config_data.get("maintenance_mode", False)):
        msg = str(config_data.get("maintenance_message") or "").strip()
        return msg or "سرور در حال به‌روزرسانی و تعمیرات است. لطفاً دقایقی دیگر تلاش کنید."
    return None


def is_queue_closed(config_data: dict | None) -> bool:
    """Returns True if matchmaking queue is explicitly closed in system config."""
    if not isinstance(config_data, dict):
        return False
    return config_data.get("is_queue_open") is False


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
