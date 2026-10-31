"""
Bot Controller for Cafe Fekr Backend.
Controls in-process AI bots for Classic Rank (and any bot-enabled game sessions).
Applies default Level 2 difficulty, human-like thinking delays, natural reactions,
and authentic Persian sportsmanship chat/reactions.
"""
import asyncio
import random
from typing import Any, Optional

from Entities.Bots.games import get_game_logic
from Entities.Bots.behavior.human_behavior import HumanBehavior


FRIENDLY_STICKER_IDS = [1, 2, 4, 6, 8, 12, 14, 16]

# Standard Persian Sportsmanship Chat / Kori reactions (from app_consts / reaction IDs 101..178)
FRIENDLY_KORI_IDS = [101, 102, 104, 105, 110, 115, 120]


class BotController:
    """
    In-process bot driver that observes game session events and submits moves
    using the dedicated game logic engines.
    """
    def __init__(
        self,
        game_session,
        bot_user_id: str,
        bot_gamer_id: int,
        game_type: str,
        level: int = 2,  # Default level must always be 2 for Classic Rank
    ):
        self.game_session = game_session
        self.bot_user_id = bot_user_id
        self.bot_gamer_id = bot_gamer_id
        self.game_type = game_type
        self.level = level
        self.bot_socket_id = f"bot_{game_session.game_id}"
        
        self.behavior = HumanBehavior()
        self.game_logic = get_game_logic(game_type, level=self.level)
        self.game_logic.set_player_role(self.bot_gamer_id)
        
        self.is_thinking: bool = False
        self._simultaneous_task: Optional[asyncio.Task] = None
        
        print(f"[BotController] Initialized for {game_type} (Role: Player {self.bot_gamer_id}, Lvl: {self.level})")

    def handle_event(self, cmd_id: str, payload: Any):
        """Called by BaseGameSession whenever a server command is broadcast or sent."""
        if self.game_session.is_game_finished:
            return

        try:
            self._process_event(cmd_id, payload)
        except Exception as e:
            print(f"[BotController] Error handling event {cmd_id}: {e}")

    def _process_event(self, cmd_id: str, payload: Any):
        if cmd_id == "GameData":
            # Initial game setup
            self.game_logic.set_player_role(self.bot_gamer_id)
            if hasattr(self.game_logic, "should_send_initial_board") and self.game_logic.should_send_initial_board():
                init_move = self.game_logic.get_initial_board_move()
                asyncio.create_task(self._send_delayed_command(init_move, delay=1.2))
            
            # 45% chance to send an opening friendly greeting reaction after countdown
            if random.random() < 0.45:
                asyncio.create_task(self._send_delayed_reaction(random.choice(FRIENDLY_STICKER_IDS), delay=random.uniform(5.5, 7.5)))

            if getattr(self.game_logic, "is_simultaneous", False):
                if self._simultaneous_task is None or self._simultaneous_task.done():
                    self._simultaneous_task = asyncio.create_task(self._simultaneous_play_loop())

        elif cmd_id == "CurrentTurn":
            self.game_logic.set_player_role(self.bot_gamer_id)
            if isinstance(payload, dict) and ("current_round" in payload or "dices" in payload):
                # Simultaneous turn (e.g. FekrBekr, Yatzy)
                self.game_logic.handle_server_command(cmd_id, payload)
                asyncio.create_task(self._take_turn())
            else:
                turn = payload.get("turn", payload) if isinstance(payload, dict) else payload
                self.game_logic.handle_server_command(cmd_id, payload)
                if int(turn) == self.bot_gamer_id:
                    asyncio.create_task(self._take_turn())

        elif cmd_id == "RollResult":
            self.game_logic.handle_server_command(cmd_id, payload)
            turn = payload.get("turn", self.bot_gamer_id) if isinstance(payload, dict) else self.bot_gamer_id
            if int(turn) == self.bot_gamer_id:
                asyncio.create_task(self._take_turn())

        elif cmd_id in ("PeaceSelected", "PeaceSwaped", "PeaceRotated", "PeaceRemoved"):
            self.game_logic.handle_server_command(cmd_id, payload)
            if hasattr(self.game_logic, "should_continue_turn") and self.game_logic.should_continue_turn():
                asyncio.create_task(self._take_turn(is_continuation=True))

        elif cmd_id == "SelectRemovePeace":
            self.game_logic.handle_server_command(cmd_id, payload)
            remover = payload.get("remover_id", payload) if isinstance(payload, dict) else payload
            if int(remover) == self.bot_gamer_id:
                asyncio.create_task(self._take_turn())

        elif cmd_id == "NewTurnRound":
            self.game_logic.handle_server_command(cmd_id, payload)
            asyncio.create_task(self._take_turn())

        elif cmd_id in ("FinishTurnRound", "FinishRound", "NewRound"):
            self.game_logic.handle_server_command(cmd_id, payload)

        elif cmd_id in ("FinishGame", "GameFinished"):
            if self._simultaneous_task and not self._simultaneous_task.done():
                self._simultaneous_task.cancel()

    def handle_reaction_received(self, reaction_id: Any, sender_gamer_id: int):
        """Called when the human opponent sends a reaction in-game."""
        if sender_gamer_id == self.bot_gamer_id:
            return
        # 70% chance to respond with a friendly reaction after a human-like delay
        if random.random() < 0.70:
            resp_id = random.choice(FRIENDLY_STICKER_IDS)
            asyncio.create_task(self._send_delayed_reaction(resp_id, delay=random.uniform(1.6, 3.2)))

    async def _send_delayed_reaction(self, reaction_id: int, delay: float):
        try:
            await asyncio.sleep(delay)
            if self.game_session and not self.game_session.is_game_finished:
                from Entities.SocketIOManagerClass import send_reaction
                await send_reaction(player_id=self.bot_gamer_id, reaction_id=reaction_id, game_id=self.game_session.game_id)
        except Exception as e:
            print(f"[BotController] Error sending reaction: {e}")

    async def _send_delayed_command(self, cmd_dict: dict, delay: float):
        try:
            await asyncio.sleep(delay)
            if self.game_session and not self.game_session.is_game_finished:
                await self.game_session.command_received(cmd_dict, self.bot_socket_id)
        except Exception as e:
            print(f"[BotController] Error sending setup command: {e}")

    async def _take_turn(self, is_continuation: bool = False):
        """Simulates natural human cognitive delay, computes move, and emits to game session."""
        if self.is_thinking or self.game_session.is_game_finished:
            return
        self.is_thinking = True
        try:
            legal_moves = self.game_logic.get_legal_moves()
            if not legal_moves:
                return

            if is_continuation:
                await asyncio.sleep(random.uniform(0.45, 0.75))
            else:
                is_critical = False
                if hasattr(self.game_logic, "is_critical_turn"):
                    is_critical = self.game_logic.is_critical_turn()
                delay = self.behavior.calculate_thinking_delay(
                    level=self.level,
                    is_critical=is_critical,
                    legal_moves_count=len(legal_moves),
                )
                await asyncio.sleep(delay)

            if self.game_session.is_game_finished:
                return

            move = self.game_logic.compute_next_move()
            if move is None:
                return

            cmd_dict = self.game_logic.build_move_command(move)
            await self.game_session.command_received(cmd_dict, self.bot_socket_id)

            # 20% chance after making a great move to send a subtle reaction
            if random.random() < 0.20:
                asyncio.create_task(self._send_delayed_reaction(random.choice([1, 2, 4, 14]), delay=random.uniform(1.2, 2.2)))

        except Exception as e:
            print(f"[BotController] Error taking turn: {e}")
        finally:
            self.is_thinking = False

    async def _simultaneous_play_loop(self):
        """Loop for simultaneous games like Sudoku."""
        await asyncio.sleep(random.uniform(3.5, 5.5))
        while not self.game_session.is_game_finished:
            legal_moves = self.game_logic.get_legal_moves()
            if not legal_moves:
                break
            await self._take_turn()
            await asyncio.sleep(random.uniform(4.5, 7.5))
