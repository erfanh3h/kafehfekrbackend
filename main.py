import logging

import socketio
import uvicorn

from Entities.SocketIOClass import Socket_Server
# from Entities.Database import game_databasae
app = socketio.ASGIApp(Socket_Server)
logging.basicConfig(level=logging.DEBUG)
if __name__ == '__main__':
    # for fix asyncio errors
    import nest_asyncio
    nest_asyncio.apply()
    uvicorn.run(app, host='0.0.0.0', port=5000)
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