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

import socketio
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request

from Commons.static_functions import make_command_json
from Controllers.SocialSession import social_session
from Entities.Security import SECRET_KEY
from Entities.SocketIOClass import Socket_Server
from Entities.Database import game_database

# Health app for container healthchecks & monitoring
health_app = FastAPI(docs_url=None, redoc_url=None)

@health_app.get("/health")
async def health_check():
    return {"status": "ok", "service": "backend"}

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

    from Commons import commands as cmd_const
    logout_cmd = make_command_json(
        id=cmd_const.Logout,
        data={
            "reason": "new_device_login",
            "message": "حساب کاربری شما روی دستگاه دیگری وارد شد.",
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
            # Check all sids in the namespace if stored in session or room
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

    print(f"[internal_force_logout_user] Forced logout for user {uid}: kicked {kicked} socket(s)")
    return {"ok": True, "kicked": kicked}

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