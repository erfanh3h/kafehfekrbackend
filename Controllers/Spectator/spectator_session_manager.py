"""
SpectatorSessionManager
Manages the full lifecycle of spectator sessions across all active matches:
- Tracks spectators per match (user_id and socket_ids) without adding them to player lists
- Enforces rate limits and single-match-per-spectator rules (joining a new match automatically leaves the old one)
- Synchronizes live match metadata (`spectator_count`, `current_game_type`, `is_spectatable`) to MongoDB `game_play_history`
- Broadcasts `SpectatorCountUpdated` to both spectators and match participants
- Forwards sanitized real-time game commands and reactions via `SpectatorGameState`
- Handles match completion / cancellation / disconnect cleanup via `SpectatorGameEnded`
"""

import time
from datetime import datetime, timezone
from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.Spectator.spectator_room_manager import SpectatorRoomManager
from Controllers.Spectator.spectator_state_serializer import SpectatorStateSerializer
from Entities.Database import game_database
from Entities.SocketIOClass import Socket_Server


class SpectatorSessionManager:
    def __init__(self):
        # game_id -> {user_id: set(sid)}
        self.game_spectators: dict[str, dict[str, set[str]]] = {}
        # sid -> {"user_id": str, "game_id": str, "namespace": str}
        self.sid_registry: dict[str, dict] = {}
        # user_id -> game_id (each user spectates at most one match at a time)
        self.user_spectating_game: dict[str, str] = {}
        # Rate limit buckets: f"{user_id}:{action}" -> list[float]
        self._rate_buckets: dict[str, list[float]] = {}

    def check_rate_limit(self, user_id: str, action: str, limit: int = 12, window_sec: float = 10.0) -> bool:
        now = time.time()
        key = f"{user_id}:{action}"
        bucket = [t for t in self._rate_buckets.get(key, []) if now - t < window_sec]
        if len(bucket) >= limit:
            self._rate_buckets[key] = bucket
            return False
        bucket.append(now)
        self._rate_buckets[key] = bucket
        return True

    def get_spectator_count(self, game_id: str) -> int:
        gid = str(game_id or "")
        users_map = self.game_spectators.get(gid, {})
        return len(users_map)

    def get_spectated_game_for_sid(self, sid: str) -> str | None:
        info = self.sid_registry.get(sid)
        return info.get("game_id") if isinstance(info, dict) else None

    def get_spectated_game_for_user(self, user_id: str) -> str | None:
        return self.user_spectating_game.get(str(user_id or ""))

    def is_user_spectating(self, user_id: str, game_id: str | None = None) -> bool:
        cur = self.user_spectating_game.get(str(user_id or ""))
        if not cur:
            return False
        if game_id is not None:
            return cur == str(game_id)
        return True

    async def add_spectator(self, user_id: str, sid: str, game_id: str, namespace: str = "/social") -> int:
        uid = str(user_id)
        gid = str(game_id)

        prev_sid_info = self.sid_registry.get(sid)
        if prev_sid_info and prev_sid_info.get("game_id") != gid:
            await self.remove_spectator_by_sid(sid)

        prev_user_gid = self.user_spectating_game.get(uid)
        if prev_user_gid and prev_user_gid != gid:
            await self.remove_spectator_by_user(uid, prev_user_gid)

        users_map = self.game_spectators.setdefault(gid, {})
        sids = users_map.setdefault(uid, set())
        sids.add(sid)

        self.sid_registry[sid] = {
            "user_id": uid,
            "game_id": gid,
            "namespace": namespace,
        }
        self.user_spectating_game[uid] = gid

        await SpectatorRoomManager.join_spectator_room(sid, gid, namespace=namespace)
        count = self.get_spectator_count(gid)
        self._update_db_spectator_count(gid, count)
        await self.broadcast_spectator_count(gid, count)
        return count

    async def remove_spectator_by_sid(self, sid: str) -> tuple[str | None, str | None, int]:
        info = self.sid_registry.pop(sid, None)
        if not info:
            return None, None, 0

        uid = str(info["user_id"])
        gid = str(info["game_id"])
        ns = str(info.get("namespace", "/social"))

        await SpectatorRoomManager.leave_spectator_room(sid, gid, namespace=ns)

        users_map = self.game_spectators.get(gid, {})
        if uid in users_map:
            users_map[uid].discard(sid)
            if not users_map[uid]:
                users_map.pop(uid, None)
                if self.user_spectating_game.get(uid) == gid:
                    self.user_spectating_game.pop(uid, None)
        if not users_map:
            self.game_spectators.pop(gid, None)

        count = self.get_spectator_count(gid)
        self._update_db_spectator_count(gid, count)
        await self.broadcast_spectator_count(gid, count)
        return uid, gid, count

    async def remove_spectator_by_user(self, user_id: str, game_id: str | None = None) -> int:
        uid = str(user_id)
        gid = str(game_id or self.user_spectating_game.get(uid) or "")
        if not gid:
            return 0

        users_map = self.game_spectators.get(gid, {})
        sids = list(users_map.pop(uid, set()))
        for s in sids:
            info = self.sid_registry.pop(s, None)
            ns = str((info or {}).get("namespace", "/social"))
            await SpectatorRoomManager.leave_spectator_room(s, gid, namespace=ns)

        if not users_map:
            self.game_spectators.pop(gid, None)
        if self.user_spectating_game.get(uid) == gid:
            self.user_spectating_game.pop(uid, None)

        count = self.get_spectator_count(gid)
        self._update_db_spectator_count(gid, count)
        await self.broadcast_spectator_count(gid, count)
        return count

    async def broadcast_spectator_count(self, game_id: str, count: int | None = None) -> None:
        gid = str(game_id)
        c = self.get_spectator_count(gid) if count is None else int(count)
        cmd = make_command_json(
            id=commands.SpectatorCountUpdated,
            data={
                "game_id": gid,
                "spectator_count": c,
            },
        )
        await SpectatorRoomManager.broadcast_to_spectators(gid, cmd)
        try:
            await Socket_Server.emit("command", cmd, room=gid, namespace="/game")
        except Exception:
            pass

    def _get_history_collection(self):
        try:
            mgr = getattr(game_database, "game_play_history_manager", None)
            if mgr is not None and hasattr(mgr, "collection"):
                return mgr.collection
            return game_database.base_db["game_play_history"]
        except Exception:
            return None

    def sync_live_match_metadata(self, game_play, is_running: bool = True) -> None:
        """
        Keep `game_play_history` updated with current sub-game type, spectatability, and spectator count
        so the FastAPI discovery endpoint (`GET /spectator/live-games`) has real-time accuracy.
        """
        if game_play is None:
            return
        gid = str(getattr(game_play, "game_play_id", "") or "")
        if not gid:
            return
        g_session = SpectatorStateSerializer.resolve_active_game_session(game_play)
        g_type = SpectatorStateSerializer.resolve_active_game_type(game_play, g_session)

        is_safe, _ = SpectatorStateSerializer.is_game_spectatable(g_type)
        allow_spec = getattr(game_play, "allow_spectators", True)
        visibility = str(getattr(game_play, "visibility", "everyone") or "everyone")
        count = self.get_spectator_count(gid)
        is_fin = bool(
            getattr(game_play, "is_game_finished", False)
            or getattr(game_play, "is_finished", False)
            or getattr(game_play, "is_game_terminated", False)
        )

        col = self._get_history_collection()
        if col is not None:
            try:
                col.update_one(
                    {"_id": gid},
                    {
                        "$set": {
                            "current_game_type": g_type,
                            "current_game_index": int(getattr(game_play, "current_game_index", 0) or 0),
                            "is_spectatable": bool(is_safe and allow_spec is not False and str(allow_spec).lower() != "none"),
                            "allow_spectators": allow_spec,
                            "visibility": visibility,
                            "spectator_count": count,
                            "is_running": bool(is_running and not is_fin),
                            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        }
                    },
                )
            except Exception:
                pass

    def _update_db_spectator_count(self, game_id: str, count: int) -> None:
        col = self._get_history_collection()
        if col is not None:
            try:
                col.update_one(
                    {"_id": str(game_id)},
                    {
                        "$set": {
                            "spectator_count": int(max(0, count)),
                            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        }
                    },
                )
            except Exception:
                pass

    async def on_game_command(self, game_id: str, command: dict, game_play=None) -> None:
        """
        Called by `SocketIOManagerClass.send_command` when a public broadcast command is sent to a game room.
        Never called for `send_private_command`.
        """
        gid = str(game_id or "")
        if not gid or not self.game_spectators.get(gid):
            return

        if game_play is None:
            game_play = self._resolve_running_game(gid)
        if game_play is None:
            return

        g_session = SpectatorStateSerializer.resolve_active_game_session(game_play)
        g_type = SpectatorStateSerializer.resolve_active_game_type(game_play, g_session)

        sanitized_cmd = SpectatorStateSerializer.sanitize_live_command(g_type, command)
        if sanitized_cmd is None:
            return

        board_state = SpectatorStateSerializer.extract_board_state(g_session)
        current_turn = SpectatorStateSerializer.extract_current_turn(g_session, board_state)
        timer_data = SpectatorStateSerializer.extract_timer_data(g_session)
        gamers = SpectatorStateSerializer.build_gamers_payload(game_play, g_session)
        scores_map = {str(g["id"]): int(g.get("match_score", 0)) for g in gamers}

        state_cmd = make_command_json(
            id=commands.SpectatorGameState,
            data={
                "game_id": gid,
                "game_type": g_type,
                "event_type": "game_command",
                "event_command": sanitized_cmd,
                "command": sanitized_cmd,
                "current_turn": current_turn,
                "scores": scores_map,
                "gamers": gamers,
                "board_state": board_state,
                "game_data": board_state,
                "timer_data": timer_data,
                "spectator_count": self.get_spectator_count(gid),
                "server_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            },
        )
        await SpectatorRoomManager.broadcast_to_spectators(gid, state_cmd)

    async def on_game_reaction(self, game_id: str, player_id: int, reaction_id: int) -> None:
        gid = str(game_id or "")
        if not gid or not self.game_spectators.get(gid):
            return

        state_cmd = make_command_json(
            id=commands.SpectatorGameState,
            data={
                "game_id": gid,
                "event_type": "reaction",
                "reaction": {
                    "player_id": player_id,
                    "reaction_id": reaction_id,
                    "playerId": player_id,
                    "reactionId": reaction_id,
                },
                "spectator_count": self.get_spectator_count(gid),
                "server_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            },
        )
        await SpectatorRoomManager.broadcast_to_spectators(gid, state_cmd)

    async def on_subgame_started(self, game_play) -> None:
        """
        Called when `BaseGamePlayClass.start_current_game` starts or transitions to a sub-game.
        Updates DB metadata and sends a fresh snapshot to any connected spectators.
        If the new sub-game is a hidden-information game, gracefully ends spectating for that match.
        """
        if game_play is None:
            return
        gid = str(getattr(game_play, "game_play_id", "") or "")
        self.sync_live_match_metadata(game_play, is_running=True)
        if not gid or not self.game_spectators.get(gid):
            return

        g_session = SpectatorStateSerializer.resolve_active_game_session(game_play)
        g_type = SpectatorStateSerializer.resolve_active_game_type(game_play, g_session)
        is_safe, unsafe_msg = SpectatorStateSerializer.is_game_spectatable(g_type)
        if not is_safe:
            await self.on_game_ended(
                gid,
                game_play=game_play,
                reason="unsafe_subgame",
                message=unsafe_msg,
            )
            return

        snapshot = SpectatorStateSerializer.serialize_snapshot(
            game_id=gid,
            game_play=game_play,
            game_session=g_session,
            spectator_count=self.get_spectator_count(gid),
        )
        snapshot["event_type"] = "subgame_started"
        await SpectatorRoomManager.broadcast_to_spectators(
            gid,
            make_command_json(id=commands.SpectatorGameState, data=snapshot),
        )

    async def on_game_ended(
        self,
        game_id: str,
        game_play=None,
        final_payload: dict | None = None,
        reason: str = "finished",
        message: str = "مسابقه به پایان رسید.",
    ) -> None:
        """
        Broadcast `SpectatorGameEnded` to all spectators of `game_id` and clean up all rooms & sessions.
        """
        gid = str(game_id or "")
        if not gid:
            return

        if game_play is None:
            game_play = self._resolve_running_game(gid)

        gamers = []
        scores_map = {}
        winner_ids = []
        winner_user_id = None
        if game_play is not None:
            g_session = SpectatorStateSerializer.resolve_active_game_session(game_play)
            gamers = SpectatorStateSerializer.build_gamers_payload(game_play, g_session)
            scores_map = {str(g["id"]): int(g.get("match_score", 0)) for g in gamers}
            winner_ids = list(getattr(game_play, "game_winners", []) or [])
            winner_user_id = getattr(game_play, "game_winner_id", None)

        users_map = self.game_spectators.pop(gid, {})

        end_cmd = make_command_json(
            id=commands.SpectatorGameEnded,
            data={
                "game_id": gid,
                "reason": reason,
                "message": message,
                "gamers": gamers,
                "scores": scores_map,
                "winners": winner_ids,
                "game_winner_id": winner_user_id,
                "final_data": SpectatorStateSerializer.strip_private_fields(final_payload or {}),
                "server_time": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            },
        )
        if users_map:
            await SpectatorRoomManager.broadcast_to_spectators(gid, end_cmd)

        for uid, sids in users_map.items():
            if self.user_spectating_game.get(uid) == gid:
                self.user_spectating_game.pop(uid, None)
            for s in list(sids):
                info = self.sid_registry.pop(s, None)
                ns = str((info or {}).get("namespace", "/social"))
                await SpectatorRoomManager.leave_spectator_room(s, gid, namespace=ns)
            try:
                if hasattr(game_database, "presence_manager"):
                    game_database.presence_manager.update_activity(
                        user_id=uid,
                        status="online",
                        current_game_id="",
                        current_game_type="",
                    )
            except Exception:
                pass

        col = self._get_history_collection()
        if col is not None:
            try:
                col.update_one(
                    {"_id": gid},
                    {
                        "$set": {
                            "spectator_count": 0,
                            "is_running": False,
                            "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        }
                    },
                )
            except Exception:
                pass

    @staticmethod
    def _resolve_running_game(game_id: str):
        try:
            from Entities.SocketIOClass.game import games
            return games.get(str(game_id))
        except Exception:
            return None


spectator_session_manager = SpectatorSessionManager()
