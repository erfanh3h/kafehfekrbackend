# Cafe Fekr — Realtime Backend Server (`kafehfekrbackend`)

The **authoritative realtime game server** for **Cafe Fekr (کافه فکر)**. It orchestrates live multiplayer matchmaking, handles client connections via Socket.IO, manages turn timers and disconnections, executes authoritative game rules for **25 board games** (including Monopoly, Risk, Chess, Backgammon, Yatzy, and Ludo), calculates competitive Elo rewards, hosts simulated AI bots, drives real-time social presence & chat, and powers the **Live Spectator Mode** with state sanitization and real-time room broadcasting.

---

## 1. High-Level Summary

| Property | Value |
|---|---|
| **Primary Stack** | Python 3.12, `python-socketio` (ASGI), `FastAPI` (Healthcheck & Root route), `uvicorn`, `pymongo`, `nest_asyncio`, `aiohttp` |
| **Default Port** | `5000` (`PORT=5000`, `HOST=0.0.0.0`) |
| **Protocol** | WebSockets / HTTP Long-Polling (Socket.IO v4, `EIO=4`) |
| **Database** | MongoDB (`KafehFekrDB`) |
| **Active Socket Namespaces** | `/game`, `/queue`, `/classic-rank`, `/lobby`, `/social`, `/multi-queue`, `/chat` |
| **Companion REST Service** | `kafehfekrserver` (Port `5001`) |
| **Supported Game Engines** | 25 authoritative board game engines |
| **Multiplayer (>2P) Architecture** | Robust 3–4 player surrender, disconnect, AFK, and podium resolution in `BaseMultiplayerGameSession` |
| **Live Spectator Subsystem** | `Controllers/Spectator/` (Discovery, sanitization, room streaming) |
| **Client Applications** | Godot 4.7 (`cafefekr/`), Legacy Flutter (`flutter-code/`) |

---

## 2. System Architecture

The backend operates on an event-driven, authoritative three-layer model with real-time social, clan, and live spectator engines:

```
                         +---------------------------------------+
                         |       Client (Godot / Flutter)        |
                         +---------------------------------------+
                                             |
                         Socket.IO v4 (EIO=4, /game, /queue, /social, etc.)
                                             v
                         +---------------------------------------+
                         |         ASGI Application Layer        |
                         |  python-socketio + FastAPI (Health)  |
                         +---------------------------------------+
                                             |
         +-----------------------------------+-----------------------------------+
         |                                   |                                   |
         v                                   v                                   v
+------------------+                +------------------+                +------------------+
| Queue & Lobby    |                | In-Match Game    |                | Social, Clan &   |
| Namespaces       |                | Orchestrator     |                | Spectator Hub    |
| (/queue, /lobby, |                | (BaseGamePlay)   |                | (/social)        |
|  /classic-rank)  |                +------------------+                +------------------+
+------------------+                         |                                   |
         |                                   v                                   v
         v                          +------------------+                +------------------+
+------------------+                |   Game Session   |  <-- TimerClass| Spectator Engine |
| In-Process Bots  |                | (BaseGameSession |  <-- 60s DC    | (Access, Rooms,  |
| (ClassicRankBot, |                | & BaseMultiplayer|      Recovery  |  State Sanitizer)|
|  25 Game Bots)   |                +------------------+                +------------------+
+------------------+                         |                                   |
                                             v                                   |
                                    +------------------+                         |
                                    | Pure Game Rules  |  <-- 25 Authoritative   |
                                    | (Entities/Games) |      Game Engines       |
                                    +------------------+                         |
                                             |                                   |
                                             +-----------------+-----------------+
                                                               |
                                                               v
                                    +------------------------------------------------------+
                                    |     Reward Manager & MongoDB Persistence             |
                                    |  (KafehFekrDB: users, history, presence, clans, DMs) |
                                    +------------------------------------------------------+
```

### The Three-Layer Game Engine & Multiplayer Resilience

