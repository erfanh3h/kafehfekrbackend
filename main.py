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