import asyncio
import string
import random

import socketio


def create_random_str() -> str:
    char_set = string.ascii_uppercase + string.digits
    random_name = ''.join(random.sample(char_set * 6, 6))
    return random_name


sio = socketio.AsyncClient(logger=True, engineio_logger=True)


@sio.event(namespace='/queue')
async def connect():
    print('connection established')


@sio.event(namespace='/queue')
async def message(data):
    print('message received :  ', data)
    # sio.emit('userMessage', {'response': 'my response'})


@sio.event(namespace='/queue')
async def command(data):
    print('command received :  ', data)


@sio.event(namespace='/queue')
async def disconnect():
    print('disconnected from server')
    exit(0)


async def start():
    await sio.connect('http://localhost:5000', wait_timeout=1, auth={'user_id': create_random_str()},
                      namespaces="/queue")
    await asyncio.sleep(1)
    while True:
        # message = input("select piece : ")
        # await sio.emit('user_command', {'id': "salam"}, namespace="/queue")
        # await asyncio.sleep(.15)

        await sio.wait()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start())