1. **Layer 1: Series Orchestrator (`Controllers/GamePlay/` — `BaseGamePlayClass`)**
   - Manages match series lifecycle:
     - **Ranked Series:** Best-of-3 (Bo3) match series across 3 drafted games.
     - **Classic Rank & Lobby:** Single-game matches.
     - **Clan Friendly Challenges:** 2–4 player clan challenges across any of the 25 games (`SocialClanChallengeStart`).
   - Countdown timers: `Join_Game_Limit_Time = 20s`, `Game_Play_Round_Time = 10s`.
   - Reconnection tracking: sets `open_game_id` in MongoDB.
   - **Spectator Broadcast Hook:** When game moves, turns, round changes, or match endings occur, the orchestrator notifies `SpectatorSessionManager` to push sanitized updates to viewers in `spectate_<game_id>`.

2. **Layer 2: Game Session Controller (`Controllers/GameSession/` — `BaseGameSession` & `BaseMultiplayerGameSession`)**
   - Manages player indices (`gamer_id: 1..N`), turn timers (`TimerClass` with thread-safe `_run_id` guards).
   - **Multiplayer (>2P) Surrender & Disconnect Architecture (`BaseMultiplayerGameSession`):**
     - When a player surrenders in a 3- or 4-player game (e.g. Risk, Ludo, Monopoly, Uno, Coup, Quiz), they are cleanly eliminated from `active_player_indexes` without ending the match for the remaining players.
     - The eliminated player's turn timer is immediately stopped, their active turn advances to the next player (`_on_player_eliminated`), and remaining players continue playing.
     - **Selective Disconnect Pause:** `_sync_timer_pause_state()` only pauses the game timer if an *active* player is disconnected. Disconnections by already-eliminated players never stall the game.
     - **Automated Human Check:** `_check_and_finish_if_no_humans_left()` detects if all remaining active players are AI bots (i.e. all human players surrendered or left). In that case, the game immediately concludes, awarding podium ranks (`rank1`, `rank2`) to the remaining bots.
     - **AFK Protection:** 2 consecutive missed turns result in player elimination without penalizing or halting remaining participants.
   - 25 concrete game session controllers (including `monopoly_game_session.py`, `risk_game_session.py`, `chess_game_session.py`, `ludo_game_session.py`).

3. **Layer 3: Pure Authoritative Game Rules (`Entities/Games/<Game>/`)**
   - Pure state machines containing board matrices, move validations, and win/draw determinations.
   - **Risk Strike Engine Overhaul:** Refined action pacing, defense-phase strategy cards, continent bonus calculations, and enhanced bot threat-evaluation.
   - **Match Numbers (`MNumbers`) Parity:** Immediate 1st piece reveal and lock state to eliminate rapid double-click race conditions.
   - **Yatzy Rules Parity:** Enforces strictly 3 re-rolls per turn-round before scoring.
   - **Sudoku Payload Versatility:** Supports both nested `data['data']` and top-level piece placement identifiers.

---

## 3. Directory Structure

