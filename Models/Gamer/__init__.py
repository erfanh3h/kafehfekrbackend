import asyncio

from Models.User import UserModel


class GamerModel(UserModel):
    def __init__(self, user_id: int, username: str, socket_id='', team_id: int = 0):
        super().__init__(user_id, username)
        self.socket_id = socket_id
        self.gamer_id: int = 0
        self.is_alive: bool = True
        self.is_disconnected: bool = False
        self.is_leaver: bool = False
        self.report_charge: int = 5
        self.reconnect_charge: int = 3
        self.team_id: int = team_id

        # self.role: int = 0
        # self.letAct: bool = True
        # this use when if user can act after use it this flag become true . this use for when if a user leave game when he most act his role
        # self.actDone: bool = False
        # self.deathType: DeathMoldels = DeathMoldels.none
        # self.isMafia = False
        # self.score : int = 0

    def reset_day(self):
        self.let_talk = True
        self.is_talking = False
        self.is_Challenging = False
        self.challenge_done = False
        self.end_talk = False

    async def talk(self):
        pass
        # return await self.communication.receive_voice_bytes()

    async def listen(self, bytes):
        pass

    async def request_challenge(self, return_function, timeout):
        pass
        # await self.communication.send_command_message({'id': 'RequestChallenge'})
        # try:
        #     message = await asyncio.wait_for(self.communication.receive_command_message(), timeout=timeout)
        #     if message is not None and message['id'] == 'RequestChallenge' and message['data']:
        #         await return_function(self.gamer_id)
        # except TimeoutError:
        #     pass

    async def accept_challenge(self, return_function, timeout):
        pass
        # await self.communication.send_command_message({'id': 'AcceptChallenge'})
        # try:
        #     message = await asyncio.wait_for(self.communication.receive_command_message(), timeout=timeout)
        #     if message is not None and message['id'] == 'AcceptChallenge' and message['data']:
        #         return_function(self.gamer_id)
        # except TimeoutError:
        #     pass

    def first_vote(self):
        pass

    def last_vote(self):
        pass

    def reaction(self):
        pass

    def night_action(self):
        pass

    async def send_wait_message(self, reason):
        pass
        # await self.communication.send_command_message({'id': 'Waiting', 'data': reason})

    async def send_custom_message(self, message):
        pass
        # await self.communication.send_command_message(message)
