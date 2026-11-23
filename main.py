import os
import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import logging
import time
from datetime import datetime

import socketio
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request

from Commons.static_functions import make_command_json
from Controllers.SocialSession import social_session
from Entities.Security import SECRET_KEY
from Entities.SocketIOClass import Socket_Server
from Entities.Database import game_database

BACKEND_STARTED_AT = time.time()

# Health app for container healthchecks & monitoring
health_app = FastAPI(docs_url=None, redoc_url=None)

@health_app.get("/health")
async def health_check():
    return {"status": "ok", "service": "backend", "uptime_seconds": int(time.time() - BACKEND_STARTED_AT)}

@health_app.get("/")
async def root():
    return {"status": "ok", "service": "backend"}


@health_app.post("/internal/social/emit")
async def internal_social_emit(request: Request, x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    body = await request.json()
    room_updates_before = body.get("room_updates_before", []) or []
    room_updates = body.get("room_updates", []) or []
    events = body.get("events", []) or []

    async def _apply_room_updates(updates):
        for upd in updates:
            if not isinstance(upd, dict):
                continue
            uid = str(upd.get("user_id", "")).strip()
            if not uid:
                continue
            sids = list(social_session.user_to_sockets.get(uid, set()))
            join_cid = str(upd.get("join_clan", "")).strip()
            leave_cid = str(upd.get("leave_clan", "")).strip()
            if leave_cid:
                for sid in sids:
                    try:
                        await Socket_Server.leave_room(sid, f"clan_{leave_cid}", namespace="/social")
                    except Exception:
                        pass
                if social_session.user_clan_room.get(uid) == leave_cid:
                    social_session.user_clan_room.pop(uid, None)
            if join_cid:
                old_cid = social_session.user_clan_room.get(uid, "")
                if old_cid and old_cid != join_cid:
                    for sid in sids:
                        try:
                            await Socket_Server.leave_room(sid, f"clan_{old_cid}", namespace="/social")
                        except Exception:
                            pass
                social_session.user_clan_room[uid] = join_cid
                for sid in sids:
                    try:
                        await Socket_Server.enter_room(sid, f"clan_{join_cid}", namespace="/social")
                    except Exception:
                        pass

    await _apply_room_updates(room_updates_before)

    emitted = 0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        room = str(ev.get("room", "")).strip()
        cmd_id = str(ev.get("command_id", "")).strip()
        data = ev.get("data", {})
        if not room or not cmd_id:
            continue
        try:
            await Socket_Server.emit(
                "command",
                make_command_json(id=cmd_id, data=data),
                room=room,
                namespace="/social",
            )
            emitted += 1
        except Exception as exc:
            print(f"[internal_social_emit] Emit error for {cmd_id} -> {room}: {exc}")

    await _apply_room_updates(room_updates)
    return {"ok": True, "emitted": emitted}


@health_app.get("/internal/user/in-game/{user_id}")
async def internal_check_user_in_game(user_id: str, x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    uid = str(user_id or "").strip()
    if not uid:
        return {"in_game": False, "game_id": ""}
    try:
        from Entities.SocketIOClass.game import games
        from Controllers.Spectator.spectator_state_serializer import SpectatorStateSerializer
        for gid, gp in list(games.items()):
            if gp is None:
                continue
            if getattr(gp, "is_game_finished", False) or getattr(gp, "is_finished", False) or getattr(gp, "is_game_terminated", False):
                continue
            pids = SpectatorStateSerializer.extract_participant_ids(gp)
            if uid not in pids:
                continue
            # If user already surrendered/left a multiplayer match, they are no longer actively playing
            g_sess = getattr(gp, "game_session", None)
            ctrl = getattr(g_sess, "game_controller", None) if g_sess is not None else None
            active_idx = getattr(ctrl, "active_player_indexes", None) if ctrl is not None else None
            if isinstance(active_idx, (list, tuple, set)) and len(active_idx) > 0 and g_sess is not None:
                g_id = g_sess.find_gamer_id_from_user_id(uid) if hasattr(g_sess, "find_gamer_id_from_user_id") else None
                if g_id is not None and g_id not in active_idx:
                    continue
            return {"in_game": True, "game_id": str(gid)}
    except Exception as exc:
        print(f"[internal_check_user_in_game] Error: {exc}")
    return {"in_game": False, "game_id": ""}


@health_app.post("/internal/auth/force-logout")
async def internal_force_logout_user(request: Request, x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    body = await request.json()
    uid = str(body.get("user_id", "")).strip()
    if not uid:
        return {"ok": False, "kicked": 0}

    reason = str(body.get("reason") or "new_device_login").strip()
    message = str(body.get("message") or "حساب کاربری شما روی دستگاه دیگری وارد شد.").strip()

    from Commons import commands as cmd_const
    logout_cmd = make_command_json(
        id=cmd_const.Logout,
        data={
            "reason": reason,
            "message": message,
        },
    )
    kicked = 0

    # 1. Kick all /social sockets for this user
    social_sids = list(social_session.user_to_sockets.get(uid, set()))
    for sid in social_sids:
        try:
            await Socket_Server.emit("command", logout_cmd, to=sid, namespace="/social")
        except Exception:
            pass
        try:
            await Socket_Server.disconnect(sid, namespace="/social")
            kicked += 1
        except Exception:
            pass

    # 2. Kick any /game sockets for this user (safety net)
    try:
        from Entities.SocketIOClass.game import socketid_userid_pairs
        for sid, mapped_uid in list(socketid_userid_pairs.items()):
            if str(mapped_uid) == uid:
                try:
                    await Socket_Server.emit("command", logout_cmd, to=sid, namespace="/game")
                except Exception:
                    pass
                try:
                    await Socket_Server.disconnect(sid, namespace="/game")
                    kicked += 1
                except Exception:
                    pass
    except Exception:
        pass

    # 3. Kick any sockets in /lobby, /queue, /multi-queue, /classic-rank, /chat rooms
    for ns in ("/lobby", "/queue", "/multi-queue", "/classic-rank", "/chat"):
        try:
            rooms_map = Socket_Server.manager.rooms.get(ns, {})
            for room_key in (uid, f"user_{uid}"):
                sids_in_room = list((rooms_map.get(room_key) or {}).keys()) if isinstance(rooms_map.get(room_key), dict) else []
                for sid in sids_in_room:
                    try:
                        await Socket_Server.emit("command", logout_cmd, to=sid, namespace=ns)
                        await Socket_Server.disconnect(sid, namespace=ns)
                        kicked += 1
                    except Exception:
                        pass
        except Exception:
            pass

    print(f"[internal_force_logout_user] Forced logout ({reason}) for user {uid}: kicked {kicked} socket(s)")
    return {"ok": True, "kicked": kicked, "reason": reason}


@health_app.get("/internal/admin/runtime-status")
async def internal_admin_runtime_status(x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    from Entities.SocketIOClass.game import games, socketid_userid_pairs
    from Entities.SocketIOClass.queue import rank_queue_session
    from Entities.SocketIOClass.multi_queue import multi_rank_queue_session
    from Entities.SocketIOClass.lobby import lobby_session
    from Controllers.Spectator.spectator_session_manager import spectator_session_manager

    online_social_users = len(getattr(social_session, "user_to_sockets", {}) or {})
    social_sockets = sum(len(sids) for sids in (getattr(social_session, "user_to_sockets", {}) or {}).values())
    active_game_sockets = len(socketid_userid_pairs or {})

    ram_games = []
    for gid, gp in list(games.items()):
        if gp is None:
            continue
        is_done = bool(
            getattr(gp, "is_game_finished", False)
            or getattr(gp, "is_finished", False)
            or getattr(gp, "is_game_terminated", False)
        )
        players = []
        for g in getattr(gp, "gamers", []) or []:
            players.append({
                "user_id": str(getattr(g, "user_id", "")),
                "username": str(getattr(g, "username", "")),
            })
        raw_types = getattr(gp, "game_types", []) or []
        game_types = [str(gt.value if hasattr(gt, "value") else gt) for gt in raw_types]
        raw_score_type = getattr(gp, "game_score_type", "")
        score_type = str(raw_score_type.value if hasattr(raw_score_type, "value") else raw_score_type)
        ram_games.append({
            "game_id": str(gid),
            "game_types": game_types,
            "game_score_type": score_type,
            "players": players,
            "spectators": spectator_session_manager.get_spectator_count(str(gid)),
            "is_finished": is_done,
        })

    multi_breakdown = {
        "Ludo": len(getattr(multi_rank_queue_session, "ludo_queuers", []) or []),
        "Risk": len(getattr(multi_rank_queue_session, "risk_queuers", []) or []),
        "Uno": len(getattr(multi_rank_queue_session, "uno_queuers", []) or []),
        "Quiz": len(getattr(multi_rank_queue_session, "quiz_queuers", []) or []),
        "Coup": len(getattr(multi_rank_queue_session, "coup_queuers", []) or []),
        "Monopoly": len(getattr(multi_rank_queue_session, "monopoly_queuers", []) or []),
    }

    spectators_map = getattr(spectator_session_manager, "game_spectators", {}) or {}
    spectators_total = sum(len(u_map) for u_map in spectators_map.values())
    spectator_rooms = sum(1 for u_map in spectators_map.values() if len(u_map) > 0)

    return {
        "ok": True,
        "service": "backend",
        "uptime_seconds": int(time.time() - BACKEND_STARTED_AT),
        "online_social_users": online_social_users,
        "social_sockets": social_sockets,
        "active_game_sockets": active_game_sockets,
        "active_ram_games_count": len([g for g in ram_games if not g["is_finished"]]),
        "active_ram_games": ram_games[:50],
        "ranked_queue_count": len(getattr(rank_queue_session, "queuers", []) or []),
        "active_pre_games_count": len(getattr(rank_queue_session, "active_pre_games", {}) or {}),
        "multi_queue_count": sum(multi_breakdown.values()),
        "multi_queue_breakdown": multi_breakdown,
        "lobbies_count": len(getattr(lobby_session, "lobbies", []) or []),
        "spectators_count": spectators_total,
        "spectator_rooms_count": spectator_rooms,
    }


@health_app.post("/internal/admin/games/{game_id}/force-terminate")
async def internal_admin_force_terminate_game(game_id: str, x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    gid = str(game_id or "").strip()
    if not gid:
        raise HTTPException(status_code=400, detail="Invalid game_id")

    from Commons import commands as cmd_const
    from Entities.SocketIOClass.game import games, delete_game, socketid_gameid_pairs, socketid_userid_pairs

    existed_in_ram = gid in games
    gp = games.get(gid)
    if gp is not None:
        try:
            setattr(gp, "is_game_terminated", True)
            setattr(gp, "is_game_finished", True)
        except Exception:
            pass

    # Notify connected game room clients that match was terminated by admin
    try:
        await Socket_Server.emit(
            "command",
            make_command_json(
                id=cmd_const.Game_Finished,
                data={
                    "terminated_by_admin": True,
                    "reason": "admin_terminated",
                    "message": "این مسابقه توسط مدیریت متوقف شد.",
                },
            ),
            room=gid,
            namespace="/game",
        )
    except Exception as exc:
        print(f"[internal_admin_force_terminate_game] Emit error for {gid}: {exc}")

    # Disconnect any sockets still mapped to this game_id
    disconnected_sockets = 0
    for sid, mapped_gid in list(socketid_gameid_pairs.items()):
        if str(mapped_gid) == gid:
            try:
                await Socket_Server.disconnect(sid, namespace="/game")
                disconnected_sockets += 1
            except Exception:
                pass
            socketid_gameid_pairs.pop(sid, None)
            socketid_userid_pairs.pop(sid, None)

    # Clean RAM timers, spectator rooms, open_game_id, and presence
    if existed_in_ram:
        delete_game(gid)

    # Safety sync to MongoDB if still marked unfinished
    try:
        game_database.base_db["game_play_history"].update_one(
            {"_id": gid},
            {"$set": {"is_finished": True, "finish_date": datetime.now(), "terminated_by_admin": True}},
        )
    except Exception:
        pass

    return {
        "ok": True,
        "game_id": gid,
        "existed_in_ram": existed_in_ram,
        "disconnected_sockets": disconnected_sockets,
    }

app = socketio.ASGIApp(Socket_Server, other_asgi_app=health_app)
# logging.basicConfig(level=logging.DEBUG)
if __name__ == '__main__':
    # for fix asyncio errors
    import nest_asyncio
    nest_asyncio.apply()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host=host, port=port)
    # eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
    
    
# from fastapi import FastAPI , WebSocket
#
# from Controllers.GameController import GameController
# from Models.Gamer import GamerModel
#
# app = FastAPI()
#
# gameController = GameController()
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
#
#
# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}
#
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     # await websocket.send_text(f"ping")
#     await gameController.add_gamer(GamerModel(user_id=len(gameController.gamers) , username='erfan' , command_socket= websocket))
#
#     # await websocket.send_text(f"salam")
#     # # await websocket.send_bytes()
#     # while True:
#     #     data = await websocket.receive_text()
#     #     await websocket.send_text(f"Message text was: {data}")