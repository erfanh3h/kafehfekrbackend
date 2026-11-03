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
from fastapi import FastAPI

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