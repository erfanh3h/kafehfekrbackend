"""
SpectatorStateSerializer
Responsible for:
1. Auditing and enforcing which games are safe to spectate vs. hidden-information games.
2. Generating sanitized, read-only game state snapshots for spectators without mutating live game state.
3. Sanitizing real-time broadcast commands before forwarding them to spectators.
"""

import copy
from datetime import datetime
from Commons import commands


# Games where all board/piece state is public and safe for spectators to watch live
SAFE_SPECTATOR_GAMES = {
    "ludo",
    "monopoly",
    "risk",
    "chess",
    "checkers",
    "backgammon",
    "othello",
    "fourinrow",
    "connect4",
    "mill",
    "pentago",
    "quoridor",
    "tictactoe",
    "xo",
    "xogame",
    "boxfour",
    "dotbox",
    "dotsandboxes",
    "yinsh",
    "yatzy",
    "mnumbers",
}

# Games with hidden player state (ships, secret codes, hidden mines, private hands, simultaneous secret choices)
# Spectating is disabled by default for these games unless dedicated public-only views exist.
PRIVATE_STATE_GAMES = {
    "battleship",
    "uno",
    "coup",
    "fekrbekr",
    "sudoku",
    "msweeper",
    "quiz",
    "rpc",
}

# Sensitive keys that must NEVER be included in any spectator snapshot or live event
FORBIDDEN_PRIVATE_KEYS = {
    "secret",
    "secret_code",
    "secret_pattern",
    "answer",
    "correct_answer",
    "solution",
    "solved_board",
    "mines",
    "mine_locations",
    "mine_board",
    "ships",
    "ship_board",
    "private_board",
    "player_boards",
    "hand",
    "hands",
    "player_hands",
    "cards_in_hand",
    "private_cards",
    "deck",
    "password",
    "device_id",
    "token",
}

# Public commands allowed to be streamed to spectators in real time
ALLOWED_PUBLIC_SPECTATOR_COMMANDS = {
    commands.Game_Play_Data,
    commands.Game_Play_Time,
    commands.Game_Play_Navigate,
    commands.Peace_Selected,
    commands.Peace_Rotated,
    commands.Peace_Swaped,
    commands.Peace_Removed,
    commands.Select_Remove_Peace,
    commands.Ring_Submited,
    commands.Ring_Moved,
    commands.Current_Turn,
    commands.Roll_Result,
    commands.Out_Of_Move,
    commands.Win_Happened,
    commands.New_Turn_Round,
    commands.Finish_Turn_Round,
    commands.New_Round,
    commands.Finish_Round,
    commands.Player_Score,
    commands.Not_played_Turns,
    commands.User_Disconnected,
    commands.User_Reconnected,
    commands.Finish_Reconnect_Time,
    commands.Surrender,
    commands.Monopoly_State,
    commands.Monopoly_Event,
    commands.Declare_Attack,
    commands.Attack,
    commands.AttackerArmy,
    commands.DefenderArmy,
    commands.QuestArmy,
    commands.Pass_Turn,
    commands.Strategy_Result,
    commands.Cancel_Attack,
    commands.Draw_Card,
    commands.Draw_Result,
    commands.Game_Data,
    commands.Start_Game,
    commands.Finish_Game,
    commands.Game_Finished,
    commands.Wait_Time,
}


