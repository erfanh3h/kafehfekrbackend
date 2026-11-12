"""
Classic Rank Bot Controller for Cafe Fekr.

Spawns an autonomous bot session connecting to /game namespace.
By default, difficulty level is 2 (Intermediate) for Classic Rank mode.
Features human-like thinking delay, intelligent game decision-making,
and Persian social reactions & chat responses.
"""

import asyncio
import os
import random
import sys
from typing import Callable, Optional
import socketio

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from .behavior.human_behavior import HumanBehavior
from .games import get_game_logic
from .games.base_game import BaseGameLogic
from .bot_data import (
    get_intelligent_bot_reaction,
    get_opening_reaction,
    get_critical_move_reaction,
    get_game_finish_reaction,
    KORI_GREETING,
    KORI_COMPLIMENT,
    KORI_SURPRISED,
    KORI_WITTY,
    KORI_FINISH,
)


class ClassicRankBot:
    def __init__(
        self,
        game_id: str,
        game_type: str,
        bot_user_id: str,
        bot_name: str,
        bot_avatar: int,
        token: str,
        level: int = 2,  # Default level must always be 2 for Classic Rank
        server_url: Optional[str] = None,
        on_finished_callback: Optional[Callable[[int], None]] = None,
    ):
        self.game_id = game_id
        self.game_type = game_type
        self.bot_user_id = bot_user_id
        self.bot_name = bot_name
        self.bot_avatar = bot_avatar
        self.token = token
        self.level = level
        if not server_url:
            port = os.getenv("PORT", "5000")
            server_url = f"http://127.0.0.1:{port}"
        self.server_url = server_url
        self.on_finished_callback = on_finished_callback
        self._http_session = None

        self.game_logic: BaseGameLogic = get_game_logic(self.game_type, level=self.level)
        self.behavior = HumanBehavior()
        self.sio: Optional[socketio.AsyncClient] = None
        self._simultaneous_task: Optional[asyncio.Task] = None
        self._pending_tasks: list[asyncio.Task] = []
        self.is_active = False
        self.my_role = 2  # default player 2, updated via GameData/UserData
        self._last_reaction_time: float = 0.0

    async def start(self):
        """Initializes and connects to the /game namespace."""
        self.is_active = True
        self.game_logic.on_game_start(self.game_id)

        try:
            import aiohttp
            self._http_session = aiohttp.ClientSession(trust_env=False)
            self.sio = socketio.AsyncClient(http_session=self._http_session)
        except Exception:
            self._http_session = None
            self.sio = socketio.AsyncClient()
        self._setup_handlers()

        # Brief delay to ensure GamePlay session is ready in backend
        await asyncio.sleep(0.4)

        for attempt in range(1, 5):
            try:
                print(f"[ClassicRankBot:{self.bot_name}] Connecting to /game (Attempt {attempt}/4) [Game ID: {self.game_id}]...")
                await self.sio.connect(
                    self.server_url,
                    namespaces=["/game"],
                    auth={"token": self.token, "game_id": self.game_id},
                )
                print(f"[ClassicRankBot:{self.bot_name}] Connected successfully as {self.bot_name} (Lvl {self.level})!")
                break
            except Exception as e:
                print(f"[ClassicRankBot:{self.bot_name}] Connection attempt {attempt} failed: {e}")
                await asyncio.sleep(0.6)

    def _setup_handlers(self):
        @self.sio.on("connect", namespace="/game")
        async def on_connect():
            print(f"[ClassicRankBot:{self.bot_name}] Socket connected to /game namespace.")

        @self.sio.on("disconnect", namespace="/game")
        async def on_disconnect():
            print(f"[ClassicRankBot:{self.bot_name}] Disconnected from /game namespace.")
            self.is_active = False

        @self.sio.on("command", namespace="/game")
        async def on_command(data):
            await self._handle_command(data)

        @self.sio.on("reaction", namespace="/game")
        async def on_reaction(data):
            await self._handle_incoming_reaction(data)

    async def emit(self, event: str, data):
        """Emits an event to /game namespace safely."""
        for _ in range(60):
            if self.sio and "/game" in self.sio.namespaces:
                break
            await asyncio.sleep(0.05)

        try:
            if self.sio and "/game" in self.sio.namespaces:
                await self.sio.emit(event, data, namespace="/game")
        except Exception as e:
            print(f"[ClassicRankBot:{self.bot_name}] Emit error ({event}): {e}")

    async def send_bot_reaction(self, reaction_id: int, delay: float = 0.0):
        """Sends a reaction/kori from the bot after an optional delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        if not self.is_active or not self.sio or not self.sio.connected:
            return
        self._last_reaction_time = asyncio.get_event_loop().time()
        print(f"[ClassicRankBot:{self.bot_name}] Sending reaction: {reaction_id}")
        await self.emit("user_reaction", reaction_id)

    async def _handle_incoming_reaction(self, data):
        """Intelligently replies to user reactions with human-like Persian expressions."""
        if not isinstance(data, dict):
            return
        sender_id = data.get("playerId", 0)
        reaction_id = data.get("reactionId", 0)

        # Ignore reactions sent by the bot itself
        if int(sender_id) == int(self.my_role):
            return

        # Cooldown guard: avoid spamming reactions if user sends rapidly
        now = asyncio.get_event_loop().time()
        if now - getattr(self, "_last_reaction_time", 0.0) < 1.6:
            return

        # 80% chance to react back, with realistic human reading & typing delay
        if random.random() < 0.80:
            delay = round(random.uniform(1.2, 2.5), 2)
            response_id = get_intelligent_bot_reaction(reaction_id)
            task = asyncio.create_task(self.send_bot_reaction(response_id, delay=delay))
            self._pending_tasks.append(task)

    async def _handle_command(self, data: dict):
        cmd_id = data.get("id")
        payload = data.get("data")

        if cmd_id in ("GamePlayData", "GamePlayTime", "GamePlayNavigate", "WaitTime"):
            return

        elif cmd_id == "GameData":
            if isinstance(payload, dict) and "gamers" in payload:
                for gamer in payload["gamers"]:
                    p_uid = gamer.get("user_id") if isinstance(gamer, dict) else ""
                    if p_uid == self.bot_user_id:
                        role = gamer.get("gamer_id", 2)
                        self.my_role = role
                        self.game_logic.set_player_role(role)
                        print(f"[ClassicRankBot:{self.bot_name}] Confirmed Player Role: Player {role}")
                        break
            self.game_logic.handle_server_command(cmd_id, payload)

        elif cmd_id == "UserData":
            if isinstance(payload, list):
                for idx, player in enumerate(payload):
                    p_uid = player.get("user_id") if isinstance(player, dict) else ""
                    if p_uid == self.bot_user_id:
                        role = idx + 1
                        self.my_role = role
                        self.game_logic.set_player_role(role)
                        print(f"[ClassicRankBot:{self.bot_name}] Assigned Role: Player {role}")
            elif isinstance(payload, dict):
                role = payload.get("user", payload.get("index", self.my_role or 2))
                self.my_role = role
                self.game_logic.set_player_role(role)
                self.game_logic.handle_server_command(cmd_id, payload)
                print(f"[ClassicRankBot:{self.bot_name}] Assigned Role: Player {role}")

        elif cmd_id == "StartGame":
            self.game_logic.handle_server_command(cmd_id, payload)
            # 50% chance to send friendly opening greeting or early match kori after 2.0 - 3.8s
            if random.random() < 0.50:
                task = asyncio.create_task(
                    self.send_bot_reaction(get_opening_reaction(), delay=random.uniform(2.0, 3.8))
                )
                self._pending_tasks.append(task)

            if hasattr(self.game_logic, "should_send_initial_board") and self.game_logic.should_send_initial_board():
                init_move = self.game_logic.get_initial_board_move()
                print(f"[ClassicRankBot:{self.bot_name}] Sending initial board setup: {init_move}")
                await self.behavior.simulate_thinking(level=self.game_logic.level, is_critical=False, legal_moves_count=1)
                await self.emit("user_command", init_move)
            elif getattr(self.game_logic, "is_simultaneous", False):
                if self._simultaneous_task is None or self._simultaneous_task.done():
                    self._simultaneous_task = asyncio.create_task(self._simultaneous_play_loop())

        elif cmd_id == "ReconnectData":
            if isinstance(payload, dict) and "gamers" in payload and isinstance(payload["gamers"], list):
                for gamer in payload["gamers"]:
                    p_uid = gamer.get("user_id") if isinstance(gamer, dict) else ""
                    if p_uid == self.bot_user_id:
                        role = gamer.get("gamer_id", 2)
                        self.my_role = role
                        self.game_logic.set_player_role(role)
                        print(f"[ClassicRankBot:{self.bot_name}] Confirmed Role on Reconnect: Player {role}")
                        break
            self.game_logic.handle_server_command(cmd_id, payload)
            if hasattr(self.game_logic, "should_send_initial_board") and self.game_logic.should_send_initial_board():
                init_move = self.game_logic.get_initial_board_move()
                await self.behavior.simulate_thinking(level=self.game_logic.level, is_critical=False, legal_moves_count=1)
                await self.emit("user_command", init_move)
            elif hasattr(self.game_logic, "should_act_on_reconnect") and self.game_logic.should_act_on_reconnect():
                await self._take_turn()
            elif getattr(self.game_logic, "is_simultaneous", False):
                if self._simultaneous_task is None or self._simultaneous_task.done():
                    self._simultaneous_task = asyncio.create_task(self._simultaneous_play_loop())

        elif cmd_id == "CurrentTurn":
            my_role = self.game_logic.my_player_num or self.my_role or 2
            if isinstance(payload, dict) and ("current_round" in payload or "current_turn" in payload or "dices" in payload or "question" in payload):
                self.game_logic.handle_server_command(cmd_id, payload)
                rnd = payload.get("current_round", payload.get("current_turn", payload.get("turn", 1)))
                print(f"[ClassicRankBot:{self.bot_name}] Simultaneous Turn (Round {rnd}) [My Role: Player {my_role}]")
                await self._take_turn()
            else:
                turn = payload.get("turn", payload) if isinstance(payload, dict) else payload
                self.game_logic.handle_server_command(cmd_id, payload)
                if int(turn) == int(my_role):
                    await self._take_turn()

        elif cmd_id == "RollResult":
            self.game_logic.handle_server_command(cmd_id, payload)
            await self._take_turn()

        elif cmd_id in ("PeaceSelected", "PeaceSwaped", "PeaceRemoved"):
            self.game_logic.handle_server_command(cmd_id, payload)
            if hasattr(self.game_logic, "should_continue_turn") and self.game_logic.should_continue_turn():
                await self._take_turn(is_continuation=True)

        elif cmd_id == "SelectRemovePeace":
            self.game_logic.handle_server_command(cmd_id, payload)
            my_role = self.game_logic.my_player_num or self.my_role or 2
            remover = payload.get("remover_id", payload) if isinstance(payload, dict) else payload
            if int(remover) == int(my_role):
                await self._take_turn()

        elif cmd_id == "NewTurnRound":
            self.game_logic.handle_server_command(cmd_id, payload)
            await self._take_turn()

        elif cmd_id == "FinishTurnRound":
            self.game_logic.handle_server_command(cmd_id, payload)

        elif cmd_id == "FinishRound":
            winner = payload.get("Winner", 0) if isinstance(payload, dict) else payload
            self.game_logic.on_round_finished(winner)

        elif cmd_id == "NewRound":
            self.game_logic.on_new_round(payload)

        elif cmd_id == "Surrender":
            print(f"[ClassicRankBot:{self.bot_name}] Opponent surrendered! Stopping bot.")
            self.is_active = False
            await asyncio.sleep(1.0)
            await self.disconnect()

        elif cmd_id in ("FinishGame", "GameFinished"):
            winner = payload.get("Winner", 0) if isinstance(payload, dict) else payload
            print(f"[ClassicRankBot:{self.bot_name}] Match Concluded! Final Winner: Player {winner}")
            self.is_active = False
            self.game_logic.on_game_finished(winner)

            bot_won = (int(winner) == int(self.my_role))
            is_draw = (int(winner) == 0)

            # 70% chance to send an outcome-appropriate reaction (victory praise or sportsmanship GG)
            if random.random() < 0.70:
                finish_reaction = get_game_finish_reaction(bot_won=bot_won, is_draw=is_draw)
                task = asyncio.create_task(
                    self.send_bot_reaction(finish_reaction, delay=random.uniform(0.6, 1.4))
                )
                self._pending_tasks.append(task)

            # Allow brief moment for reaction to be sent before disconnecting
            await asyncio.sleep(1.8)
            await self.disconnect()
            if self.on_finished_callback:
                self.on_finished_callback(winner)

        else:
            self.game_logic.handle_server_command(cmd_id, payload)
            if hasattr(self.game_logic, "should_continue_turn") and self.game_logic.should_continue_turn():
                await self._take_turn(is_continuation=True)

    async def _take_turn(self, is_continuation: bool = False):
        """Simulates human thinking time (Level 2) and plays move."""
        if not self.sio or not self.sio.connected:
            return

        legal_moves = self.game_logic.get_legal_moves()
        if not legal_moves:
            return

        if is_continuation:
            await asyncio.sleep(0.55)
        else:
            is_critical = self.game_logic.is_critical_turn()
            # 25% chance to send a tactical reaction during tense, critical turns
            if is_critical and random.random() < 0.25:
                reaction_choice = get_critical_move_reaction()
                asyncio.create_task(self.send_bot_reaction(reaction_choice, delay=0.4))

            await self.behavior.simulate_thinking(
                level=self.game_logic.level,
                is_critical=is_critical,
                legal_moves_count=len(legal_moves),
                bot_label=f"{self.bot_name} ({self.game_type} Lvl {self.game_logic.level})",
            )

        move = self.game_logic.compute_next_move()
        if move is None:
            return

        cmd_dict = self.game_logic.build_move_command(move)
        cmd_id = cmd_dict.get("id", "user_command")
        cmd_data = cmd_dict.get("data", move)

        print(f"[ClassicRankBot:{self.bot_name}] Playing move -> {move} (Command: {cmd_id})")
        await self.emit("user_command", {"id": cmd_id, "data": cmd_data})

    async def _simultaneous_play_loop(self):
        """Loop for simultaneous games like Sudoku."""
        await asyncio.sleep(random.uniform(3.0, 5.0))
        while self.is_active and self.sio and self.sio.connected:
            legal_moves = self.game_logic.get_legal_moves()
            if not legal_moves:
                break
            await self._take_turn()
            await asyncio.sleep(random.uniform(5.0, 8.5))

    async def disconnect(self):
        """Cleanly disconnects socket client and cancels pending tasks."""
        if self._simultaneous_task and not self._simultaneous_task.done():
            self._simultaneous_task.cancel()
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()

        if self.sio and self.sio.connected:
            try:
                await self.sio.disconnect()
            except Exception:
                pass
        if hasattr(self, "_http_session") and self._http_session and not self._http_session.closed:
            try:
                await self._http_session.close()
            except Exception:
                pass
        self.is_active = False
