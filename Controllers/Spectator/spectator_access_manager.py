"""
SpectatorAccessManager
Validates whether a user is allowed to spectate a given match:
- Checks user authentication
- Checks that user is not an active player in the match or another active match
- Checks match existence, running status, and spectatable game type
- Checks participant block lists (bidirectional)
- Checks lobby/match visibility and participant privacy settings (`everyone`, `friends`, `clan`, `none`)
- Checks spectator capacity per match
"""

from Controllers.Spectator.spectator_state_serializer import SpectatorStateSerializer
from Entities.Database import game_database


MAX_SPECTATORS_PER_GAME = 50


class SpectatorAccessManager:
    MAX_SPECTATORS_PER_GAME = MAX_SPECTATORS_PER_GAME

    @classmethod
    def check_can_spectate(
        cls,
        viewer_id: str,
        game_id: str,
        game_play,
        current_spectator_count: int = 0,
        active_player_game_id: str | None = None,
    ) -> tuple[bool, str, str]:
        """
        Returns (allowed: bool, reason_code: str, message_fa: str)
        """
        viewer_id_str = str(viewer_id or "").strip()
        game_id_str = str(game_id or "").strip()

        if not viewer_id_str:
            return False, "unauthenticated", "برای تماشای مسابقه ابتدا وارد حساب کاربری خود شوید."

        if not game_id_str or game_play is None:
            return False, "match_not_found", "این مسابقه به پایان رسیده یا دیگر فعال نیست."

        is_finished = bool(
            getattr(game_play, "is_game_finished", False)
            or getattr(game_play, "is_finished", False)
            or getattr(game_play, "is_game_terminated", False)
        )
        if is_finished:
            return False, "match_finished", "این مسابقه به پایان رسیده است."

        g_session = SpectatorStateSerializer.resolve_active_game_session(game_play)
        if g_session is None:
            return False, "session_unavailable", "مسابقه هنوز آماده تماشای زنده نیست."

        match_users = SpectatorStateSerializer.extract_participant_ids(game_play)
        if viewer_id_str in match_users:
            return False, "is_participant", "شما بازیکن فعال این مسابقه هستید و نمی‌توانید به عنوان تماشاگر وارد شوید."

        if active_player_game_id and str(active_player_game_id) != game_id_str:
            return False, "in_active_game", "شما در حال انجام یک مسابقه فعال هستید."

        g_type = SpectatorStateSerializer.resolve_active_game_type(game_play, g_session)
        is_safe, unsafe_msg = SpectatorStateSerializer.is_game_spectatable(g_type)
        if not is_safe:
            return False, "hidden_info_game", unsafe_msg

        if current_spectator_count >= cls.MAX_SPECTATORS_PER_GAME:
            return False, "spectator_limit_reached", "ظرفیت تماشاگران این مسابقه تکمیل شده است."

        allow_spectators = getattr(game_play, "allow_spectators", True)
        if allow_spectators is False or str(allow_spectators).lower() == "none":
            return False, "spectating_disabled", "امکان تماشای این مسابقه توسط سازنده غیرفعال شده است."

        # Check block relationships against all human participants
        for pid in match_users:
            if pid.startswith("bot_") or pid.startswith("test_bot"):
                continue
            try:
                if game_database.friends_manager.is_blocked(viewer_id_str, pid):
                    return False, "blocked", "امکان تماشای این مسابقه وجود ندارد."
            except Exception:
                pass

        visibility = str(getattr(game_play, "visibility", "everyone") or "everyone").lower()
        human_participants = [
            pid for pid in match_users if not (pid.startswith("bot_") or pid.startswith("test_bot"))
        ]

        if human_participants:
            for pid in human_participants:
                user_doc = cls._read_user_doc(pid)
                priv = (user_doc or {}).get("privacy", {}) if isinstance(user_doc, dict) else {}
                if not isinstance(priv, dict):
                    priv = {}

                show_game = priv.get("show_current_game", True)
                spec_mode = str(priv.get("allow_spectators", visibility or "everyone")).lower()
                if not show_game or spec_mode == "none":
                    return False, "privacy_restricted", "بازیکنان این مسابقه تماشای زنده را در تنظیمات حریم خصوصی محدود کرده‌اند."

                if spec_mode == "friends":
                    if not cls._are_friends(viewer_id_str, pid):
                        return False, "friends_only", "تماشای این مسابقه فقط برای دوستان بازیکنان مجاز است."
                elif spec_mode == "clan":
                    if not (cls._share_clan(viewer_id_str, pid) or cls._are_friends(viewer_id_str, pid)):
                        return False, "clan_only", "تماشای این مسابقه فقط برای دوستان یا هم‌کلنی‌های بازیکنان مجاز است."

        if visibility == "friends" and human_participants:
            if not any(cls._are_friends(viewer_id_str, pid) for pid in human_participants):
                return False, "friends_only", "تماشای این مسابقه فقط برای دوستان بازیکنان مجاز است."
        elif visibility == "clan" and human_participants:
            if not any(cls._share_clan(viewer_id_str, pid) for pid in human_participants):
                return False, "clan_only", "تماشای این مسابقه فقط برای اعضای کلن مجاز است."

        return True, "ok", ""

    @staticmethod
    def _read_user_doc(user_id: str) -> dict | None:
        try:
            um = game_database.users_manager
            if hasattr(um, "read_user"):
                doc = um.read_user(user_id)
                if isinstance(doc, dict):
                    return doc
            if hasattr(um, "read_by_id"):
                doc = um.read_by_id(user_id)
                if isinstance(doc, dict):
                    return doc
            return game_database.base_db["users"].find_one({"_id": user_id})
        except Exception:
            return None

    @staticmethod
    def _are_friends(user_a: str, user_b: str) -> bool:
        try:
            fm = game_database.friends_manager
            if hasattr(fm, "are_friends"):
                return bool(fm.are_friends(user_a, user_b))
            if hasattr(fm, "get_friend_ids"):
                return str(user_b) in set(str(x) for x in fm.get_friend_ids(user_a))
        except Exception:
            pass
        return False

    @staticmethod
    def _share_clan(user_a: str, user_b: str) -> bool:
        try:
            cm = game_database.clans_manager
            if hasattr(cm, "get_user_membership"):
                ma = cm.get_user_membership(user_a)
                mb = cm.get_user_membership(user_b)
                if ma and mb and ma.get("clan_id") and str(ma.get("clan_id")) == str(mb.get("clan_id")):
                    return True
            if hasattr(cm, "get_user_clan"):
                ca = cm.get_user_clan(user_a)
                cb = cm.get_user_clan(user_b)
                if ca and cb and ca.get("clan_id") and str(ca.get("clan_id")) == str(cb.get("clan_id")):
                    return True
        except Exception:
            pass
        return False
