from Commons.static_functions import safe_run_async
import threading
import time

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

MULTI_RANK_REQUIRED_PLAYERS = 4

_MULTI_RANK_ALIASES = {
    "ludo": GameTypesEnum.LUDO.value,
    "risk": GameTypesEnum.RISK.value,
    "uno": GameTypesEnum.UNO.value,
    "quiz": GameTypesEnum.QUIZ.value,
    "coup": GameTypesEnum.COUP.value,
    "کودتا": GameTypesEnum.COUP.value,
    "monopoly": GameTypesEnum.MONOPOLY.value,
    "مونوپولی": GameTypesEnum.MONOPOLY.value,
    "منوپولی": GameTypesEnum.MONOPOLY.value,
}


class MultiRankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.MultiRANK)
        self.ludo_queuers: list[QueuerModel] = []
        self.risk_queuers: list[QueuerModel] = []
        self.uno_queuers: list[QueuerModel] = []
        self.quiz_queuers: list[QueuerModel] = []
        self.coup_queuers: list[QueuerModel] = []
        self.monopoly_queuers: list[QueuerModel] = []
        # Shared mapping referencing the same list objects for uniform queue operations
        self._queues_by_type: dict[str, list[QueuerModel]] = {
            GameTypesEnum.LUDO.value: self.ludo_queuers,
            GameTypesEnum.RISK.value: self.risk_queuers,
            GameTypesEnum.UNO.value: self.uno_queuers,
            GameTypesEnum.QUIZ.value: self.quiz_queuers,
            GameTypesEnum.COUP.value: self.coup_queuers,
            GameTypesEnum.MONOPOLY.value: self.monopoly_queuers,
        }
        self._lock = threading.Lock()

    @staticmethod
    def normalize_game_type(game_type) -> str:
        raw = str(game_type.value if hasattr(game_type, "value") else game_type).strip().lower()
        return _MULTI_RANK_ALIASES.get(raw, str(game_type))

    def _get_queue_list(self, game_type):
        norm = self.normalize_game_type(game_type)
        return self._queues_by_type.get(norm), norm

    @staticmethod
    def _distinct_queuers(queuer_list: list[QueuerModel]) -> list[QueuerModel]:
        distinct = []
        seen_uids = set()
        for q in list(queuer_list):
            uid_s = str(q.user_id)
            if uid_s not in seen_uids:
                seen_uids.add(uid_s)
                distinct.append(q)
        return distinct

    def _remove_queuer_from_all_locked(self, queuer: QueuerModel) -> None:
        for q_list in self._queues_by_type.values():
            if queuer in q_list:
                q_list.remove(queuer)

    def find_gamer_from_user_id(self, user_id):
        uid_str = str(user_id)
        with self._lock:
            for q_list in self._queues_by_type.values():
                for queuer in q_list:
                    if str(queuer.user_id) == uid_str:
                        return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        if not socket_id:
            return None
        with self._lock:
            for q_list in self._queues_by_type.values():
                for queuer in q_list:
                    if queuer.socket_id == socket_id:
                        return queuer
        return None

    def can_user_join_queue(self, user_id, socket_id=None) -> bool:
        existing_q = self.find_gamer_from_user_id(user_id)
        if existing_q is not None:
            if socket_id and existing_q.socket_id == socket_id:
                with self._lock:
                    self._remove_queuer_from_all_locked(existing_q)
            else:
                try:
                    from Entities.SocketIOClass import Socket_Server
                    if not Socket_Server.manager.is_connected(existing_q.socket_id, "/multi-queue"):
                        with self._lock:
                            self._remove_queuer_from_all_locked(existing_q)
                    else:
                        return False
                except Exception:
                    return False

        try:
            from Entities.SocketIOClass.game import games
            for _g_id, game_play in list(games.items()):
                if not getattr(game_play, "is_game_finished", False) and not getattr(game_play, "is_game_terminated", False):
                    is_active_fn = getattr(game_play, "is_user_active_in_game", game_play.is_user_id_valid)
                    if is_active_fn(user_id):
                        return False
        except Exception:
            pass

        return True

    def broadcast_queue_status(self, game_type):
        queue_list, norm_type = self._get_queue_list(game_type)
        if queue_list is None:
            return
        with self._lock:
            distinct = self._distinct_queuers(queue_list)
        if not distinct:
            return
        status_payload = {
            "game_type": norm_type,
            "queuers_count": min(MULTI_RANK_REQUIRED_PLAYERS, len(distinct)),
            "required_count": MULTI_RANK_REQUIRED_PLAYERS,
            "queuers": [q.to_json() for q in distinct[:MULTI_RANK_REQUIRED_PLAYERS]],
        }
        from Entities.SocketIOManagerClass import send_queue_command
        for q in distinct:
            if q.socket_id:
                safe_run_async(
                    send_queue_command(
                        command=make_command_json(id="Queue_Status", data=status_payload),
                        socket_id=q.socket_id,
                        namespace='/multi-queue',
                    )
                )

    async def command_received(self, data, socket_id):
        from Entities.SocketIOManagerClass import send_global_command
        if not isinstance(data, dict):
            return
        cmd_id = data.get('id')
        if cmd_id == commands.Message:
            gamer = self.find_gamer_from_socket_id(socket_id)
            if gamer is None:
                return
            send_data = {'name': gamer.username, 'content': data.get('content', ''), 'id': gamer.user_id}
            await send_global_command(command=make_command_json(id=commands.Message, data=send_data))
        elif cmd_id in ("Leave_Queue", "leave_queue", "Cancel_Queue"):
            await self.disconnect_user(socket_id)

    def start_new_game(self, queuers, game_type):
        from Entities.SocketIOManagerClass import send_queue_command

        norm_type = self.normalize_game_type(game_type)
        game_id = static_functions.create_random_game_id()
        final_game_types = [norm_type]
        game_data = {
            'game_id': game_id,
            'game_type': norm_type,
            'players_count': len(queuers),
            'queuers': [q.to_json() for q in queuers],
        }

        from Entities.SocketIOClass.game import add_new_game
        add_new_game(game_id, queuers, final_game_types, self.game_score_type)

        with self._lock:
            for queuer_data in queuers:
                self._remove_queuer_from_all_locked(queuer_data)

        for queuer_data in queuers:
            safe_run_async(
                send_queue_command(
                    command=make_command_json(id=commands.Start_Game, data=game_data),
                    socket_id=queuer_data.socket_id,
                    namespace='/multi-queue',
                )
            )

    def _try_matchmake_once(self) -> bool:
        matches: list[tuple[str, list[QueuerModel]]] = []
        with self._lock:
            for game_type_val, q_list in self._queues_by_type.items():
                distinct = self._distinct_queuers(q_list)
                if len(distinct) >= MULTI_RANK_REQUIRED_PLAYERS:
                    matched = distinct[:MULTI_RANK_REQUIRED_PLAYERS]
                    matched_uids = {str(q.user_id) for q in matched}
                    # Mutate in-place so attribute aliases (e.g. self.ludo_queuers) stay synchronized
                    q_list[:] = [q for q in q_list if str(q.user_id) not in matched_uids]
                    matches.append((game_type_val, matched))

        for game_type_val, matched in matches:
            threading.Thread(
                target=self.start_new_game,
                args=(matched, game_type_val),
                daemon=True,
            ).start()
            self.broadcast_queue_status(game_type_val)

        return bool(matches)

    def check_start_new_game(self):
        while True:
            started = self._try_matchmake_once()
            time.sleep(0.5 if started else 1.0)

    def join_user(self, user_data: QueuerModel, game_type) -> bool:
        norm_type = self.normalize_game_type(game_type)
        target_list = self._queues_by_type.get(norm_type)
        if target_list is None:
            return False
        if not self.can_user_join_queue(user_data.user_id, user_data.socket_id):
            return False

        user_data.selected_game = norm_type
        uid_str = str(user_data.user_id)
        with self._lock:
            for q_list in self._queues_by_type.values():
                q_list[:] = [q for q in q_list if str(q.user_id) != uid_str]
            target_list.append(user_data)

        self.broadcast_queue_status(norm_type)
        self._try_matchmake_once()
        return True

    async def disconnect_user(self, socket_id):
        affected_types = []
        with self._lock:
            for game_type_val, q_list in self._queues_by_type.items():
                for user_data in list(q_list):
                    if socket_id == user_data.socket_id:
                        q_list.remove(user_data)
                        affected_types.append(game_type_val)
                        break
        for gt in affected_types:
            self.broadcast_queue_status(gt)
