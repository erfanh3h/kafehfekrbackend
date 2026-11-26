"""Shared authentication and gate checks for Socket.IO namespaces."""

from Commons import commands
from Commons.static_functions import (
    check_ban_and_auto_unban,
    get_maintenance_block,
    is_queue_closed,
    is_version_allowed,
)
from Entities.Database import game_database
from Entities.Security import check_is_token_valid


async def authenticate_namespace_user(
    ns,
    socket_id: str,
    auth,
    namespace: str,
    *,
    require_dict_auth: bool = True,
    check_maintenance: bool = False,
    check_version: bool = False,
    check_queue: bool = False,
    allow_pre_game_reconnect: bool = False,
    disconnect_bot: bool = False,
):
    """
    Validates Socket.IO auth token, ban status, maintenance mode, client version, and queue state.
    Returns (token_data, user_data, is_bot) on success, or None after emitting Logout/QueueClosed and disconnecting.
    """
    if require_dict_auth and not isinstance(auth, dict):
        await ns.disconnect(socket_id, namespace=namespace)
        return None

    token_data = await check_is_token_valid(auth)
    if not token_data:
        await ns.emit("command", {"id": commands.Logout}, to=socket_id, namespace=namespace)
        await ns.disconnect(socket_id, namespace=namespace)
        return None

    user_id = token_data["id"]
    is_bot = bool(token_data.get("is_bot")) or str(user_id).startswith("bot_")
    if disconnect_bot and is_bot:
        await ns.disconnect(socket_id, namespace=namespace)
        return None

    user_data = None
    if not is_bot:
        user_data = game_database.users_manager.read_user(user_id)
        if user_data is None or check_ban_and_auto_unban(user_data, game_database.users_manager):
            await ns.emit(
                "command",
                {
                    "id": commands.Logout,
                    "data": {
                        "reason": "banned",
                        "message": "حساب کاربری شما توسط مدیریت مسدود شده است.",
                    },
                },
                to=socket_id,
                namespace=namespace,
            )
            await ns.disconnect(socket_id, namespace=namespace)
            return None

        if check_maintenance or check_version or check_queue:
            config_data = game_database.config_manager.read_config() or {}
            if check_maintenance:
                maint_msg = get_maintenance_block(config_data)
                if maint_msg:
                    await ns.emit(
                        "command",
                        {
                            "id": commands.Logout,
                            "data": {"reason": "maintenance", "message": maint_msg},
                        },
                        to=socket_id,
                        namespace=namespace,
                    )
                    await ns.disconnect(socket_id, namespace=namespace)
                    return None

            if check_version:
                client_ver = str(auth.get("version", "")).strip() if isinstance(auth, dict) else ""
                if client_ver:
                    allowed_ver = str(config_data.get("allowed_version", "")).strip()
                    if allowed_ver and not is_version_allowed(client_ver, allowed_ver):
                        await ns.emit(
                            "command",
                            {
                                "id": commands.Logout,
                                "data": {
                                    "reason": "force_update",
                                    "message": f"نسخه بازی شما ({client_ver}) قدیمی است. حداقل نسخه مجاز {allowed_ver} می‌باشد.",
                                },
                            },
                            to=socket_id,
                            namespace=namespace,
                        )
                        await ns.disconnect(socket_id, namespace=namespace)
                        return None

            if check_queue:
                pre_game_id = auth.get("pre_game_id") if isinstance(auth, dict) else None
                is_reconn_pregame = allow_pre_game_reconnect and (
                    bool(pre_game_id) or (isinstance(user_data, dict) and bool(user_data.get("open_pre_game_id")))
                )
                if not is_reconn_pregame and is_queue_closed(config_data):
                    await ns.emit(
                        "command",
                        {
                            "id": getattr(commands, "Queue_Closed", "QueueClosed"),
                            "data": {"message": "صف مسابقات در حال حاضر توسط مدیریت بسته شده است."},
                        },
                        to=socket_id,
                        namespace=namespace,
                    )
                    await ns.disconnect(socket_id, namespace=namespace)
                    return None

    return token_data, user_data, is_bot