```
kafehfekrbackend/
├── main.py                     # Entry point: ASGI app, Socket.IO server & FastAPI healthcheck
├── Dockerfile                  # Container build definition (Python 3.12-slim)
├── requirements.txt            # Python dependencies (fastapi, python-socketio, pymongo, etc.)
├── .dockerignore / .gitignore   # Ignored files
├── test*.py                    # Test harnesses and smoke scripts
│
├── Bots/                       # In-process AI bots
│   ├── bot_controller.py       # Bot runner and event listener
│   ├── bot_data.py             # Pre-configured bot profile pools (names, avatars, frames)
│   ├── behavior/               # Human-like behaviors (delay heuristics, deliberate mistake rate)
│   │   └── human_behavior.py
│   └── games/                  # Per-game bot decision engines (25 game AI scripts)
│       ├── risk.py             # Risk AI (continent priorities, strategy cards, defense play)
│       ├── monopoly.py         # Monopoly AI (property evaluation, auctions, trades)
│       ├── yatzy.py            # Yatzy AI (3 re-rolls, category scoring heuristics)
│       ├── chess.py            # Minimax Chess AI
│       └── ...                 # 21 additional game bot engines
│
├── Commons/                    # Shared protocol definitions & helpers
│   ├── commands.py             # Master list of ~140 command string constants
│   └── static_functions.py     # Asyncio loop dispatcher (safe_run_async), difficulty mappings
│
├── Controllers/                # Match orchestrators and session managers
│   ├── GamePlay/               # Series-level orchestrator (BaseGamePlayClass)
│   ├── GameSession/            # 25 game-specific sessions + BaseMultiplayerGameSession
│   ├── QueueSession/           # Matchmaking queues (rank, lobby, classic_rank, multi_rank)
│   ├── SocialSession/          # Real-time social coordinator (presence, DMs, clans, invites)
│   └── Spectator/              # Complete Live Spectator Mode subsystem
│       ├── __init__.py         # Package exports
│       ├── spectator_access_manager.py     # Privacy, relationship, and game safety rules
│       ├── spectator_controller.py         # Socket.IO spectator command handler & live games
│       ├── spectator_room_manager.py       # Socket room management (spectate_<game_id>)
│       ├── spectator_session_manager.py    # Active viewer tracking & broadcast coordinator
│       └── spectator_state_serializer.py   # State sanitization (strips hidden private data)
│
├── Entities/                   # Core business logic and infrastructure
│   ├── Database/               # MongoDB collections, indexes & queries
│   │   ├── config_collection.py
│   │   ├── game_history_collection.py      # Round records + ensure_indexes()
│   │   ├── game_play_history_collection.py # Series records + ensure_indexes()
│   │   ├── questions_collection.py         # Trivia question bank
│   │   ├── users_collection.py             # Profiles, wallets, active match pointers, avatar frames
│   │   ├── user_history_collection.py      # Aggregated performance stats + ensure_indexes()
│   │   └── social/                         # Social system persistence
│   │       ├── clans_collection.py         # Clans, memberships, join requests, audit logs
│   │       ├── clan_messages_collection.py # Clan chat messages
│   │       ├── direct_messages_collection.py # Private player-to-player DMs
│   │       ├── friends_collection.py       # Friendships, requests, blocks
│   │       ├── invitations_collection.py   # Match and lobby invitations
│   │       ├── notifications_collection.py # In-game notification events
│   │       ├── presence_collection.py      # Real-time online/in-game presence
│   │       ├── reports_collection.py       # Moderation tickets
│   │       └── rivals_collection.py        # Head-to-head rivalry stats
│   ├── Games/                  # Authoritative rules for each of the 25 games
│   │   ├── Risk/               # Risk Strike territories, strategy cards, defense phase, attack handler
│   │   ├── Monopoly/           # Monopoly board, deeds, chance/chest cards, trade & auction logic
│   │   ├── MNumbers/           # Immediate 1st card reveal & lock logic
│   │   ├── Yatzy/              # 3 re-rolls per round scoring
│   │   └── ...                 # 21 additional pure game implementations
│   ├── RewardManagerClass/     # Dynamic Elo rating, multi-rank podium rewards, XP & Coin algorithms
│   ├── Security/               # JWT token validation & decoding
│   ├── SocketIOClass/          # Socket.IO Namespace handlers
│   │   ├── _auth_guard.py      # Shared auth, ban/auto-unban, maintenance, version & queue gates
│   │   ├── game.py             # /game namespace (live player moves, O(1) lookups & cleanup)
│   │   ├── queue.py            # /queue namespace (ranked matchmaking & draft)
│   │   ├── classic_rank.py     # /classic-rank namespace (instant bot matches)
│   │   ├── lobby.py            # /lobby namespace (custom rooms)
│   │   ├── social.py           # /social namespace (presence, DMs, clans, live games, spectate)
│   │   ├── multi_queue.py      # /multi-queue namespace (4-player queue for 6 games)
│   │   └── chat.py             # /chat namespace (global chat)
│   ├── SocketIOManagerClass/   # Room-level emission helper utilities
│   └── TimerClass/             # Robust threading timer with run_id safety guards
│
├── Models/                     # Data models (Gamer, Queuer, Lobby, User with profile_frame)
└── tests/                      # Automated unit tests
    ├── test_classic_rank_ai_levels.py
    ├── test_multiplayer_surrender_disconnect.py
    └── test_backend_optimizations.py
```

