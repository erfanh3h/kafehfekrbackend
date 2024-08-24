import asyncio

import socketio

sio = socketio.AsyncClient(logger=True, engineio_logger=True)


@sio.event(namespace='/game')
async def connect():
    print('connection established')


@sio.event(namespace='/game')
async def message(data):
    print('message received :  ', data)
    # sio.emit('userMessage', {'response': 'my response'})


@sio.event(namespace='/game')
async def command(data):
    print('command received :  ', data)


@sio.event(namespace='/game')
async def disconnect():
    print('disconnected from server')
    exit(0)


async def start():
    await sio.connect('http://localhost:5000', wait_timeout=1, auth={'user_id': "0", 'game_id': 'gameId'},
                      namespaces="/game")
    await asyncio.sleep(1)
    while True:
        message = input("select piece : ")
        await sio.emit('user_command', {'id': 'SelectPeace', 'data': {'index': int(message), 'dice_index': 0}},
                       namespace="/game")
        await asyncio.sleep(.15)

    # await sio.wait()


# tictactoe
# message = input("select peace : ")
# await sio.emit('userCommand', {'id': 'SelectPeace', 'data': int(message)})
# await asyncio.sleep(.15)

# RPC
# message = input("select peace type : ")
# selection = "rock"
# if message == "0":
#     selection = "rock"
# elif message == "1":
#     selection = "paper"
# elif message == "2":
#     selection = "cutter"
# await sio.emit('userCommand', {'id': 'SelectPeace', 'data': selection})

# MNumbers
# msg = input("select peace : ")
# await sio.emit('userCommand', {'id': 'SelectPeace', 'data': {'index1': int(msg), 'index2': 35}})
# await asyncio.sleep(.15)
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start())
