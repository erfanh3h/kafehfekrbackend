import asyncio

import socketio

sio = socketio.AsyncClient(logger=True, engineio_logger=True)


@sio.event
async def connect():
    print('connection established')


@sio.event
async def message(data):
    print('message received :  ', data)
    # sio.emit('userMessage', {'response': 'my response'})


@sio.event
async def command(data):
    print('command received :  ', data)


@sio.event
async def disconnect():
    print('disconnected from server')
    exit(0)


async def start():
    await sio.connect('http://localhost:5000', wait_timeout=1, auth={'user_id': 0, 'game_id': 'gameId'})
    await asyncio.sleep(1)
    while True:
        message = input("select peace : ")
        await sio.emit('userCommand', {'id': 'SelectPeace', 'data': int(message)})
        await asyncio.sleep(.15)

    # await sio.wait()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start())