---

## 4. Socket.IO Namespaces & Protocols

| Namespace | Handler File | Session Manager | Description |
|---|---|---|---|
| `/game` | `Entities/SocketIOClass/game.py` | `BaseGamePlayClass` | Main gameplay room. Handles player moves, turns, timer ticks, reconnects, surrender, and game end. |
| `/queue` | `Entities/SocketIOClass/queue.py` | `RankQueueSession` | Ranked matchmaking. Manages queue entry, match acceptance (20s), and 7-turn pick/ban draft. |
| `/classic-rank` | `Entities/SocketIOClass/classic_rank.py` | `ClassicRankSession` | Instant human vs AI bot match generation. Spawns an in-process bot and directs both to `/game`. |
| `/lobby` | `Entities/SocketIOClass/lobby.py` | `LobbySession` | Custom friendly rooms (2–4 players, password support, kick, ready, start). |
| `/social` | `Entities/SocketIOClass/social.py` | `SocialSessionManager` & `SpectatorController` | Real-time presence, private DMs, clan chat rooms (`clan_<id>`), invitations, live games discovery (`RequestLiveGames`), and spectator sessions (`RequestSpectate`, `LeaveSpectate`). |
| `/multi-queue` | `Entities/SocketIOClass/multi_queue.py` | `MultiRankQueueSession`| 4-player matchmaking queue (`Ludo`, `Risk`, `Uno`, `Quiz`, `Coup`, `Monopoly`). |
| `/chat` | `Entities/SocketIOClass/chat.py` | `ChatSession` | Global community chat (Legacy Flutter client). |

All namespaces enforce shared authentication and gating via `Entities/SocketIOClass/_auth_guard.py` (JWT validation, ban/auto-unban, maintenance mode, minimum client version, and queue-closed checks as configured per namespace). Matchmaking (`RankQueueSession`, `MultiRankQueueSession`) and `LobbySession` include thread-safe queue locking and defensive payload validation, and `RiskGameSession` / `RiskGameClass` enforce attacker-only roll authority and timer recovery on invalid payloads.

---

## 5. Live Spectator Mode Subsystem (`Controllers/Spectator/`)

The backend provides a comprehensive, production-grade spectator architecture:

```
                                [Client Request]
                         RequestSpectate {game_id} on /social
                                        │
                                        ▼
                         SpectatorAccessManager.check_can_spectate()
                         ├─ Game is active & not finished?
                         ├─ Mutual blockcheck (viewer vs players)?
                         ├─ Viewer not already playing in another active match?
                         ├─ Player privacy allows spectators? (everyone/friends/clan/nobody)
                         ├─ Relationship check (is friend or clanmate)?
                         └─ Spectator capacity limit (< 50 viewers)?
                                        │
                         [PASSED]       │       [FAILED]
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
  SpectatorRoomManager.join_room()                    Emit SpectateRejected
  (sid joins spectate_<game_id>)                     {"reason": ..., "message": ...}
                 │
                 ▼
  SpectatorStateSerializer.serialize_snapshot()
  (Strips hidden private state: hidden cards,
   unrevealed mines, secret fleet locations)
                 │
                 ▼
  Emit SpectateAccepted {snapshot} to viewer
  Emit SpectatorCountUpdated to spectate_<game_id>
                 │
                 ▼
  [LIVE MATCH IN PROGRESS]
  Game engine emits SpectatorGameState / SpectatorTurnChanged /
  SpectatorMoveBroadcast to room spectate_<game_id> in real time!
                 │
                 ▼
  [MATCH FINISHES]
  Emit SpectatorGameEnded {winner, scores} -> Auto-cleans spectator room.
```