class SpectatorStateSerializer:
    @staticmethod
    def normalize_game_type(game_type) -> str:
        val = getattr(game_type, "value", game_type)
        return str(val or "").strip().lower().replace("_", "").replace("-", "")

    @staticmethod
    def raw_game_type_str(game_type) -> str:
        val = getattr(game_type, "value", game_type)
        return str(val or "").strip()

    @classmethod
    def is_game_spectatable(cls, game_type) -> tuple[bool, str]:
        norm = cls.normalize_game_type(game_type)
        if not norm:
            return False, "نوع بازی نامشخص است."
        if norm in PRIVATE_STATE_GAMES:
            return False, "این بازی دارای اطلاعات مخفی بازیکنان است و امکان تماشای زنده ندارد."
        if norm not in SAFE_SPECTATOR_GAMES:
            return False, "امکان تماشای زنده برای این نوع بازی فعال نیست."
        return True, ""

    @classmethod
    def strip_private_fields(cls, data):
        """Recursively strip any forbidden private keys without mutating the original object."""
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                k_lower = str(k).strip().lower()
                if (
                    k_lower in FORBIDDEN_PRIVATE_KEYS
                    or k_lower.startswith("secret")
                    or k_lower.startswith("private_")
                ):
                    continue
                cleaned[k] = cls.strip_private_fields(v)
            return cleaned
        if isinstance(data, list):
            return [cls.strip_private_fields(item) for item in data]
        if isinstance(data, tuple):
            return [cls.strip_private_fields(item) for item in data]
        return copy.deepcopy(data)

    @classmethod
    def sanitize_dict(cls, data):
        return cls.strip_private_fields(data)

    @classmethod
    def resolve_active_game_session(cls, game_play):
        if game_play is None:
            return None
        return getattr(game_play, "game_session", None) or getattr(game_play, "current_game_session", None)

    @classmethod
    def resolve_active_game_type(cls, game_play, game_session=None) -> str:
        if game_session is None:
            game_session = cls.resolve_active_game_session(game_play)
        if game_session is not None and getattr(game_session, "game_type", None):
            return cls.raw_game_type_str(game_session.game_type)
        if game_play is not None:
            game_types = list(getattr(game_play, "game_types", []) or [])
            idx = int(getattr(game_play, "current_game_index", 0) or 0)
            if 0 <= idx < len(game_types):
                return cls.raw_game_type_str(game_types[idx])
            elif game_types:
                return cls.raw_game_type_str(game_types[0])
        return ""

    @classmethod
    def extract_board_state(cls, game_session) -> dict:
        """Safely extract public board state from a running game_session without mutating it."""
        if game_session is None:
            return {}
        raw_state = {}
        try:
            controller = getattr(game_session, "game_controller", None)
            if controller is not None and hasattr(controller, "get_game_data"):
                raw_state = controller.get_game_data() or {}
            elif hasattr(game_session, "get_game_data"):
                raw_state = game_session.get_game_data() or {}
        except Exception:
            raw_state = {}

        if not isinstance(raw_state, dict):
            raw_state = {"board": raw_state}

        sanitized = cls.strip_private_fields(raw_state)

        current_turn = cls.extract_current_turn(game_session, sanitized)
        if current_turn is not None and "current_turn" not in sanitized:
            sanitized["current_turn"] = current_turn

        return sanitized

    @classmethod
    def extract_current_turn(cls, game_session, board_state: dict | None = None) -> int:
        if isinstance(board_state, dict) and "current_turn" in board_state:
            try:
                return int(board_state["current_turn"])
            except Exception:
                pass
        if game_session is not None:
            for attr in ("turn", "current_turn"):
                val = getattr(game_session, attr, None)
                if isinstance(val, int) and val > 0:
                    return val
            controller = getattr(game_session, "game_controller", None)
            if controller is not None:
                for attr in ("current_turn", "turn", "gamer_turn"):
                    val = getattr(controller, attr, None)
                    if isinstance(val, int) and val > 0:
                        return val
        return 1

    @classmethod
    def extract_timer_data(cls, game_session) -> dict:
        if game_session is None:
            return {"turn_time": 30, "remaining_time": 30}
        try:
            timer_obj = getattr(game_session, "timer", None)
            if timer_obj is not None:
                max_t = int(getattr(timer_obj, "max_time", 30) or 30)
                counter = int(getattr(timer_obj, "counter", 0) or 0)
                rem_t = max(1, max_t - counter)
                return {"turn_time": max_t, "remaining_time": rem_t}
            if hasattr(game_session, "get_timer_data"):
                t_data = game_session.get_timer_data()
                if isinstance(t_data, dict):
                    return copy.deepcopy(t_data)
                if isinstance(t_data, (int, float)):
                    return {"turn_time": 30, "remaining_time": float(t_data)}
        except Exception:
            pass
        return {"turn_time": 30, "remaining_time": 30}

    @classmethod
    def extract_participant_ids(cls, game_play) -> list[str]:
        if game_play is None:
            return []
        gamers = getattr(game_play, "gamers", None)
        if isinstance(gamers, list) and gamers:
            ids = []
            for g in gamers:
                if isinstance(g, dict):
                    uid = g.get("user_id", g.get("id", ""))
                else:
                    uid = getattr(g, "user_id", "")
                if uid:
                    ids.append(str(uid))
            if ids:
                return ids
        users = getattr(game_play, "users", None)
        if isinstance(users, list):
            return [str(u) for u in users if u]
        return []

    @classmethod
    def build_gamers_payload(cls, game_play, game_session=None, user_profiles: dict | None = None) -> list[dict]:
        """
        Build the `gamers` array compatible with Cafe Fekr client (`GameManager.set_match_gamers`)
        and enriched with public profile fields for the Spectator UI.
        """
        if game_session is None:
            game_session = cls.resolve_active_game_session(game_play)
        user_profiles = user_profiles or {}
        gamer_scores = list(getattr(game_play, "gamer_scores", []) or [])

        # Map session gamer objects/dicts by user_id
        session_gamer_by_uid = {}
        raw_session_gamers = getattr(game_session, "gamers", None) if game_session is not None else None
        if isinstance(raw_session_gamers, list):
            for idx, sg in enumerate(raw_session_gamers):
                uid_s = str(sg.get("user_id", "") if isinstance(sg, dict) else getattr(sg, "user_id", ""))
                if uid_s:
                    session_gamer_by_uid[uid_s] = (idx + 1, sg)
        elif isinstance(raw_session_gamers, dict):
            for idx, (uid_s, sg) in enumerate(raw_session_gamers.items()):
                session_gamer_by_uid[str(uid_s)] = (idx + 1, sg)

        # Inspect controller for left/eliminated players (multiplayer Ludo/Risk/Monopoly/etc.)
        controller = getattr(game_session, "game_controller", None) if game_session is not None else None
        active_indexes = getattr(controller, "active_player_indexes", None) if controller is not None else None
        if isinstance(active_indexes, (list, tuple, set)):
            active_index_set = {int(x) for x in active_indexes if str(x).isdigit() or isinstance(x, int)}
        else:
            active_index_set = None
        leaver_gid = getattr(controller, "leaver_id", None) if controller is not None else None
        dc_user_ids = set(str(x) for x in (getattr(game_play, "disconnected_user_ids", None) or set()))

        raw_gamers = getattr(game_play, "gamers", None)
        gamers_list = []

        if isinstance(raw_gamers, list) and raw_gamers:
            for idx, g in enumerate(raw_gamers):
                if isinstance(g, dict):
                    uid_str = str(g.get("user_id", g.get("id", "")))
                    base_name = g.get("username", g.get("name", ""))
                    base_img = g.get("user_image", g.get("image", 0))
                    base_score = g.get("user_score", g.get("score", 0))
                    base_xp = g.get("user_xp", g.get("xp", 0))
                    is_dc = bool(g.get("is_disconnected", False))
                else:
                    uid_str = str(getattr(g, "user_id", ""))
                    base_name = getattr(g, "username", getattr(g, "name", ""))
                    base_img = getattr(g, "user_image", getattr(g, "image", 0))
                    base_score = getattr(g, "user_score", getattr(g, "score", 0))
                    base_xp = getattr(g, "user_xp", getattr(g, "xp", 0))
                    is_dc = bool(getattr(g, "is_disconnected", False))

                gamer_id = idx + 1
                remain_dc_time = 0
                sg_tuple = session_gamer_by_uid.get(uid_str)
                sg_obj = sg_tuple[1] if sg_tuple else None
                if sg_obj is not None:
                    if isinstance(sg_obj, dict):
                        gamer_id = int(sg_obj.get("gamer_id", sg_obj.get("id", gamer_id)) or gamer_id)
                        not_played = int(sg_obj.get("not_played_turns", sg_obj.get("not_played", 0)) or 0)
                        sg_score = int(sg_obj.get("game_score", sg_obj.get("score", 0)) or 0)
                        is_dc = is_dc or bool(sg_obj.get("is_disconnected", False))
                        remain_dc_time = int(sg_obj.get("remain_dc_time", 0) or 0)
                    else:
                        gamer_id = int(getattr(sg_obj, "gamer_id", getattr(sg_obj, "id", gamer_id)) or gamer_id)
                        not_played = int(getattr(sg_obj, "not_played_turns", 0) or 0)
                        sg_score = int(getattr(sg_obj, "game_score", 0) or 0)
                        is_dc = is_dc or bool(getattr(sg_obj, "is_disconnected", False))
                        sg_timer = getattr(sg_obj, "timer", None)
                        if sg_timer is not None and not getattr(sg_timer, "is_canceled", True):
                            remain_dc_time = max(0, int(getattr(sg_timer, "max_time", 0) or 0))
                else:
                    not_played = 0
                    sg_score = 0

                if uid_str in dc_user_ids:
                    is_dc = True

                is_left = False
                if active_index_set is not None and len(active_index_set) > 0 and gamer_id not in active_index_set:
                    is_left = True
                if leaver_gid is not None and str(leaver_gid) == str(gamer_id):
                    is_left = True
                if controller is not None and hasattr(controller, "players"):
                    c_players = getattr(controller, "players", None)
                    if isinstance(c_players, dict):
                        cp = c_players.get(gamer_id) or c_players.get(str(gamer_id))
                        if isinstance(cp, dict) and (cp.get("bankrupt") is True or cp.get("is_alive") is False or cp.get("eliminated") is True):
                            is_left = True
                        elif cp is not None and (getattr(cp, "bankrupt", False) or getattr(cp, "is_alive", True) is False):
                            is_left = True

                pub = user_profiles.get(uid_str, {}) if isinstance(user_profiles, dict) else {}
                username = str(pub.get("username") or base_name or f"بازیکن {gamer_id}")
                avatar = int(pub.get("image", pub.get("avatar", base_img)) or 0)
                user_score = int(pub.get("score", base_score) or 0)
                xp = int(pub.get("xp", base_xp) or 0)
                match_score = int(gamer_scores[idx]) if idx < len(gamer_scores) else sg_score

                gamers_list.append({
                    "id": gamer_id,
                    "gamer_id": gamer_id,
                    "team_id": gamer_id,
                    "user_id": uid_str,
                    "name": username,
                    "username": username,
                    "user_image": avatar,
                    "image": avatar,
                    "avatar": avatar,
                    "profile_frame": int(pub.get("profile_frame", 0) or 0),
                    "profile_title": str(pub.get("profile_title", "") or ""),
                    "clan": pub.get("clan"),
                    "user_score": user_score,
                    "score": match_score,
                    "game_score": sg_score,
                    "match_score": match_score,
                    "xp": xp,
                    "not_played": not_played,
                    "is_disconnected": is_dc,
                    "is_left": is_left,
                    "is_eliminated": is_left,
                    "remain_dc_time": remain_dc_time,
                })
        else:
            # Fallback if `game_play` only defines `users` list and `users_info` dict
            users = list(getattr(game_play, "users", []) or [])
            users_info = getattr(game_play, "users_info", {}) or {}
            for idx, uid in enumerate(users):
                uid_str = str(uid)
                gamer_id = idx + 1
                sg_tuple = session_gamer_by_uid.get(uid_str)
                sg_obj = sg_tuple[1] if sg_tuple else None
                if isinstance(sg_obj, dict) and "id" in sg_obj:
                    gamer_id = int(sg_obj["id"])
                u_info = users_info.get(uid_str, {}) if isinstance(users_info, dict) else {}
                pub = user_profiles.get(uid_str, {}) if isinstance(user_profiles, dict) else {}
                username = str(pub.get("username") or u_info.get("username") or u_info.get("name") or f"بازیکن {gamer_id}")
                avatar = int(pub.get("image", u_info.get("image", u_info.get("user_image", 0))) or 0)
                user_score = int(pub.get("score", u_info.get("score", 0)) or 0)
                match_score = int(gamer_scores[idx]) if idx < len(gamer_scores) else 0
                gamers_list.append({
                    "id": gamer_id,
                    "gamer_id": gamer_id,
                    "team_id": gamer_id,
                    "user_id": uid_str,
                    "name": username,
                    "username": username,
                    "user_image": avatar,
                    "image": avatar,
                    "avatar": avatar,
                    "profile_frame": int(pub.get("profile_frame", 0) or 0),
                    "profile_title": str(pub.get("profile_title", "") or ""),
                    "clan": pub.get("clan"),
                    "user_score": user_score,
                    "score": match_score,
                    "game_score": match_score,
                    "match_score": match_score,
                    "xp": int(pub.get("xp", 0) or 0),
                    "not_played": 0,
                    "is_disconnected": False,
                })

        gamers_list.sort(key=lambda g: int(g.get("id", 1)))
        return gamers_list

    @classmethod
    def serialize_snapshot(
        cls,
        game_id: str,
        game_play,
        game_session=None,
        spectator_count: int = 0,
        user_profiles: dict | None = None,
    ) -> dict:
        """
        Generate a complete, sanitized read-only snapshot for a spectator joining or resyncing.
        Includes both high-level spectator metadata and `reconnect_data` compatible with BaseGameBoard.
        """
        if game_session is None:
            game_session = cls.resolve_active_game_session(game_play)
        game_type = cls.resolve_active_game_type(game_play, game_session)

        board_state = cls.extract_board_state(game_session)
        current_turn = cls.extract_current_turn(game_session, board_state)
        timer_data = cls.extract_timer_data(game_session)
        gamers = cls.build_gamers_payload(game_play, game_session, user_profiles=user_profiles)

        scores_map = {str(g["id"]): int(g.get("match_score", 0)) for g in gamers}
        round_num = int(board_state.get("current_round", int(getattr(game_play, "current_game_index", 0) or 0) + 1) or 1)
        raw_score_type = getattr(game_play, "game_score_type", 0)
        score_type_val = getattr(raw_score_type, "value", raw_score_type)

        # Detect any currently disconnected (non-left) player whose reconnect pause timer is active
        disconnected_player = None
        for g in gamers:
            if bool(g.get("is_disconnected", False)) and not bool(g.get("is_left", False)) and int(g.get("remain_dc_time", 0) or 0) > 0:
                disconnected_player = {
                    "user_id": str(g.get("user_id", "")),
                    "gamer_id": int(g.get("gamer_id", g.get("id", 0))),
                    "username": str(g.get("username", g.get("name", "بازیکن"))),
                    "remaining_time": int(g.get("remain_dc_time", 60)),
                }
                break

        reconnect_payload = {
            "gamers": gamers,
            "game_data": board_state,
            "game_type": game_type,
            "current_turn": current_turn,
            "timer_data": timer_data.get("remaining_time", 30) if isinstance(timer_data, dict) else timer_data,
            "turn_time": timer_data.get("turn_time", 30) if isinstance(timer_data, dict) else 30,
            "scores": scores_map,
            "is_spectator": True,
            "disconnected_player": disconnected_player,
        }

        return {
            "game_id": str(game_id),
            "game_type": game_type,
            "game_types": [cls.raw_game_type_str(gt) for gt in (getattr(game_play, "game_types", []) or [game_type])],
            "current_game_index": int(getattr(game_play, "current_game_index", 0) or 0),
            "game_score_type": score_type_val,
            "status": "in_progress",
            "is_spectator": True,
            "spectator_count": int(max(0, spectator_count)),
            "current_turn": current_turn,
            "round_number": round_num,
            "players": gamers,
            "gamers": gamers,
            "scores": scores_map,
            "board_state": board_state,
            "game_data": board_state,
            "timer_data": timer_data,
            "disconnected_player": disconnected_player,
            "reconnect_data": reconnect_payload,
            "server_time": datetime.utcnow().isoformat(),
        }

    @classmethod
    def sanitize_live_command(cls, game_type: str, command: dict) -> dict | None:
        """
        Inspect an outgoing room command emitted via SocketIOManager.send_command.
        Returns a sanitized copy if safe for spectators, or None if it should not be forwarded.
        """
        if not isinstance(command, dict):
            return None
        ok, _ = cls.is_game_spectatable(game_type)
        if not ok:
            return None

        cmd_id = command.get("id") or command.get("command_id")
        if cmd_id not in ALLOWED_PUBLIC_SPECTATOR_COMMANDS:
            return None

        cleaned = cls.strip_private_fields(command)
        if "id" not in cleaned and cmd_id:
            cleaned["id"] = cmd_id
        return cleaned
