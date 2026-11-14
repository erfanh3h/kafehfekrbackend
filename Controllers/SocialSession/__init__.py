from datetime import datetime
import re
import time
from Commons import commands
from Commons.static_functions import make_command_json, create_random_name
from Entities.Database import game_database
from Entities.Database.social.clans_collection import CLAN_ROLE_RANK


# Games where players have NO secret hands/private hidden grids -> Safe for live spectators!
SAFE_SPECTATOR_GAMES = {
    "chess",
    "checkers",
    "othello",
    "fourinrow",
    "mill",
    "pentago",
    "quoridor",
    "backgammon",
    "ludo",
    "tictactoe",
    "boxfour",
    "dotbox",
    "yinsh",
    "yatzy",
    "monopoly",
    "risk",
}

# Games with secret private state (hidden ships, hidden mines, secret cards/influence, secret code) -> Never expose to spectators!
PRIVATE_STATE_GAMES = {
    "battleship",
    "sudoku",
    "msweeper",
    "mnumbers",
    "fekrbekr",
    "uno",
    "coup",
    "quiz",
    "rpc",
}


class SocialSessionManager:
    """Real-time session coordinator for the /social Socket.IO namespace."""

    def __init__(self):
        # socket_id -> user_id
        self.socket_to_user: dict[str, str] = {}
        # user_id -> set of active socket_ids on /social
        self.user_to_sockets: dict[str, set[str]] = {}
        # user_id -> clan_id currently joined as room
        self.user_clan_room: dict[str, str] = {}
        # rate limiter per (user_id, action)
        self._rate_buckets: dict[tuple[str, str], list[float]] = {}

    def _check_rate(self, user_id: str, action: str, max_calls: int = 25, window_sec: float = 60.0) -> bool:
        now = time.time()
        key = (str(user_id), str(action))
        bucket = [t for t in self._rate_buckets.get(key, []) if now - t < window_sec]
        if len(bucket) >= max_calls:
            return False
        bucket.append(now)
        self._rate_buckets[key] = bucket
        return True

    def _serialize_dt(self, val) -> str:
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val or "")

    async def connect_user(self, socket_id: str, user_data: dict, namespace_obj) -> None:
        uid = str(user_data["_id"])
        self.socket_to_user[socket_id] = uid
        if uid not in self.user_to_sockets:
            self.user_to_sockets[uid] = set()
        was_offline = len(self.user_to_sockets[uid]) == 0
        self.user_to_sockets[uid].add(socket_id)

        await namespace_obj.enter_room(socket_id, f"user_{uid}", namespace="/social")

        mem = game_database.clans_manager.get_user_membership(uid)
        clan_id = str(mem["clan_id"]) if mem else ""
        if clan_id:
            self.user_clan_room[uid] = clan_id
            await namespace_obj.enter_room(socket_id, f"clan_{clan_id}", namespace="/social")

        open_gid = str(user_data.get("open_game_id", "") or "")
        initial_status = "in_game" if open_gid else "online"
        pres = game_database.presence_manager.update_presence(
            user_id=uid,
            status=initial_status,
            current_game_id=open_gid,
            socket_id=socket_id,
            add_socket=True,
        )

        # Send initial social sync payload to the connected client
        unread_notifs = game_database.notifications_manager.get_unread_count(uid)
        unread_dms = game_database.direct_messages_manager.get_total_unread_count(uid)
        active_invites = game_database.invitations_manager.get_incoming_invitations(uid)
        await namespace_obj.emit(
            "command",
            make_command_json(
                id=commands.Social_Init,
                data={
                    "user_id": uid,
                    "clan_id": clan_id,
                    "status": pres.get("status", "online"),
                    "unread_notifications": unread_notifs,
                    "unread_dms": unread_dms,
                    "active_invitations_count": len(active_invites),
                },
            ),
            to=socket_id,
            namespace="/social",
        )

        if was_offline:
            await self.broadcast_presence_to_peers(uid, pres, namespace_obj)

    async def disconnect_user(self, socket_id: str, namespace_obj) -> None:
        uid = self.socket_to_user.pop(socket_id, None)
        if not uid:
            return
        try:
            await namespace_obj.leave_room(socket_id, f"user_{uid}", namespace="/social")
        except Exception:
            pass
        cid = self.user_clan_room.get(uid, "")
        if cid:
            try:
                await namespace_obj.leave_room(socket_id, f"clan_{cid}", namespace="/social")
            except Exception:
                pass

        sockets = self.user_to_sockets.get(uid, set())
        sockets.discard(socket_id)
        if not sockets:
            self.user_to_sockets.pop(uid, None)
            self.user_clan_room.pop(uid, None)
            u_doc = game_database.users_manager.read_user(uid) or {}
            open_gid = str(u_doc.get("open_game_id", "") or "")
            new_st = "in_game" if open_gid else "offline"
            pres = game_database.presence_manager.update_presence(
                user_id=uid,
                status=new_st,
                current_game_id=open_gid,
                socket_id=socket_id,
                add_socket=False,
            )
            await self.broadcast_presence_to_peers(uid, pres, namespace_obj)
        else:
            game_database.presence_manager.update_presence(
                user_id=uid,
                status="online",
                socket_id=socket_id,
                add_socket=False,
            )

    async def broadcast_presence_to_peers(self, user_id: str, presence_doc: dict, namespace_obj) -> None:
        uid = str(user_id)
        u_doc = game_database.users_manager.read_user(uid) or {}
        priv = u_doc.get("privacy") if isinstance(u_doc.get("privacy"), dict) else {}
        show_game = bool(priv.get("show_current_game", True))
        show_last_seen = bool(priv.get("show_last_seen", True))

        payload = {
            "user_id": uid,
            "username": str(u_doc.get("username", "بازیکن")),
            "image": int(u_doc.get("image", 0) or 0),
            "status": str(presence_doc.get("status", "offline")),
            "current_game_type": str(presence_doc.get("current_game_type", "")) if show_game else "",
            "current_game_id": str(presence_doc.get("current_game_id", "")) if show_game else "",
            "current_lobby_id": str(presence_doc.get("current_lobby_id", "")) if show_game else "",
            "last_seen": self._serialize_dt(presence_doc.get("last_seen")) if show_last_seen else "",
        }
        cmd = make_command_json(id=commands.Social_Presence_Changed, data=payload)

        # Emit to online friends
        friend_ids = game_database.friends_manager.get_friend_ids(uid)
        for fid in friend_ids:
            if fid in self.user_to_sockets:
                await namespace_obj.emit("command", cmd, room=f"user_{fid}", namespace="/social")

        # Emit to clan room if member of a clan
        mem = game_database.clans_manager.get_user_membership(uid)
        if mem and mem.get("clan_id"):
            await namespace_obj.emit("command", cmd, room=f"clan_{mem['clan_id']}", namespace="/social")

    async def handle_command(self, socket_id: str, data: dict, namespace_obj) -> None:
        if not isinstance(data, dict):
            return
        uid = self.socket_to_user.get(socket_id)
        if not uid:
            return
        cmd_id = str(data.get("id", ""))
        payload = data.get("data", {})
        if not isinstance(payload, dict):
            payload = {}

        u_doc = game_database.users_manager.read_user(uid)
        if not u_doc:
            return

        # 1. Presence Update
        if cmd_id == commands.Social_Presence_Update:
            st = str(payload.get("status", "online"))
            g_type = str(payload.get("current_game_type", ""))
            g_id = str(payload.get("current_game_id", ""))
            l_id = str(payload.get("current_lobby_id", ""))
            pres = game_database.presence_manager.update_presence(
                user_id=uid,
                status=st,
                current_game_type=g_type,
                current_game_id=g_id,
                current_lobby_id=l_id,
                socket_id=socket_id,
                add_socket=True,
            )
            # Refresh clan room membership if user recently joined/left a clan
            mem = game_database.clans_manager.get_user_membership(uid)
            new_cid = str(mem["clan_id"]) if mem else ""
            old_cid = self.user_clan_room.get(uid, "")
            if old_cid and old_cid != new_cid:
                await namespace_obj.leave_room(socket_id, f"clan_{old_cid}", namespace="/social")
            if new_cid and new_cid != old_cid:
                self.user_clan_room[uid] = new_cid
                await namespace_obj.enter_room(socket_id, f"clan_{new_cid}", namespace="/social")
            await self.broadcast_presence_to_peers(uid, pres, namespace_obj)
            return

        # 2. Direct Message Send
        if cmd_id == commands.Social_DM_Send:
            if not self._check_rate(uid, "dm_send", 30, 60.0):
                await self._send_error(socket_id, "تعداد پیام‌های ارسالی بیش از حد مجاز است.", namespace_obj)
                return
            to_id = str(payload.get("to_user_id", "")).strip()
            text = str(payload.get("text", "")).strip()[:500]
            if not to_id or to_id == uid or not text:
                return
            if game_database.friends_manager.is_blocked(uid, to_id):
                await self._send_error(socket_id, "امکان ارسال پیام به این بازیکن وجود ندارد.", namespace_obj)
                return
            target_u = game_database.users_manager.read_user(to_id)
            if not target_u:
                return
            priv = target_u.get("privacy") if isinstance(target_u.get("privacy"), dict) else {}
            dm_policy = str(priv.get("allow_dms", "everyone"))
            if dm_policy == "none" or (dm_policy == "friends" and not game_database.friends_manager.are_friends(uid, to_id)):
                await self._send_error(socket_id, "این بازیکن دریافت پیام خصوصی را محدود کرده است.", namespace_obj)
                return

            msg_doc = game_database.direct_messages_manager.create_direct_message(uid, to_id, text)
            formatted = {
                "message_id": str(msg_doc["_id"]),
                "conversation_id": str(msg_doc["conversation_id"]),
                "from_user_id": uid,
                "from_username": str(u_doc.get("username", "بازیکن")),
                "from_image": int(u_doc.get("image", 0) or 0),
                "to_user_id": to_id,
                "text": text,
                "is_read": False,
                "created_at": self._serialize_dt(msg_doc.get("created_at")),
            }
            ev = make_command_json(id=commands.Social_DM_Received, data=formatted)
            await namespace_obj.emit("command", ev, room=f"user_{uid}", namespace="/social")
            await namespace_obj.emit("command", ev, room=f"user_{to_id}", namespace="/social")
            return

        # 3. Direct Message Mark Read
        if cmd_id == commands.Social_DM_Read:
            partner_id = str(payload.get("partner_id", "")).strip()
            if partner_id:
                game_database.direct_messages_manager.mark_conversation_read(uid, partner_id)
                await namespace_obj.emit(
                    "command",
                    make_command_json(
                        id=commands.Social_DM_Read,
                        data={"reader_id": uid, "partner_id": partner_id},
                    ),
                    room=f"user_{partner_id}",
                    namespace="/social",
                )
            return

        # 4. Clan Chat Send
        if cmd_id == commands.Social_Clan_Chat_Send:
            if not self._check_rate(uid, "clan_chat", 30, 60.0):
                await self._send_error(socket_id, "ارسال پیام بیش از حد سریع است.", namespace_obj)
                return
            mem = game_database.clans_manager.get_user_membership(uid)
            if not mem:
                await self._send_error(socket_id, "شما عضو هیچ کلنی نیستید.", namespace_obj)
                return
            cid = str(mem["clan_id"])
            text = str(payload.get("text", "")).strip()[:500]
            if not text:
                return
            await namespace_obj.enter_room(socket_id, f"clan_{cid}", namespace="/social")
            self.user_clan_room[uid] = cid
            mentions = re.findall(r"@([A-Za-z0-9_\u0600-\u06FF]+)", text)
            msg_doc = game_database.clan_messages_manager.create_message(
                clan_id=cid,
                sender_id=uid,
                sender_name=str(u_doc.get("username", "بازیکن")),
                sender_image=int(u_doc.get("image", 0) or 0),
                sender_role=str(mem.get("role", "member")),
                text=text,
                msg_type="text",
                mentions=mentions[:5],
            )
            formatted = {
                "message_id": str(msg_doc["_id"]),
                "clan_id": cid,
                "sender_id": uid,
                "sender_name": str(u_doc.get("username", "بازیکن")),
                "sender_image": int(u_doc.get("image", 0) or 0),
                "sender_role": str(mem.get("role", "member")),
                "text": text,
                "msg_type": "text",
                "mentions": mentions[:5],
                "created_at": self._serialize_dt(msg_doc.get("created_at")),
            }
            await namespace_obj.emit(
                "command",
                make_command_json(id=commands.Social_Clan_Chat_Received, data=formatted),
                room=f"clan_{cid}",
                namespace="/social",
            )
            return

        # 5. Clan Chat Moderator Delete
        if cmd_id == commands.Social_Clan_Chat_Delete:
            mem = game_database.clans_manager.get_user_membership(uid)
            if not mem:
                return
            cid = str(mem["clan_id"])
            msg_id = str(payload.get("message_id", "")).strip()
            msg = game_database.clan_messages_manager.read_message(msg_id)
            if not msg or str(msg.get("clan_id")) != cid:
                return
            role_rank = CLAN_ROLE_RANK.get(str(mem.get("role", "member")), 1)
            if str(msg.get("sender_id")) != uid and role_rank < CLAN_ROLE_RANK["elder"]:
                await self._send_error(socket_id, "مجاز به حذف این پیام نیستید.", namespace_obj)
                return
            game_database.clan_messages_manager.delete_message(msg_id, uid)
            await namespace_obj.emit(
                "command",
                make_command_json(
                    id=commands.Social_Clan_Chat_Delete,
                    data={"clan_id": cid, "message_id": msg_id, "deleted_by": uid},
                ),
                room=f"clan_{cid}",
                namespace="/social",
            )
            return

        # 6. Multiplayer Game / Lobby Invitation Send
        if cmd_id == commands.Social_Game_Invite_Send:
            if not self._check_rate(uid, "game_invite", 15, 60.0):
                await self._send_error(socket_id, "لطفاً قبل از ارسال دعوت‌نامه بعدی کمی صبر کنید.", namespace_obj)
                return
            to_id = str(payload.get("to_user_id", "")).strip()
            game_type = str(payload.get("game_type", "Ludo") or "Ludo")
            invite_mode = str(payload.get("invite_mode", "lobby") or "lobby")
            lobby_id = str(payload.get("lobby_id", "") or "")
            lobby_password = str(payload.get("lobby_password", "") or "")
            player_count = max(2, min(int(payload.get("player_count", 2) or 2), 4))

            if not to_id or to_id == uid or game_database.friends_manager.is_blocked(uid, to_id):
                await self._send_error(socket_id, "امکان دعوت این بازیکن وجود ندارد.", namespace_obj)
                return

            are_friends = game_database.friends_manager.are_friends(uid, to_id)
            my_mem = game_database.clans_manager.get_user_membership(uid)
            th_mem = game_database.clans_manager.get_user_membership(to_id)
            same_clan = (
                my_mem is not None
                and th_mem is not None
                and str(my_mem.get("clan_id")) == str(th_mem.get("clan_id"))
            )
            if not are_friends and not same_clan:
                await self._send_error(socket_id, "فقط دوستان یا هم‌کلنی‌های خود را می‌توانید دعوت کنید.", namespace_obj)
                return

            target_u = game_database.users_manager.read_user(to_id)
            if not target_u:
                await self._send_error(socket_id, "بازیکن یافت نشد.", namespace_obj)
                return
            if str(target_u.get("open_game_id", "") or ""):
                await self._send_error(socket_id, "این بازیکن در حال حاضر در یک مسابقه فعال حضور دارد.", namespace_obj)
                return

            # Validate lobby if lobby_id provided
            if lobby_id:
                from Entities.SocketIOClass.lobby import lobby_session
                lob = lobby_session.find_lobby_from_id(lobby_id)
                if lob is None:
                    await self._send_error(socket_id, "لابی مورد نظر دیگر فعال نیست.", namespace_obj)
                    return
                if len(lob.queuers) >= int(lob.lobby_count):
                    await self._send_error(socket_id, "ظرفیت لابی تکمیل شده است.", namespace_obj)
                    return
                game_type = str(lob.lobby_game_type)
                lobby_password = str(lob.lobby_password or "")
                player_count = int(lob.lobby_count)

            inv_doc = game_database.invitations_manager.create_invitation(
                from_user_id=uid,
                from_username=str(u_doc.get("username", "بازیکن")),
                from_image=int(u_doc.get("image", 0) or 0),
                to_user_id=to_id,
                invite_mode=invite_mode,
                game_type=game_type,
                lobby_id=lobby_id,
                lobby_password=lobby_password,
                player_count=player_count,
                clan_id=str(my_mem["clan_id"]) if same_clan else "",
            )
            inv_payload = {
                "invite_id": str(inv_doc["_id"]),
                "from_user_id": uid,
                "from_username": str(u_doc.get("username", "بازیکن")),
                "from_image": int(u_doc.get("image", 0) or 0),
                "to_user_id": to_id,
                "invite_mode": invite_mode,
                "game_type": game_type,
                "lobby_id": lobby_id,
                "lobby_password": lobby_password,
                "player_count": player_count,
                "status": "pending",
                "expires_at": self._serialize_dt(inv_doc.get("expires_at")),
            }
            game_database.notifications_manager.create_notification(
                user_id=to_id,
                notif_type="game_invitation_received",
                title="🎮 دعوت به بازی",
                body=f"{u_doc.get('username', 'بازیکن')} شما را به بازی «{game_type}» دعوت کرد!",
                actor_id=uid,
                actor_name=str(u_doc.get("username", "بازیکن")),
                actor_image=int(u_doc.get("image", 0) or 0),
                payload=inv_payload,
                category="game_invitations",
            )
            await namespace_obj.emit(
                "command",
                make_command_json(id=commands.Social_Game_Invite_Received, data=inv_payload),
                room=f"user_{to_id}",
                namespace="/social",
            )
            await namespace_obj.emit(
                "command",
                make_command_json(id=commands.Social_Game_Invite_Result, data={"sent": True, **inv_payload}),
                to=socket_id,
                namespace="/social",
            )
            return

        # 7. Multiplayer Game / Lobby Invitation Respond
        if cmd_id == commands.Social_Game_Invite_Respond:
            invite_id = str(payload.get("invite_id", "")).strip()
            action = str(payload.get("action", "accept")).strip().lower()
            inv = game_database.invitations_manager.read_invitation(invite_id)
            if not inv or str(inv.get("to_user_id")) != uid or inv.get("status") != "pending":
                await self._send_error(socket_id, "این دعوت‌نامه منقضی شده یا معتبر نیست.", namespace_obj)
                return

            from_id = str(inv.get("from_user_id", ""))
            if action != "accept":
                game_database.invitations_manager.update_status(invite_id, "rejected")
                rej_payload = {
                    "invite_id": invite_id,
                    "status": "rejected",
                    "from_user_id": from_id,
                    "to_user_id": uid,
                    "to_username": str(u_doc.get("username", "بازیکن")),
                }
                await namespace_obj.emit(
                    "command",
                    make_command_json(id=commands.Social_Game_Invite_Result, data=rej_payload),
                    room=f"user_{from_id}",
                    namespace="/social",
                )
                await namespace_obj.emit(
                    "command",
                    make_command_json(id=commands.Social_Game_Invite_Result, data=rej_payload),
                    to=socket_id,
                    namespace="/social",
                )
                return

            # Accepted! Validate lobby or create direct friendly match
            lobby_id = str(inv.get("lobby_id", "") or "")
            game_type = str(inv.get("game_type", "Ludo") or "Ludo")
            lobby_password = str(inv.get("lobby_password", "") or "")
            created_game_id = ""

            if lobby_id:
                from Entities.SocketIOClass.lobby import lobby_session
                lob = lobby_session.find_lobby_from_id(lobby_id)
                if lob is None:
                    game_database.invitations_manager.update_status(invite_id, "expired")
                    await self._send_error(socket_id, "لابی مورد نظر دیگر وجود ندارد.", namespace_obj)
                    return
                if len(lob.queuers) >= int(lob.lobby_count):
                    await self._send_error(socket_id, "ظرفیت این لابی تکمیل شده است.", namespace_obj)
                    return
            else:
                # Direct 1v1 friendly match creation using existing authoritative game engine!
                from_u = game_database.users_manager.read_user(from_id)
                if not from_u or str(from_u.get("open_game_id", "") or ""):
                    await self._send_error(socket_id, "دعوت‌کننده در حال حاضر در بازی دیگری حضور دارد.", namespace_obj)
                    return
                from Models.Queuer import QueuerModel
                from Entities.SocketIOClass.game import add_new_game
                from Entities.RewardManagerClass.game_score_types import GameScoreTypesEnum

                q1 = QueuerModel(
                    user_id=from_id,
                    username=str(from_u.get("username", "بازیکن ۱")),
                    socket_id="",
                    user_image=int(from_u.get("image", 0) or 0),
                    user_coin=int(from_u.get("coin", 0) or 0),
                    user_score=int(from_u.get("score", 0) or 0),
                    user_xp=int(from_u.get("xp", 0) or 0),
                )
                q2 = QueuerModel(
                    user_id=uid,
                    username=str(u_doc.get("username", "بازیکن ۲")),
                    socket_id="",
                    user_image=int(u_doc.get("image", 0) or 0),
                    user_coin=int(u_doc.get("coin", 0) or 0),
                    user_score=int(u_doc.get("score", 0) or 0),
                    user_xp=int(u_doc.get("xp", 0) or 0),
                )
                created_game_id = f"frg_{create_random_name()}"
                game_database.users_manager.update_user(from_id, open_game_id=created_game_id)
                game_database.users_manager.update_user(uid, open_game_id=created_game_id)
                add_new_game(created_game_id, [q1, q2], [game_type], GameScoreTypesEnum.LOBBY)

            game_database.invitations_manager.update_status(
                invite_id, "accepted", {"game_id": created_game_id}
            )
            acc_payload = {
                "invite_id": invite_id,
                "status": "accepted",
                "from_user_id": from_id,
                "to_user_id": uid,
                "to_username": str(u_doc.get("username", "بازیکن")),
                "game_type": game_type,
                "lobby_id": lobby_id,
                "lobby_password": lobby_password,
                "game_id": created_game_id,
            }
            await namespace_obj.emit(
                "command",
                make_command_json(id=commands.Social_Game_Invite_Result, data=acc_payload),
                room=f"user_{from_id}",
                namespace="/social",
            )
            await namespace_obj.emit(
                "command",
                make_command_json(id=commands.Social_Game_Invite_Result, data=acc_payload),
                room=f"user_{uid}",
                namespace="/social",
            )
            return

        # 8. Safe Spectator Join / Snapshot
        if cmd_id == commands.Social_Spectate_Join:
            target_uid = str(payload.get("target_user_id", "")).strip()
            req_game_id = str(payload.get("game_id", "")).strip()
            if not req_game_id and target_uid:
                tu = game_database.users_manager.read_user(target_uid) or {}
                req_game_id = str(tu.get("open_game_id", "") or "")
            if not req_game_id:
                await self._send_error(socket_id, "مسابقه فعالی برای تماشا یافت نشد.", namespace_obj)
                return

            from Entities.SocketIOClass.game import games
            game_obj = games.get(req_game_id)
            if game_obj is None:
                await self._send_error(socket_id, "این مسابقه به پایان رسیده است.", namespace_obj)
                return

            # Authorization check: viewer must be a friend or clanmate of at least one participant
            participant_ids = [str( getattr(g, "user_id", "") ) for g in getattr(game_obj, "gamers", [])]
            authorized = False
            my_friends = set(game_database.friends_manager.get_friend_ids(uid))
            my_mem = game_database.clans_manager.get_user_membership(uid)
            my_cid = str(my_mem["clan_id"]) if my_mem else ""
            for pid in participant_ids:
                if not pid or pid.startswith("bot_"):
                    continue
                if game_database.friends_manager.is_blocked(uid, pid):
                    authorized = False
                    break
                if pid in my_friends:
                    authorized = True
                elif my_cid:
                    pmem = game_database.clans_manager.get_user_membership(pid)
                    if pmem and str(pmem.get("clan_id")) == my_cid:
                        authorized = True

            if not authorized:
                await self._send_error(socket_id, "فقط مسابقات دوستان و هم‌کلنی‌های خود را می‌توانید تماشا کنید.", namespace_obj)
                return

            g_session = getattr(game_obj, "game_session", None)
            active_gtype = ""
            if g_session is not None and hasattr(g_session, "game_type"):
                active_gtype = str(getattr(g_session.game_type, "value", g_session.game_type))
            elif getattr(game_obj, "game_types", None):
                active_gtype = str(game_obj.game_types[0])

            gt_lower = active_gtype.lower()
            if gt_lower in PRIVATE_STATE_GAMES or gt_lower not in SAFE_SPECTATOR_GAMES:
                await self._send_error(
                    socket_id,
                    f"بازی «{active_gtype}» دارای اطلاعات مخفی بازیکنان است و امکان تماشای زنده آن وجود ندارد.",
                    namespace_obj,
                )
                return

            gamers_info = []
            for g in getattr(game_obj, "gamers", []):
                gamers_info.append(
                    {
                        "user_id": str(getattr(g, "user_id", "")),
                        "username": str(getattr(g, "username", "بازیکن")),
                        "gamer_id": int(getattr(g, "gamer_id", 1)),
                        "image": int(getattr(g, "user_image", 0) or 0),
                        "score": int(getattr(g, "game_score", 0) or 0),
                    }
                )
            board_state = {}
            if g_session is not None and hasattr(g_session, "get_game_data"):
                try:
                    board_state = g_session.get_game_data()
                except Exception:
                    board_state = {}

            await namespace_obj.emit(
                "command",
                make_command_json(
                    id=commands.Social_Spectate_Data,
                    data={
                        "game_id": req_game_id,
                        "game_type": active_gtype,
                        "gamers": gamers_info,
                        "game_data": board_state,
                    },
                ),
                to=socket_id,
                namespace="/social",
            )
            return

    async def _send_error(self, socket_id: str, message: str, namespace_obj) -> None:
        await namespace_obj.emit(
            "command",
            make_command_json(id=commands.Social_Error, data={"message": message}),
            to=socket_id,
            namespace="/social",
        )


social_session = SocialSessionManager()