### Live Spectator Commands Reference

| Command ID | Direction | Namespace | Payload / Purpose |
|---|---|---|---|
| `RequestSpectate` | Client $\rightarrow$ Server | `/social` | `{"game_id": "...", "player_id": "..."}`: Request to spectate an ongoing match. |
| `SpectateAccepted` | Server $\rightarrow$ Client | `/social` | Initial sanitized state snapshot (`game_id`, `game_type`, `board_data`, `gamers`, `spectator_count`). |
| `SpectateRejected` | Server $\rightarrow$ Client | `/social` | `{"game_id": "...", "reason": "...", "message": "..."}`: Rejection details. |
| `LeaveSpectate` | Client $\rightarrow$ Server | `/social` | `{"game_id": "..."}`: Leaves the spectator room and updates viewer count. |
| `RequestSpectatorState`| Client $\rightarrow$ Server | `/social` | Requests fresh state snapshot after connection disruption. |
| `SpectatorCountUpdated`| Server $\rightarrow$ Client | `/social` & `/game` | `{"game_id": "...", "spectator_count": <int>}`: Live viewer counter update. |
| `SpectatorGameState` | Server $\rightarrow$ Client | `/social` | Sanitized game state broadcast following major phase or board changes. |
| `SpectatorGameEnded` | Server $\rightarrow$ Client | `/social` | `{"game_id": "...", "winner_id": "...", "scores": [...]}`: Final match results broadcast to spectators. |
| `RequestLiveGames` | Client $\rightarrow$ Server | `/social` | `{"scope": "all"|"friends"|"clan", "game_type": "..."}`: Requests live ongoing matches. |
| `LiveGamesList` | Server $\rightarrow$ Client | `/social` | `{"items": [...], "total": <int>}`: List of watchable ongoing matches with player profiles. |

---

## 6. The 25 Board Game Engines & Spectator Safety Rules

The backend strictly enforces state sanitization boundaries:

| Game Type | Persian Title | Players | Turn Time | Rounds | Scoring Type | Spectator Classification |
|---|---|---|---|---|---|---|
| `TicTacToe` | تیک تاک تو | 2 | 10s | 5 | Round wins | **Safe** (Full board public) |
| `RPC` | سنگ کاغذ قیچی | 2 | 7s | 3 | Cumulative | **Sanitized** (Hidden pick until revealed) |
| `FekrBekr` | فکر بکر | 2 | 60s (Setup 60s) | 12 | Guess count | **Sanitized** (Secret code hidden) |
| `Yatzy` | یاتزی | 2 | 60s | 12 | Cumulative | **Safe** (Public dice & scores; 3 re-rolls) |
| `FourInRow` | دوز چهارتایی | 2 | 15s | 1 | Single | **Safe** (Full board public) |
| `Chess` | شطرنج | 2 | 20s | 1 | Single | **Safe** (Full board public) |
| `Checkers` | چکرز | 2 | 20s | 1 | Single | **Safe** (Full board public) |
| `BackGammon` | تخته نرد | 2 | 30s | 1 | Cumulative | **Safe** (Full board public) |
| `Othello` | اتللو | 2 | 20s | 1 | Piece count | **Safe** (Full board public) |
| `Mill` | دوز نه تایی | 2 | 15s | 1 | Single | **Safe** (Full board public) |
| `DotBox` | نقطه خط | 2 | 15s | 1 | Box count | **Safe** (Full board public) |
| `Pentago` | پنتاگو | 2 | 25s | 1 | Single | **Safe** (Full board public) |
| `Yinsh` | یینش | 2 | 30s (Ring 20s) | 1 | Ring points | **Safe** (Full board public) |
| `BattleShip` | نبرد کشتی | 2 | 12s (Setup 60s) | 1 | Hit points | **Sanitized** (Hidden ships masked) |
| `Sudoku` | سودوکو | 2 | 1200s | 1 | Race / Accuracy | **Safe** (Public puzzle grid) |
| `BoxFour` | چهارطرفه | 2 | 12s | 1 | Territory | **Safe** (Full board public) |
| `MNumbers` | کشف اعداد | 2 | 7s | 1 | Pair points | **Sanitized** (Immediate 1st reveal & lock) |
| `MSweeper` | مین یاب | 2 | 600s | 1 | Mine points | **Sanitized** (Unrevealed mines masked) |
| `Ludo` | منچ | 2–4 | 25s | 1 | Podium finish | **Safe** (Multiplayer surrender-tolerant) |
| `Risk` | ریسک استرایک | 2–4 | 30s (Pass 5s) | 1 | Podium finish | **Sanitized** (Defense cards, strategy hand) |
| `Monopoly` | مونوپولی | 2–4 | 28s (Resp 14s) | 1 | Wealth / Podium| **Safe** (Multiplayer surrender-tolerant) |
| `Uno` | اونو | 2–4 | 20s | 1 | Card points | **Sanitized** (Hand cards masked) |
| `Coup` | کودتا | 2–4 | 25s (Resp 12s) | 1 | Last standing | **Sanitized** (Influence cards masked) |
| `Quiz` | کوئیز | 2–4 | 15s (Wait 4s) | 10 | Answer points | **Safe** (Simultaneous trivia) |
| `Quoridor` | کریدور | 2–4 | 30s | 1 | Race to edge | **Safe** (Board & remaining walls public) |

