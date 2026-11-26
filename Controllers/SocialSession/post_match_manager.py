import asyncio
import secrets
import time
from typing import Callable

from Commons import commands
from Commons.static_functions import make_command_json, create_random_name
from Entities.Database.social.rivals_collection import is_bot_user_id


class PostMatchManager:
    """Coordinates post-match Rematch & Switch-Game-Together flows over /social.

    Strictly restricted to finished 2-player human-vs-human matches. Bot matches
    (ClassicRank, bot_*, test_bot*, 3goBRU, is_bot=True) are never registered.
    """

    SESSION_TTL_SEC = 120.0
    REMATCH_TIMEOUT_SEC = 15
    SWITCH_GAME_TIMEOUT_SEC = 20

    def __init__(
        self,
        db_provider: Callable | None = None,
        add_new_game_fn: Callable | None = None,
        create_private_lobby_fn: Callable | None = None,
        valid_game_types: list[str] | None = None,
    ):
        self._db_provider = db_provider
        self._add_new_game_fn = add_new_game_fn
        self._create_private_lobby_fn = create_private_lobby_fn
        self._valid_game_types_override = valid_game_types
        # game_id -> session dict
        self.sessions: dict[str, dict] = {}
        # user_id -> most recent finished game_id
        self.user_last_session: dict[str, str] = {}

    def _get_db(self):
        if self._db_provider is not None:
            return self._db_provider()
        from Entities.Database import game_database
        return game_database

    def _get_canonical_game_type(self, raw_game_type: str) -> str:
        raw = str(raw_game_type or "").strip()
        if not raw:
            return ""
        if self._valid_game_types_override is not None:
            lookup = {str(g).lower(): str(g) for g in self._valid_game_types_override}
            return lookup.get(raw.lower(), "")
        from Entities.Games.game_types import GameTypesEnum
        for gt in GameTypesEnum:
            if gt.value.lower() == raw.lower():
                return gt.value
        return ""

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_ids = [
            gid for gid, sess in self.sessions.items()
            if now >= float(sess.get("expires_at", 0.0)) or bool(sess.get("consumed", False))
        ]
        for gid in expired_ids:
            sess = self.sessions.pop(gid, None)
            if sess:
                self._cancel_offer_task(sess)
                for uid in sess.get("player_ids", []):
                    if self.user_last_session.get(uid) == gid:
                        self.user_last_session.pop(uid, None)

    def _cancel_offer_task(self, sess: dict) -> None:
        offer = sess.get("active_offer")
        if isinstance(offer, dict):
            task = offer.get("timeout_task")
            if task is not None and hasattr(task, "cancel"):
                try:
                    task.cancel()
                except Exception:
                    pass
            offer["timeout_task"] = None

    def register_finished_match(
        self,
        game_id: str,
        gamers: list,
        game_types: list,
        game_score_type,
    ) -> bool:
        self._cleanup_expired()
        gid = str(game_id or "").strip()
        if not gid or not isinstance(gamers, list) or len(gamers) != 2:
            return False

        score_type_val = getattr(game_score_type, "value", str(game_score_type or ""))
        if str(score_type_val).lower() == "classicrank":
            return False

        player_ids: list[str] = []
        players_meta: dict[str, dict] = {}
        for g in gamers:
            uid = str(getattr(g, "user_id", "") or "").strip()
            if not uid or is_bot_user_id(uid) or bool(getattr(g, "is_bot", False)):
                return False
            player_ids.append(uid)
            players_meta[uid] = {
                "user_id": uid,
                "username": str(getattr(g, "username", "بازیکن") or "بازیکن"),
                "user_image": int(getattr(g, "user_image", 0) or 0),
                "user_coin": int(getattr(g, "user_coin", 0) or 0),
                "user_score": int(getattr(g, "user_score", 0) or 0),
                "profile_frame": int(getattr(g, "profile_frame", 1) or 1),
            }

        if len(set(player_ids)) != 2:
            return False

        last_gt = str(game_types[-1]) if (isinstance(game_types, list) and game_types) else "TicTacToe"
        canonical_gt = self._get_canonical_game_type(last_gt) or last_gt

        now = time.time()
        self.sessions[gid] = {
            "game_id": gid,
            "player_ids": player_ids,
            "players_meta": players_meta,
            "game_type": canonical_gt,
            "original_score_type": str(score_type_val),
            "created_at": now,
            "expires_at": now + self.SESSION_TTL_SEC,
            "active_offer": None,
            "left_users": set(),
            "consumed": False,
        }
        for uid in player_ids:
            self.user_last_session[uid] = gid
        return True

    def _get_session_for_user(self, user_id: str, game_id: str) -> tuple[dict | None, str, str]:
        self._cleanup_expired()
        uid = str(user_id or "").strip()
        gid = str(game_id or "").strip()
        if not gid:
            gid = self.user_last_session.get(uid, "")
        sess = self.sessions.get(gid)
        if not sess or sess.get("consumed"):
            return None, "", "مهلت درخواست پس از مسابقه به پایان رسیده است."
        pids = sess.get("player_ids", [])
        if uid not in pids:
            return None, "", "شما در این مسابقه حضور نداشتید."
        opp_id = pids[1] if pids[0] == uid else pids[0]
        if opp_id in sess.get("left_users", set()):
            return None, opp_id, "حریف صفحه پایان مسابقه را ترک کرده است."
        return sess, opp_id, ""

    def _check_pair_can_start_game(self, uid: str, opp_id: str) -> tuple[bool, str]:
        db = self._get_db()
        try:
            if hasattr(db, "friends_manager") and db.friends_manager.is_blocked(uid, opp_id):
                return False, "امکان شروع بازی مجدد با این بازیکن وجود ندارد."
        except Exception:
            pass
        try:
            u1 = db.users_manager.read_user(uid) or {}
            u2 = db.users_manager.read_user(opp_id) or {}
            if str(u1.get("open_game_id", "") or ""):
                return False, "شما در حال حاضر در بازی فعال دیگری هستید."
            if str(u2.get("open_game_id", "") or ""):
                return False, "حریف هم‌اکنون وارد بازی دیگری شده است."
        except Exception:
            pass
        return True, ""

    def _spawn_direct_match(self, sess: dict, target_game_type: str) -> str:
        """Spawns a fresh 1v1 friendly LOBBY match with SWAPPED P1 <-> P2 roles."""
        db = self._get_db()
        # Swap original player order so first-turn / White-Black / Red-Blue flips fairly
        p1_old, p2_old = sess["player_ids"][0], sess["player_ids"][1]
        swapped_ids = [p2_old, p1_old]
        new_game_id = f"rm_{create_random_name()}"

        from Models.Queuer import QueuerModel
        from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum

        queuers = []
        for pid in swapped_ids:
            u_doc = db.users_manager.read_user(pid) or {}
            fallback = sess["players_meta"].get(pid, {})
            queuers.append(
                QueuerModel(
                    user_id=pid,
                    username=str(u_doc.get("username", fallback.get("username", "بازیکن")) or "بازیکن"),
                    socket_id="",
                    user_image=int(u_doc.get("image", fallback.get("user_image", 0)) or 0),
                    user_coin=int(u_doc.get("coin", fallback.get("user_coin", 0)) or 0),
                    user_score=int(u_doc.get("score", fallback.get("user_score", 0)) or 0),
                    profile_frame=int(u_doc.get("profile_frame", fallback.get("profile_frame", 1)) or 1),
                )
            )
            db.users_manager.update_user(pid, open_game_id=new_game_id)

        if self._add_new_game_fn is not None:
            self._add_new_game_fn(new_game_id, queuers, [target_game_type], GameScoreTypesEnum.LOBBY)
        else:
            from Entities.SocketIOClass.game import add_new_game
            add_new_game(new_game_id, queuers, [target_game_type], GameScoreTypesEnum.LOBBY)

        return new_game_id

    def _create_private_switch_lobby(self, sess: dict, creator_id: str, target_game_type: str) -> dict:
        if self._create_private_lobby_fn is not None:
            return self._create_private_lobby_fn(creator_id, target_game_type)
        from Commons import static_functions
        from Models.Lobby import LobbyModel
        from Entities.SocketIOClass.lobby import lobby_session

        lobby_id = static_functions.create_random_game_id(length=6)
        lobby_password = secrets.token_hex(4)
        creator_name = sess["players_meta"].get(creator_id, {}).get("username", "دوستانه")
        lobby_name = f"اتاق خصوصی {creator_name}"[:28]
        new_lobby = LobbyModel(
            lobby_id=lobby_id,
            creator_id=creator_id,
            game_type=target_game_type,
            lobby_name=lobby_name,
            lobby_count=2,
            lobby_password=lobby_password,
        )
        lobby_session.lobbies.append(new_lobby)
        return {
            "lobby_id": lobby_id,
            "lobby_password": lobby_password,
            "game_type": target_game_type,
            "creator_id": creator_id,
        }

    async def _emit_to_user(self, namespace_obj, user_id: str, cmd_id: str, payload: dict) -> None:
        if namespace_obj is None:
            return
        await namespace_obj.emit(
            "command",
            make_command_json(id=cmd_id, data=payload),
            room=f"user_{user_id}",
            namespace="/social",
        )

    def _schedule_offer_timeout(self, sess: dict, offer_id: str, timeout_sec: int, namespace_obj) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def _expire():
            try:
                await asyncio.sleep(timeout_sec)
            except asyncio.CancelledError:
                return
            current_offer = sess.get("active_offer")
            if not isinstance(current_offer, dict) or current_offer.get("offer_id") != offer_id:
                return
            if sess.get("consumed"):
                return
            offer_kind = current_offer.get("kind", "rematch")
            sess["active_offer"] = None
            declined_cmd = (
                commands.Rematch_Declined if offer_kind == "rematch" else commands.Switch_Game_Declined
            )
            payload = {
                "game_id": sess["game_id"],
                "reason": "timeout",
                "message": "زمان پاسخ به درخواست به پایان رسید.",
            }
            for pid in sess["player_ids"]:
                await self._emit_to_user(namespace_obj, pid, declined_cmd, payload)

        task = loop.create_task(_expire())
        if isinstance(sess.get("active_offer"), dict):
            sess["active_offer"]["timeout_task"] = task

    async def handle_rematch_request(self, user_id: str, game_id: str, namespace_obj) -> dict:
        uid = str(user_id or "").strip()
        sess, opp_id, err = self._get_session_for_user(uid, game_id)
        if err or sess is None:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Rematch_Declined,
                {"game_id": str(game_id or ""), "reason": "unavailable", "message": err},
            )
            return {"ok": False, "reason": "unavailable", "message": err}

        can_start, block_err = self._check_pair_can_start_game(uid, opp_id)
        if not can_start:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Rematch_Declined,
                {"game_id": sess["game_id"], "reason": "busy", "message": block_err},
            )
            return {"ok": False, "reason": "busy", "message": block_err}

        existing = sess.get("active_offer")
        # Mutual / simultaneous rematch tap -> accept immediately!
        if isinstance(existing, dict) and existing.get("kind") == "rematch" and existing.get("from_user_id") == opp_id:
            return await self.handle_rematch_respond(uid, sess["game_id"], "accept", namespace_obj)

        # Duplicate tap from same user -> resend remaining waiting state
        if isinstance(existing, dict) and existing.get("kind") == "rematch" and existing.get("from_user_id") == uid:
            rem = max(1, int(existing.get("expires_at", time.time()) - time.time()))
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Rematch_State,
                {"game_id": sess["game_id"], "status": "waiting", "timeout": rem, "game_type": sess["game_type"]},
            )
            return {"ok": True, "status": "waiting", "timeout": rem}

        self._cancel_offer_task(sess)
        offer_id = secrets.token_hex(6)
        sess["active_offer"] = {
            "offer_id": offer_id,
            "kind": "rematch",
            "from_user_id": uid,
            "target_game_type": sess["game_type"],
            "open_lobby": False,
            "expires_at": time.time() + self.REMATCH_TIMEOUT_SEC,
            "timeout_task": None,
        }
        self._schedule_offer_timeout(sess, offer_id, self.REMATCH_TIMEOUT_SEC, namespace_obj)

        from_meta = sess["players_meta"].get(uid, {})
        await self._emit_to_user(
            namespace_obj,
            uid,
            commands.Rematch_State,
            {
                "game_id": sess["game_id"],
                "status": "waiting",
                "timeout": self.REMATCH_TIMEOUT_SEC,
                "game_type": sess["game_type"],
            },
        )
        await self._emit_to_user(
            namespace_obj,
            opp_id,
            commands.Rematch_Offered,
            {
                "game_id": sess["game_id"],
                "from_user_id": uid,
                "from_username": from_meta.get("username", "حریف"),
                "game_type": sess["game_type"],
                "timeout": self.REMATCH_TIMEOUT_SEC,
            },
        )
        return {"ok": True, "status": "offered", "timeout": self.REMATCH_TIMEOUT_SEC}

    async def handle_rematch_respond(self, user_id: str, game_id: str, action: str, namespace_obj) -> dict:
        uid = str(user_id or "").strip()
        act = str(action or "decline").strip().lower()
        sess, opp_id, err = self._get_session_for_user(uid, game_id)
        if err or sess is None:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Rematch_Declined,
                {"game_id": str(game_id or ""), "reason": "unavailable", "message": err},
            )
            return {"ok": False, "reason": "unavailable"}

        offer = sess.get("active_offer")
        if not isinstance(offer, dict) or offer.get("kind") != "rematch":
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Rematch_Declined,
                {"game_id": sess["game_id"], "reason": "expired", "message": "درخواست بازی مجدد منقضی شده است."},
            )
            return {"ok": False, "reason": "expired"}

        if act in ("decline", "cancel"):
            self._cancel_offer_task(sess)
            sess["active_offer"] = None
            reason = "cancelled" if offer.get("from_user_id") == uid else "declined"
            msg = "درخواست بازی مجدد لغو شد." if reason == "cancelled" else "حریف درخواست بازی مجدد را نپذیرفت."
            for pid in sess["player_ids"]:
                await self._emit_to_user(
                    namespace_obj,
                    pid,
                    commands.Rematch_Declined,
                    {"game_id": sess["game_id"], "reason": reason, "by_user_id": uid, "message": msg},
                )
            return {"ok": True, "status": reason}

        if act != "accept" or offer.get("from_user_id") == uid:
            return {"ok": False, "reason": "invalid_action"}

        can_start, block_err = self._check_pair_can_start_game(uid, opp_id)
        if not can_start:
            self._cancel_offer_task(sess)
            sess["active_offer"] = None
            for pid in sess["player_ids"]:
                await self._emit_to_user(
                    namespace_obj,
                    pid,
                    commands.Rematch_Declined,
                    {"game_id": sess["game_id"], "reason": "busy", "message": block_err},
                )
            return {"ok": False, "reason": "busy", "message": block_err}

        self._cancel_offer_task(sess)
        sess["active_offer"] = None
        sess["consumed"] = True

        new_game_id = self._spawn_direct_match(sess, sess["game_type"])
        accepted_payload = {
            "old_game_id": sess["game_id"],
            "new_game_id": new_game_id,
            "game_id": new_game_id,
            "game_type": sess["game_type"],
            "swapped_roles": True,
            "match_mode": "lobby",
        }
        for pid in sess["player_ids"]:
            await self._emit_to_user(namespace_obj, pid, commands.Rematch_Accepted, accepted_payload)

        self.sessions.pop(sess["game_id"], None)
        return {"ok": True, "status": "accepted", "new_game_id": new_game_id, "game_type": sess["game_type"]}

    async def handle_switch_game_request(
        self,
        user_id: str,
        game_id: str,
        target_game_type: str,
        open_lobby: bool = False,
        namespace_obj=None,
    ) -> dict:
        uid = str(user_id or "").strip()
        sess, opp_id, err = self._get_session_for_user(uid, game_id)
        if err or sess is None:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Switch_Game_Declined,
                {"game_id": str(game_id or ""), "reason": "unavailable", "message": err},
            )
            return {"ok": False, "reason": "unavailable", "message": err}

        canonical_gt = self._get_canonical_game_type(target_game_type)
        if not canonical_gt:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Switch_Game_Declined,
                {"game_id": sess["game_id"], "reason": "invalid_game", "message": "بازی انتخاب‌شده معتبر نیست."},
            )
            return {"ok": False, "reason": "invalid_game"}

        can_start, block_err = self._check_pair_can_start_game(uid, opp_id)
        if not can_start:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Switch_Game_Declined,
                {"game_id": sess["game_id"], "reason": "busy", "message": block_err},
            )
            return {"ok": False, "reason": "busy", "message": block_err}

        existing = sess.get("active_offer")
        if (
            isinstance(existing, dict)
            and existing.get("kind") == "switch_game"
            and existing.get("from_user_id") == opp_id
            and existing.get("target_game_type") == canonical_gt
        ):
            return await self.handle_switch_game_respond(uid, sess["game_id"], "accept", namespace_obj)

        self._cancel_offer_task(sess)
        offer_id = secrets.token_hex(6)
        sess["active_offer"] = {
            "offer_id": offer_id,
            "kind": "switch_game",
            "from_user_id": uid,
            "target_game_type": canonical_gt,
            "open_lobby": bool(open_lobby),
            "expires_at": time.time() + self.SWITCH_GAME_TIMEOUT_SEC,
            "timeout_task": None,
        }
        self._schedule_offer_timeout(sess, offer_id, self.SWITCH_GAME_TIMEOUT_SEC, namespace_obj)

        from_meta = sess["players_meta"].get(uid, {})
        await self._emit_to_user(
            namespace_obj,
            uid,
            commands.Switch_Game_State,
            {
                "game_id": sess["game_id"],
                "status": "waiting",
                "target_game_type": canonical_gt,
                "timeout": self.SWITCH_GAME_TIMEOUT_SEC,
            },
        )
        await self._emit_to_user(
            namespace_obj,
            opp_id,
            commands.Switch_Game_Offered,
            {
                "game_id": sess["game_id"],
                "from_user_id": uid,
                "from_username": from_meta.get("username", "حریف"),
                "target_game_type": canonical_gt,
                "open_lobby": bool(open_lobby),
                "timeout": self.SWITCH_GAME_TIMEOUT_SEC,
            },
        )
        return {"ok": True, "status": "offered", "target_game_type": canonical_gt}

    async def handle_switch_game_respond(self, user_id: str, game_id: str, action: str, namespace_obj) -> dict:
        uid = str(user_id or "").strip()
        act = str(action or "decline").strip().lower()
        sess, opp_id, err = self._get_session_for_user(uid, game_id)
        if err or sess is None:
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Switch_Game_Declined,
                {"game_id": str(game_id or ""), "reason": "unavailable", "message": err},
            )
            return {"ok": False, "reason": "unavailable"}

        offer = sess.get("active_offer")
        if not isinstance(offer, dict) or offer.get("kind") != "switch_game":
            await self._emit_to_user(
                namespace_obj,
                uid,
                commands.Switch_Game_Declined,
                {"game_id": sess["game_id"], "reason": "expired", "message": "پیشنهاد تغییر بازی منقضی شده است."},
            )
            return {"ok": False, "reason": "expired"}

        if act in ("decline", "cancel"):
            self._cancel_offer_task(sess)
            sess["active_offer"] = None
            reason = "cancelled" if offer.get("from_user_id") == uid else "declined"
            msg = "پیشنهاد تغییر بازی لغو شد." if reason == "cancelled" else "حریف پیشنهاد تغییر بازی را نپذیرفت."
            for pid in sess["player_ids"]:
                await self._emit_to_user(
                    namespace_obj,
                    pid,
                    commands.Switch_Game_Declined,
                    {"game_id": sess["game_id"], "reason": reason, "by_user_id": uid, "message": msg},
                )
            return {"ok": True, "status": reason}

        if act != "accept" or offer.get("from_user_id") == uid:
            return {"ok": False, "reason": "invalid_action"}

        can_start, block_err = self._check_pair_can_start_game(uid, opp_id)
        if not can_start:
            self._cancel_offer_task(sess)
            sess["active_offer"] = None
            for pid in sess["player_ids"]:
                await self._emit_to_user(
                    namespace_obj,
                    pid,
                    commands.Switch_Game_Declined,
                    {"game_id": sess["game_id"], "reason": "busy", "message": block_err},
                )
            return {"ok": False, "reason": "busy", "message": block_err}

        target_gt = str(offer.get("target_game_type", sess["game_type"]))
        use_lobby = bool(offer.get("open_lobby", False))
        creator_id = str(offer.get("from_user_id", uid))
        self._cancel_offer_task(sess)
        sess["active_offer"] = None
        sess["consumed"] = True

        if use_lobby:
            lobby_info = self._create_private_switch_lobby(sess, creator_id, target_gt)
            payload = {
                "old_game_id": sess["game_id"],
                "mode": "lobby",
                "lobby_id": lobby_info["lobby_id"],
                "lobby_password": lobby_info["lobby_password"],
                "game_type": target_gt,
                "creator_id": creator_id,
            }
            for pid in sess["player_ids"]:
                await self._emit_to_user(namespace_obj, pid, commands.Switch_Game_Accepted, payload)
            self.sessions.pop(sess["game_id"], None)
            return {"ok": True, "status": "accepted", "mode": "lobby", **lobby_info}

        new_game_id = self._spawn_direct_match(sess, target_gt)
        payload = {
            "old_game_id": sess["game_id"],
            "mode": "direct",
            "new_game_id": new_game_id,
            "game_id": new_game_id,
            "game_type": target_gt,
            "swapped_roles": True,
            "match_mode": "lobby",
        }
        for pid in sess["player_ids"]:
            await self._emit_to_user(namespace_obj, pid, commands.Switch_Game_Accepted, payload)
        self.sessions.pop(sess["game_id"], None)
        return {"ok": True, "status": "accepted", "mode": "direct", "new_game_id": new_game_id, "game_type": target_gt}

    async def handle_post_match_leave(self, user_id: str, game_id: str, namespace_obj) -> None:
        uid = str(user_id or "").strip()
        gid = str(game_id or "").strip() or self.user_last_session.get(uid, "")
        sess = self.sessions.get(gid)
        if not sess or uid not in sess.get("player_ids", []):
            return
        sess["left_users"].add(uid)
        self._cancel_offer_task(sess)
        sess["active_offer"] = None
        opp_id = sess["player_ids"][1] if sess["player_ids"][0] == uid else sess["player_ids"][0]
        if opp_id not in sess["left_users"]:
            leave_payload = {
                "game_id": gid,
                "reason": "opponent_left",
                "by_user_id": uid,
                "message": "حریف صفحه پایان مسابقه را ترک کرد.",
            }
            await self._emit_to_user(namespace_obj, opp_id, commands.Rematch_Declined, leave_payload)
            await self._emit_to_user(namespace_obj, opp_id, commands.Switch_Game_Declined, leave_payload)

    async def handle_user_disconnected(self, user_id: str, namespace_obj) -> None:
        uid = str(user_id or "").strip()
        gid = self.user_last_session.get(uid, "")
        if gid:
            await self.handle_post_match_leave(uid, gid, namespace_obj)


post_match_manager = PostMatchManager()
