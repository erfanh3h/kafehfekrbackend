"""
SpectatorController
Handles all incoming client spectator commands:
- RequestSpectate (and aliases SocialSpectateJoin, SocialSpectateRequest)
- LeaveSpectate (and alias SocialSpectateLeave)
- RequestSpectatorState (for spectator reconnect / manual resync)
"""

from Commons import commands
from Commons.static_functions import make_command_json
from Controllers.Spectator.spectator_access_manager import SpectatorAccessManager
from Controllers.Spectator.spectator_room_manager import SpectatorRoomManager
from Controllers.Spectator.spectator_session_manager import spectator_session_manager
from Controllers.Spectator.spectator_state_serializer import SpectatorStateSerializer
from Entities.Database import game_database


class SpectatorController:
    def __init__(self, session_manager=None):
        self.session_manager = session_manager or spectator_session_manager

    def _resolve_running_game_and_active_player_game(self, viewer_id: str, target_game_id: str):
        running_game = None
        active_player_game_id = None
        try:
            from Entities.SocketIOClass.game import games
            running_game = games.get(str(target_game_id))
            for gid, gp in list(games.items()):
                if gp is None:
                    continue
                is_fin = bool(
                    getattr(gp, "is_game_finished", False)
                    or getattr(gp, "is_finished", False)
                    or getattr(gp, "is_game_terminated", False)
                )
                if is_fin:
                    continue
                pids = SpectatorStateSerializer.extract_participant_ids(gp)
                if str(viewer_id) in pids:
                    active_player_game_id = str(gid)
                    break
        except Exception:
            pass
        return running_game, active_player_game_id

    def _load_public_profiles(self, user_ids: list[str]) -> dict[str, dict]:
        profiles = {}
        for uid in user_ids:
            uid_str = str(uid or "")
            if not uid_str or uid_str.startswith("bot_") or uid_str.startswith("test_bot"):
                continue
            try:
                u_doc = SpectatorAccessManager._read_user_doc(uid_str)
                if isinstance(u_doc, dict):
                    clan_info = None
                    try:
                        cm = game_database.clans_manager
                        if hasattr(cm, "get_user_membership"):
                            mem = cm.get_user_membership(uid_str)
                            if mem and mem.get("clan_id"):
                                c_doc = cm.read_clan(str(mem["clan_id"])) if hasattr(cm, "read_clan") else None
                                if isinstance(c_doc, dict):
                                    clan_info = {
                                        "clan_id": str(c_doc.get("_id", mem["clan_id"])),
                                        "name": str(c_doc.get("name", "")),
                                        "tag": str(c_doc.get("tag", "")),
                                        "emblem_id": int(c_doc.get("emblem_id", 1) or 1),
                                    }
                    except Exception:
                        clan_info = None
                    profiles[uid_str] = {
                        "user_id": uid_str,
                        "username": u_doc.get("username", "بازیکن"),
                        "image": int(u_doc.get("image", u_doc.get("avatar", 0)) or 0),
                        "profile_frame": int(u_doc.get("profile_frame", 0) or 0),
                        "profile_title": str(u_doc.get("profile_title", "") or ""),
                        "score": int(u_doc.get("score", 0) or 0),
                        "xp": int(u_doc.get("xp", 0) or 0),
                        "clan": clan_info,
                    }
            except Exception:
                pass
        return profiles

    async def handle_request_spectate(
        self,
        viewer_id: str,
        sid: str,
        payload: dict,
        namespace: str = "/social",
        presence_callback=None,
    ) -> dict:
        uid = str(viewer_id or "").strip()
        if not self.session_manager.check_rate_limit(uid, "spectate_join", limit=10, window_sec=10.0):
            rej = make_command_json(
                id=commands.SpectateRejected,
                data={
                    "game_id": str((payload or {}).get("game_id", "")),
                    "reason": "rate_limited",
                    "message": "تعداد درخواست‌های شما بیش از حد مجاز است. چند ثانیه صبر کنید.",
                },
            )
            await SpectatorRoomManager.emit_to_spectator(sid, rej, namespace=namespace)
            return rej

        game_id = str((payload or {}).get("game_id", "")).strip()
        target_player_id = str((payload or {}).get("player_id", (payload or {}).get("user_id", ""))).strip()
        if not game_id and target_player_id:
            try:
                from Entities.SocketIOClass.game import games
                for gid, gp in list(games.items()):
                    if gp and not getattr(gp, "is_game_finished", False) and not getattr(gp, "is_finished", False):
                        if target_player_id in SpectatorStateSerializer.extract_participant_ids(gp):
                            game_id = str(gid)
                            break
            except Exception:
                pass

        running_game, active_player_game_id = self._resolve_running_game_and_active_player_game(uid, game_id)
        current_count = self.session_manager.get_spectator_count(game_id)
        if self.session_manager.is_user_spectating(uid, game_id):
            current_count = max(0, current_count - 1)

        allowed, reason_code, msg_fa = SpectatorAccessManager.check_can_spectate(
            viewer_id=uid,
            game_id=game_id,
            game_play=running_game,
            current_spectator_count=current_count,
            active_player_game_id=active_player_game_id,
        )

        if not allowed:
            rej = make_command_json(
                id=commands.SpectateRejected,
                data={
                    "game_id": game_id,
                    "reason": reason_code,
                    "message": msg_fa,
                },
            )
            await SpectatorRoomManager.emit_to_spectator(sid, rej, namespace=namespace)
            await SpectatorRoomManager.emit_to_spectator(
                sid,
                make_command_json(id=commands.Social_Error, data={"message": msg_fa, "reason": reason_code}),
                namespace=namespace,
            )
            return rej

        new_count = await self.session_manager.add_spectator(uid, sid, game_id, namespace=namespace)
        g_session = SpectatorStateSerializer.resolve_active_game_session(running_game)
        participant_ids = SpectatorStateSerializer.extract_participant_ids(running_game)
        user_profiles = self._load_public_profiles(participant_ids)
        snapshot = SpectatorStateSerializer.serialize_snapshot(
            game_id=game_id,
            game_play=running_game,
            game_session=g_session,
            spectator_count=new_count,
            user_profiles=user_profiles,
        )

        g_type = str(snapshot.get("game_type", ""))
        try:
            if hasattr(game_database, "presence_manager"):
                pres = game_database.presence_manager.update_activity(
                    user_id=uid,
                    status="spectating",
                    current_game_id=game_id,
                    current_game_type=g_type,
                )
                if callable(presence_callback) and isinstance(pres, dict):
                    await presence_callback(uid, pres)
        except Exception:
            pass

        accepted_cmd = make_command_json(
            id=commands.SpectateAccepted,
            data=snapshot,
        )
        await SpectatorRoomManager.emit_to_spectator(sid, accepted_cmd, namespace=namespace)

        state_cmd = make_command_json(
            id=commands.SpectatorGameState,
            data={
                **snapshot,
                "event_type": "initial_snapshot",
            },
        )
        await SpectatorRoomManager.emit_to_spectator(sid, state_cmd, namespace=namespace)
        await SpectatorRoomManager.emit_to_spectator(
            sid,
            make_command_json(id=commands.Social_Spectate_Data, data=snapshot),
            namespace=namespace,
        )
        return accepted_cmd

    async def handle_leave_spectate(
        self,
        viewer_id: str,
        sid: str,
        payload: dict | None = None,
        namespace: str = "/social",
        presence_callback=None,
    ) -> dict:
        uid = str(viewer_id or "").strip()
        req_gid = str((payload or {}).get("game_id", "")).strip()

        _, removed_gid, count = await self.session_manager.remove_spectator_by_sid(sid)
        target_gid = removed_gid or req_gid
        if uid and self.session_manager.is_user_spectating(uid, target_gid):
            count = await self.session_manager.remove_spectator_by_user(uid, target_gid)

        try:
            if hasattr(game_database, "presence_manager"):
                pres = game_database.presence_manager.update_activity(
                    user_id=uid,
                    status="online",
                    current_game_id="",
                    current_game_type="",
                )
                if callable(presence_callback) and isinstance(pres, dict):
                    await presence_callback(uid, pres)
        except Exception:
            pass

        ack = make_command_json(
            id=commands.Social_Ack,
            data={
                "action": "spectate_left",
                "game_id": target_gid,
                "spectator_count": count,
            },
        )
        await SpectatorRoomManager.emit_to_spectator(sid, ack, namespace=namespace)
        return ack

    async def handle_request_spectator_state(
        self,
        viewer_id: str,
        sid: str,
        payload: dict | None = None,
        namespace: str = "/social",
    ) -> dict:
        uid = str(viewer_id or "").strip()
        if not self.session_manager.check_rate_limit(uid, "spectate_state", limit=20, window_sec=10.0):
            return make_command_json(id=commands.SpectateRejected, data={"reason": "rate_limited"})

        game_id = str((payload or {}).get("game_id", "")).strip()
        if not game_id:
            game_id = str(
                self.session_manager.get_spectated_game_for_sid(sid)
                or self.session_manager.get_spectated_game_for_user(uid)
                or ""
            )

        running_game, _ = self._resolve_running_game_and_active_player_game(uid, game_id)
        is_fin = bool(
            running_game is None
            or getattr(running_game, "is_game_finished", False)
            or getattr(running_game, "is_finished", False)
            or getattr(running_game, "is_game_terminated", False)
        )
        if is_fin:
            ended = make_command_json(
                id=commands.SpectatorGameEnded,
                data={
                    "game_id": game_id,
                    "reason": "match_finished",
                    "message": "این مسابقه به پایان رسیده است.",
                },
            )
            await SpectatorRoomManager.emit_to_spectator(sid, ended, namespace=namespace)
            return ended

        if not self.session_manager.is_user_spectating(uid, game_id):
            return await self.handle_request_spectate(uid, sid, {"game_id": game_id}, namespace=namespace)

        await SpectatorRoomManager.join_spectator_room(sid, game_id, namespace=namespace)
        g_session = SpectatorStateSerializer.resolve_active_game_session(running_game)
        participant_ids = SpectatorStateSerializer.extract_participant_ids(running_game)
        user_profiles = self._load_public_profiles(participant_ids)
        snapshot = SpectatorStateSerializer.serialize_snapshot(
            game_id=game_id,
            game_play=running_game,
            game_session=g_session,
            spectator_count=self.session_manager.get_spectator_count(game_id),
            user_profiles=user_profiles,
        )
        state_cmd = make_command_json(
            id=commands.SpectatorGameState,
            data={
                **snapshot,
                "event_type": "resync_snapshot",
            },
        )
        await SpectatorRoomManager.emit_to_spectator(sid, state_cmd, namespace=namespace)
        return state_cmd

    async def handle_disconnect(self, sid: str) -> None:
        await self.session_manager.remove_spectator_by_sid(sid)


spectator_controller = SpectatorController(spectator_session_manager)