---

## 7. Economy, Rewards & Multiplayer Podium Architecture (`RewardManagerClass`)

- **Dynamic Elo Rating (1v1 Ranked):**
  - Base K-factor of 20 with beginner protection (softer K of 12 if score < 300).
  - Clean Sweep bonus (2-0 victory earns +15% Elo boost).
  - Normal surrender treated as standard loss; full disconnect timeout or AFK incurs an increased penalty (minimum -15 score).
- **Multiplayer (>2P) Podium Rewards:**
  - Rank 1: $+12$ rating, $+50$ XP, $+25$ coins.
  - Rank 2: $+4$ rating, $+30$ XP, $+15$ coins.
  - Rank 3: $-4$ rating, $+15$ XP, $0$ coins.
  - Rank 4: $-8$ rating, $+10$ XP, $0$ coins.
  - Automatic rank deduplication: prevents identical player assignment to multiple podium positions.
- **Engagement Bonuses:**
  - Daily First Win bonus: $+15$ XP, $+15$ coins.
  - Win Streak bonus: $+8$ XP per consecutive win.
  - Clan & Social match play awards Clan XP contributing to clan level progression.

---

## 8. Configuration & Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | Port for the Socket.IO ASGI server |
| `HOST` | `0.0.0.0` | Host interface binding |
| `MONGO_URI` | `mongodb://localhost:27017/` | Connection string to MongoDB instance |
| `SECRET_KEY` | dev fallback key | Shared HS256 JWT secret and `X-Internal-Secret` for `/internal/*` endpoints |

---

## 9. Development, Testing & Deployment

### Running Unit Tests
```bash
python -m unittest discover -s tests -v
```

### Running with Docker Compose (Recommended)
From the project root:
```bash
docker compose up -d backend
```

### Running Locally with Python
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
python main.py
```

### Health Check, Internal Control & Diagnostics
- **HTTP Healthcheck:** `GET http://localhost:5000/health` -> `{"status": "ok", "service": "backend", "uptime_seconds": ...}`
- **Internal Control API (`X-Internal-Secret`):** `/internal/social/emit`, `/internal/user/in-game/{user_id}`, `/internal/auth/force-logout`, `/internal/admin/runtime-status`, `/internal/admin/games/{game_id}/force-terminate`
- **Socket.IO Handshake:** `GET http://localhost:5000/socket.io/?EIO=4&transport=polling`
