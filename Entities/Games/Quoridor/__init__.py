from collections import deque
from Entities.Games.base_game_class import BaseGameClass
from Commons import commands


class QuoridorGameClass(BaseGameClass):
    """
    Full 2-player Quoridor (9x9) game rules engine.

    - Player 1 starts at [8, 4] and wins by reaching row 0.
    - Player 2 starts at [0, 4] and wins by reaching row 8.
    - Each player begins with 10 walls on an 8x8 interior intersection grid (0..7, 0..7).
    - Horizontal wall ('H') at (wr, wc) blocks vertical movement between:
        (wr, wc) <-> (wr+1, wc) and (wr, wc+1) <-> (wr+1, wc+1)
    - Vertical wall ('V') at (wr, wc) blocks horizontal movement between:
        (wr, wc) <-> (wr, wc+1) and (wr+1, wc) <-> (wr+1, wc+1)
    - Enforces orthogonal moves, straight jump over adjacent opponent,
      diagonal sidesteps when directly behind opponent is blocked,
      wall bounds/overlap/crossing checks, and BFS reachability for BOTH players.
    """

    BOARD_SIZE = 9
    WALL_GRID_SIZE = 8
    INITIAL_WALLS = 10

    def __init__(self, send_data_function):
        super().__init__(send_data_function)
        self.pawns = {1: [8, 4], 2: [0, 4]}
        self.walls_left = {1: self.INITIAL_WALLS, 2: self.INITIAL_WALLS}
        self.h_walls = []  # list of [wr, wc]
        self.v_walls = []  # list of [wr, wc]
        self._h_set = set()
        self._v_set = set()
        self.winner_id = 0
        self.current_round = 0
        self.current_turn = 0
        self.is_current_turn_played = False
        self.last_move = {}

    def get_game_data(self):
        return {
            "game_type": "Quoridor",
            "board_size": self.BOARD_SIZE,
            "pawns": [list(self.pawns[1]), list(self.pawns[2])],
            "walls_left": [int(self.walls_left[1]), int(self.walls_left[2])],
            "h_walls": [list(w) for w in self.h_walls],
            "v_walls": [list(w) for w in self.v_walls],
            "current_turn": int(self.current_turn),
            "winner": int(self.winner_id),
            "last_move": dict(self.last_move) if self.last_move else {},
        }

    def _is_blocked(self, r1: int, c1: int, r2: int, c2: int, h_set=None, v_set=None) -> bool:
        if not (0 <= r2 < self.BOARD_SIZE and 0 <= c2 < self.BOARD_SIZE):
            return True
        if h_set is None:
            h_set = self._h_set
        if v_set is None:
            v_set = self._v_set
        dr = r2 - r1
        dc = c2 - c1
        if abs(dr) + abs(dc) != 1:
            return True
        if dr == -1:  # moving North (r1 -> r1-1) crosses horizontal gap r1-1
            wr = r1 - 1
            return (wr, c1) in h_set or (wr, c1 - 1) in h_set
        if dr == 1:   # moving South (r1 -> r1+1) crosses horizontal gap r1
            wr = r1
            return (wr, c1) in h_set or (wr, c1 - 1) in h_set
        if dc == -1:  # moving West (c1 -> c1-1) crosses vertical gap c1-1
            wc = c1 - 1
            return (r1, wc) in v_set or (r1 - 1, wc) in v_set
        if dc == 1:   # moving East (c1 -> c1+1) crosses vertical gap c1
            wc = c1
            return (r1, wc) in v_set or (r1 - 1, wc) in v_set
        return True

    def get_legal_pawn_moves(self, gamer_id: int) -> list:
        r, c = self.pawns[gamer_id]
        opp_id = 2 if gamer_id == 1 else 1
        orow, ocol = self.pawns[opp_id]
        legal = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if self._is_blocked(r, c, nr, nc):
                continue
            if nr == orow and nc == ocol:
                # Try straight jump behind opponent
                jr, jc = nr + dr, nc + dc
                if not self._is_blocked(nr, nc, jr, jc):
                    legal.append([jr, jc])
                else:
                    # Blocked directly behind opponent -> diagonal sidesteps
                    if dr != 0:
                        for sc in (-1, 1):
                            sr, sc_col = nr, nc + sc
                            if not self._is_blocked(nr, nc, sr, sc_col):
                                legal.append([sr, sc_col])
                    else:
                        for sr_off in (-1, 1):
                            sr, sc_col = nr + sr_off, nc
                            if not self._is_blocked(nr, nc, sr, sc_col):
                                legal.append([sr, sc_col])
            else:
                legal.append([nr, nc])
        return legal

    def _has_path_to_goal(self, start_rc, goal_row: int, h_set, v_set) -> bool:
        sr, sc = start_rc
        if sr == goal_row:
            return True
        visited = {(sr, sc)}
        q = deque([(sr, sc)])
        while q:
            r, c = q.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if (nr, nc) in visited:
                    continue
                if self._is_blocked(r, c, nr, nc, h_set=h_set, v_set=v_set):
                    continue
                if nr == goal_row:
                    return True
                visited.add((nr, nc))
                q.append((nr, nc))
        return False

    def can_place_wall(self, gamer_id: int, wr: int, wc: int, orientation: str) -> bool:
        if self.walls_left.get(gamer_id, 0) <= 0:
            return False
        if not (0 <= wr < self.WALL_GRID_SIZE and 0 <= wc < self.WALL_GRID_SIZE):
            return False
        ori = str(orientation).upper()
        if ori not in ("H", "V"):
            return False

        # Cannot cross perpendicular wall at exact same intersection center
        if (wr, wc) in self._h_set or (wr, wc) in self._v_set:
            return False

        if ori == "H":
            if (wr, wc - 1) in self._h_set or (wr, wc + 1) in self._h_set:
                return False
            new_h = self._h_set | {(wr, wc)}
            new_v = self._v_set
        else:
            if (wr - 1, wc) in self._v_set or (wr + 1, wc) in self._v_set:
                return False
            new_h = self._h_set
            new_v = self._v_set | {(wr, wc)}

        # Both players must still have a valid path to their goal rows
        if not self._has_path_to_goal(self.pawns[1], 0, new_h, new_v):
            return False
        if not self._has_path_to_goal(self.pawns[2], self.BOARD_SIZE - 1, new_h, new_v):
            return False
        return True

    def _parse_action(self, raw_data):
        if isinstance(raw_data, dict):
            action = str(raw_data.get("action", "")).strip().lower()
            if not action:
                if "orientation" in raw_data:
                    action = "wall"
                else:
                    action = "move"
            if action == "move":
                if "row" in raw_data and "col" in raw_data:
                    return ("move", int(raw_data["row"]), int(raw_data["col"]), "")
                if "index" in raw_data or "target_peace" in raw_data:
                    idx = int(raw_data.get("index", raw_data.get("target_peace", -1)))
                    if 0 <= idx < self.BOARD_SIZE * self.BOARD_SIZE:
                        return ("move", idx // self.BOARD_SIZE, idx % self.BOARD_SIZE, "")
            elif action == "wall":
                if "row" in raw_data and "col" in raw_data:
                    wr = int(raw_data["row"])
                    wc = int(raw_data["col"])
                    ori = str(raw_data.get("orientation", "")).strip().upper()
                    if ori in ("H", "V"):
                        return ("wall", wr, wc, ori)
                if "wall_row" in raw_data and "wall_col" in raw_data:
                    wr = int(raw_data["wall_row"])
                    wc = int(raw_data["wall_col"])
                    ori = str(raw_data.get("orientation", "")).strip().upper()
                    if ori in ("H", "V"):
                        return ("wall", wr, wc, ori)
        elif isinstance(raw_data, (int, str)):
            try:
                val = int(raw_data)
                if 0 <= val < self.BOARD_SIZE * self.BOARD_SIZE:
                    return ("move", val // self.BOARD_SIZE, val % self.BOARD_SIZE, "")
            except (ValueError, TypeError):
                pass
        return None

    def check_authority(self, data, gamer_id):
        if self.is_game_finished or gamer_id != self.current_turn:
            return False
        parsed = self._parse_action(data)
        if parsed is None:
            return False
        action, r, c, ori = parsed
        if action == "move":
            return [r, c] in self.get_legal_pawn_moves(gamer_id)
        if action == "wall":
            return self.can_place_wall(gamer_id, r, c, ori)
        return False

    async def recieve_data(self, command_id, data, gamer_id):
        if command_id != commands.Select_Peace:
            return False
        parsed = self._parse_action(data)
        if parsed is None:
            return False
        action, r, c, ori = parsed

        if action == "move":
            if [r, c] not in self.get_legal_pawn_moves(gamer_id):
                return False
            self.pawns[gamer_id] = [r, c]
            goal_row = 0 if gamer_id == 1 else (self.BOARD_SIZE - 1)
            if r == goal_row:
                self.is_game_finished = True
                self.winner_id = gamer_id
            target_peace = r * self.BOARD_SIZE + c
        elif action == "wall":
            if not self.can_place_wall(gamer_id, r, c, ori):
                return False
            self.walls_left[gamer_id] -= 1
            if ori == "H":
                self.h_walls.append([r, c])
                self._h_set.add((r, c))
            else:
                self.v_walls.append([r, c])
                self._v_set.add((r, c))
            target_peace = -1
        else:
            return False

        self.is_current_turn_played = True
        self.last_move = {
            "gamer_id": int(gamer_id),
            "action": action,
            "row": int(r),
            "col": int(c),
            "orientation": ori,
        }

        payload = {
            "gamer_id": int(gamer_id),
            "user": int(gamer_id),
            "target_peace": int(target_peace),
            "action": action,
            "row": int(r),
            "col": int(c),
            "orientation": ori,
            "pawns": [list(self.pawns[1]), list(self.pawns[2])],
            "walls_left": [int(self.walls_left[1]), int(self.walls_left[2])],
            "h_walls": [list(w) for w in self.h_walls],
            "v_walls": [list(w) for w in self.v_walls],
            "winner": int(self.winner_id),
        }
        await self.send_data_function(commands.Peace_Selected, payload)
        return True

    def check_game_ended(self):
        return self.is_game_finished

    def get_game_winner(self):
        winner = super().get_game_winner()
        if winner == 0:
            winner = self.winner_id
        return winner

    def change_turn(self):
        self.current_round += 1
        if self.current_turn == 0:
            self.current_turn = 1
        elif self.current_turn == 1:
            self.current_turn = 2
        else:
            self.current_turn = 1
        self.is_current_turn_played = False
