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
    if data['id'] == 'RequestChallenge':
        message = input("wana challenge ? (1 for accept) : ")
        if message == "1":
            await sio.emit('userCommand', {'id': 'UserRequestedChallenge'})

@sio.event
async def disconnect():
    print('disconnected from server')

async def start():
    await sio.connect('http://localhost:5000' , wait_timeout = 1 , auth={'name' : 'test'})
    await asyncio.sleep(1)
    # while True:
    #     message = input("Enter : ")
    #     await sio.emit('userMessage', {'response': f'{str(message)}'})
    #     await asyncio.sleep(.15)

    await sio.wait()

if __name__ == '__main__':
    loop=asyncio.get_event_loop()
    loop.run_until_complete(start())
