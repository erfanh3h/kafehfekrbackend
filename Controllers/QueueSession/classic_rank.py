"""
Classic Rank Session Manager for Cafe Fekr.

Handles Classic Rank matches where a player selects any game
and competes against an AI bot with default difficulty level = 2.
"""

import asyncio
import random
from typing import Dict, Optional

from Commons import commands, static_functions
from Commons.static_functions import make_command_json
from Entities.RewardManagerClass import GameScoreTypesEnum
from Entities.Security import create_access_token
from Models.Queuer import QueuerModel
from Bots import get_random_bot_profile, ClassicRankBot


class ClassicRankSession:
    def __init__(self):
        self.game_score_type = GameScoreTypesEnum.CLASSIC_RANK
        self.active_bots: Dict[str, ClassicRankBot] = {}

    async def start_classic_rank_match(self, human_queuer: QueuerModel, game_type: str, socket_id: str):
        """Creates a Classic Rank match for a human player vs an intelligent bot."""
        # Generate random Persian bot profile
        bot_prof = get_random_bot_profile(exclude_avatar=human_queuer.user_image)
        bot_name = bot_prof["name"]
        bot_avatar = bot_prof["avatar"]
        bot_score = bot_prof["score"]
        bot_user_id = "bot_" + static_functions.create_random_user_id()

        # Generate verified token for the bot
        bot_token = create_access_token({
            "id": bot_user_id,
            "phone": "09" + str(random.randint(100000000, 999999999)),
            "device_id": "bot_device_" + bot_user_id,
            "is_bot": True,
        })

        # Create bot QueuerModel
        bot_queuer = QueuerModel(
            user_id=bot_user_id,
            username=bot_name,
            user_image=bot_avatar,
            user_coin=1000,
            user_score=bot_score,
            is_rdy=True,
        )

        game_id = static_functions.create_random_game_id()
        final_game_types = [game_type]

        # Randomize player positions (Player 1 vs Player 2)
        queuers = [human_queuer, bot_queuer]
        random.shuffle(queuers)

        # Register game on /game namespace
        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

        # Instantiate bot with default level = 2
        def on_bot_game_finished(winner):
            if game_id in self.active_bots:
                del self.active_bots[game_id]

        bot = ClassicRankBot(
            game_id=game_id,
            game_type=game_type,
            bot_user_id=bot_user_id,
            bot_name=bot_name,
            bot_avatar=bot_avatar,
            token=bot_token,
            level=2,  # Default level must always be 2
            on_finished_callback=on_bot_game_finished,
        )
        self.active_bots[game_id] = bot

        # Launch bot connection in background
        asyncio.create_task(bot.start())

        # Notify human client that the match is ready (after namespace Connect ACK is flushed)
        game_data = {"game_id": game_id, "game_type": game_type}
        from Entities.SocketIOClass import Socket_Server

        async def _delayed_start_emit():
            await asyncio.sleep(0.05)
            await Socket_Server.emit(
                "command",
                make_command_json(id=commands.Start_Game, data=game_data),
                to=socket_id,
                namespace="/classic-rank",
            )

        asyncio.create_task(_delayed_start_emit())
        print(f"[ClassicRankSession] Match started: {game_id} | Game: {game_type} | Human: {human_queuer.username} vs Bot: {bot_name} (Lvl 2)")
