import socketio
import asyncio
import random
from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession.rank import RankQueueSession
from Models.Queuer import QueuerModel
from Entities.RewardManagerClass import GameScoreTypesEnum

rank_queue_session = RankQueueSession()
rank_queue_session.init_session()

connected_queuers: dict[str, QueuerModel] = {}
socket_user_map: dict[str, str] = {}

PERSIAN_NAMES = [
    "آرش", "سارا", "نیلوفر", "بردیا", "کوروش", "شایان", "مبینا", "امیررضا",
    "رویا", "آرمین", "پویا", "مهسا", "دانیال", "فرهاد", "الناز", "کامران",
    "سامان", "غزاله", "کیان", "آوا", "سهراب", "ندا", "امید", "بهار", "شهاب", "یلدا"
]

class QueueSocketNameSpace(socketio.AsyncNamespace):
    async def on_connect(self, socket_id, environ, auth):
        if auth is not None:
            try:
                from Entities.Security import extract_token
                token_data = await extract_token(auth['token'])
                if token_data is not None:
                    user_id = token_data['id']
                    pre_game_id = auth.get('pre_game_id', None)
                    mode = auth.get('mode', None)
                    game_type = auth.get('game_type', None)
                else:
                    await self.disconnect(socket_id, namespace="/queue")
                    return
            except Exception as e:
                print('Error in queue on_connect auth:', e)
                await self.disconnect(socket_id, namespace="/queue")
                return
        else:
            await self.disconnect(socket_id, namespace="/queue")
            return

        from Entities.Database import game_database
        user_data = game_database.users_manager.read_user(user_id) or {}
        queuer_data = QueuerModel(
            user_id,
            user_data.get("username", "بازیکن"),
            socket_id=socket_id,
            user_image=user_data.get('image', 1),
            user_coin=user_data.get('coin', 1000),
            user_score=user_data.get('score', 1000)
        )
        connected_queuers[socket_id] = queuer_data
        socket_user_map[socket_id] = user_id

        if mode in ("ClassicRank", "classic_rank"):
            target_game = game_type if game_type else "TicTacToe"
            asyncio.create_task(self.delayed_start_classic_rank(queuer_data, target_game, socket_id))
            return

        if pre_game_id is None:
            rank_queue_session.join_queuer(queuer_data)
        else:
            rank_queue_session.reconnect_queuer(pre_game_id, queuer_data)

    async def delayed_start_classic_rank(self, queuer_data, game_type, socket_id):
        # Allow connect handshake to finish and room assignment to complete
        await asyncio.sleep(0.25)
        await self.start_classic_rank(queuer_data, game_type, socket_id)

    async def on_disconnect(self, socket_id):
        if socket_id in connected_queuers:
            del connected_queuers[socket_id]
        if socket_id in socket_user_map:
            del socket_user_map[socket_id]
        await rank_queue_session.disconnect_user(socket_id)

    async def on_user_command(self, socket_id, data):
        print('User Sended command ', data)
        cmd_id = data.get('id', '')
        if cmd_id in ("StartClassicRank", getattr(commands, 'Start_Classic_Rank', 'StartClassicRank')):
            cmd_payload = data.get('data') if isinstance(data.get('data'), dict) else data
            game_type = cmd_payload.get('game_type', 'TicTacToe')
            queuer_data = connected_queuers.get(socket_id)
            if not queuer_data:
                queuer_data = rank_queue_session.find_gamer_from_socket_id(socket_id)
            if not queuer_data:
                from Entities.Database import game_database
                user_id = socket_user_map.get(socket_id)
                u_data = game_database.users_manager.read_user(user_id) or {} if user_id else {}
                queuer_data = QueuerModel(
                    user_id or ("u_" + socket_id),
                    u_data.get("username", "بازیکن"),
                    socket_id=socket_id,
                    user_image=u_data.get('image', 1),
                    user_coin=u_data.get('coin', 1000),
                    user_score=u_data.get('score', 1000)
                )
                connected_queuers[socket_id] = queuer_data

            if queuer_data in rank_queue_session.queuers:
                rank_queue_session.queuers.remove(queuer_data)
            await self.start_classic_rank(queuer_data, game_type, socket_id)
            return

        await rank_queue_session.command_received(data, socket_id)

    async def start_classic_rank(self, human_queuer, game_type, socket_id):
        from Entities.SocketIOManagerClass import send_queue_command
        from Entities.SocketIOClass.game import add_new_game

        game_id = static_functions.create_random_game_id()
        bot_id = "bot_" + static_functions.create_random_name()
        bot_name = random.choice(PERSIAN_NAMES)
        bot_avatar = random.randint(1, 26)
        bot_score = human_queuer.user_score if human_queuer.user_score is not None else 1000

        bot_queuer = QueuerModel(
            bot_id,
            bot_name,
            socket_id=None,
            user_image=bot_avatar,
            user_coin=human_queuer.user_coin if human_queuer.user_coin is not None else 1000,
            user_score=bot_score
        )

        queuers = [human_queuer, bot_queuer]
        final_game_types = [game_type]

        game_data = {
            'game_id': game_id,
            'game_type': game_type,
            'game_score_type': 'ClassicRank'
        }
        print(f'[ClassicRank] Starting match {game_id} for {human_queuer.user_id} vs {bot_name} ({game_type}) on socket {socket_id}')
        await send_queue_command(
            command=make_command_json(id=commands.Start_Game, data=game_data),
            socket_id=socket_id
        )

        add_new_game(game_id, queuers, final_game_types, GameScoreTypesEnum.CLASSIC_RANK)

def return_random_id():
    user_id = static_functions.create_random_name()
    return user_id
