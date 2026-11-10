from Commons.static_functions import safe_run_async
import asyncio
import threading
import time

from Commons import static_functions, commands
from Commons.static_functions import make_command_json
from Controllers.QueueSession import BaseQueueSession
from Entities.Games.game_types import GameTypesEnum
from Entities.RewardManagerClass import GameScoreTypesEnum
from Models.Queuer import QueuerModel

MULTI_RANK_REQUIRED_PLAYERS = 4


class MultiRankQueueSession(BaseQueueSession):
    def __init__(self):
        super().__init__(GameScoreTypesEnum.MultiRANK)
        self.ludo_queuers: list[QueuerModel] = []
        self.risk_queuers: list[QueuerModel] = []
        self.uno_queuers: list[QueuerModel] = []
        self._lock = threading.Lock()

    @staticmethod
    def normalize_game_type(game_type) -> str:
        raw = str(game_type.value if hasattr(game_type, "value") else game_type).strip().lower()
        if raw == "ludo":
            return GameTypesEnum.LUDO.value
        if raw == "risk":
            return GameTypesEnum.RISK.value
        if raw == "uno":
            return GameTypesEnum.UNO.value
        return str(game_type)

    def _get_queue_list(self, game_type):
        norm = self.normalize_game_type(game_type)
        if norm == GameTypesEnum.LUDO.value:
            return self.ludo_queuers, GameTypesEnum.LUDO.value
        if norm == GameTypesEnum.RISK.value:
            return self.risk_queuers, GameTypesEnum.RISK.value
        if norm == GameTypesEnum.UNO.value:
            return self.uno_queuers, GameTypesEnum.UNO.value
        return None, norm

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

    def find_gamer_from_user_id(self, user_id):
        for queuer in list(self.ludo_queuers) + list(self.risk_queuers) + list(self.uno_queuers):
            if str(queuer.user_id) == str(user_id):
                return queuer
        return None

    def find_gamer_from_socket_id(self, socket_id):
        for queuer in list(self.ludo_queuers) + list(self.risk_queuers) + list(self.uno_queuers):
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def can_user_join_queue(self, user_id, socket_id=None) -> bool:
        existing_q = self.find_gamer_from_user_id(user_id)
        if existing_q is not None:
            if socket_id and existing_q.socket_id == socket_id:
                with self._lock:
                    if existing_q in self.ludo_queuers:
                        self.ludo_queuers.remove(existing_q)
                    if existing_q in self.risk_queuers:
                        self.risk_queuers.remove(existing_q)
                    if existing_q in self.uno_queuers:
                        self.uno_queuers.remove(existing_q)
            else:
                try:
                    from Entities.SocketIOClass import Socket_Server
                    if not Socket_Server.manager.is_connected(existing_q.socket_id, "/multi-queue"):
                        with self._lock:
                            if existing_q in self.ludo_queuers:
                                self.ludo_queuers.remove(existing_q)
                            if existing_q in self.risk_queuers:
                                self.risk_queuers.remove(existing_q)
                            if existing_q in self.uno_queuers:
                                self.uno_queuers.remove(existing_q)
                    else:
                        return False
                except Exception:
                    return False

        try:
            from Entities.SocketIOClass.game import games
            for g_id, game_play in list(games.items()):
                if not getattr(game_play, "is_game_finished", False) and not getattr(game_play, "is_game_terminated", False):
                    if game_play.is_user_id_valid(user_id):
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
                if queuer_data in self.ludo_queuers:
                    self.ludo_queuers.remove(queuer_data)
                if queuer_data in self.risk_queuers:
                    self.risk_queuers.remove(queuer_data)
                if queuer_data in self.uno_queuers:
                    self.uno_queuers.remove(queuer_data)

        for queuer_data in queuers:
            safe_run_async(
                send_queue_command(
                    command=make_command_json(id=commands.Start_Game, data=game_data),
                    socket_id=queuer_data.socket_id,
                    namespace='/multi-queue',
                )
            )

    def _try_matchmake_once(self) -> bool:
        ludo_match = None
        risk_match = None
        uno_match = None
        with self._lock:
            distinct_ludo = self._distinct_queuers(self.ludo_queuers)
            if len(distinct_ludo) >= MULTI_RANK_REQUIRED_PLAYERS:
                ludo_match = distinct_ludo[:MULTI_RANK_REQUIRED_PLAYERS]
                matched_uids = {str(q.user_id) for q in ludo_match}
                self.ludo_queuers = [q for q in self.ludo_queuers if str(q.user_id) not in matched_uids]

            distinct_risk = self._distinct_queuers(self.risk_queuers)
            if len(distinct_risk) >= MULTI_RANK_REQUIRED_PLAYERS:
                risk_match = distinct_risk[:MULTI_RANK_REQUIRED_PLAYERS]
                matched_uids = {str(q.user_id) for q in risk_match}
                self.risk_queuers = [q for q in self.risk_queuers if str(q.user_id) not in matched_uids]

            distinct_uno = self._distinct_queuers(self.uno_queuers)
            if len(distinct_uno) >= MULTI_RANK_REQUIRED_PLAYERS:
                uno_match = distinct_uno[:MULTI_RANK_REQUIRED_PLAYERS]
                matched_uids = {str(q.user_id) for q in uno_match}
                self.uno_queuers = [q for q in self.uno_queuers if str(q.user_id) not in matched_uids]

        started_any = False
        if ludo_match is not None:
            started_any = True
            threading.Thread(
                target=self.start_new_game,
                args=(ludo_match, GameTypesEnum.LUDO.value),
                daemon=True,
            ).start()
            self.broadcast_queue_status(GameTypesEnum.LUDO.value)

        if risk_match is not None:
            started_any = True
            threading.Thread(
                target=self.start_new_game,
                args=(risk_match, GameTypesEnum.RISK.value),
                daemon=True,
            ).start()
            self.broadcast_queue_status(GameTypesEnum.RISK.value)

        if uno_match is not None:
            started_any = True
            threading.Thread(
                target=self.start_new_game,
                args=(uno_match, GameTypesEnum.UNO.value),
                daemon=True,
            ).start()
            self.broadcast_queue_status(GameTypesEnum.UNO.value)

        return started_any

    def check_start_new_game(self):
        while True:
            started = self._try_matchmake_once()
            time.sleep(0.5 if started else 1.0)

    def join_user(self, user_data: QueuerModel, game_type) -> bool:
        norm_type = self.normalize_game_type(game_type)
        if norm_type not in (GameTypesEnum.LUDO.value, GameTypesEnum.RISK.value, GameTypesEnum.UNO.value):
            return False
        if not self.can_user_join_queue(user_data.user_id, user_data.socket_id):
            return False

        user_data.selected_game = norm_type
        with self._lock:
            self.ludo_queuers = [q for q in self.ludo_queuers if str(q.user_id) != str(user_data.user_id)]
            self.risk_queuers = [q for q in self.risk_queuers if str(q.user_id) != str(user_data.user_id)]
            self.uno_queuers = [q for q in self.uno_queuers if str(q.user_id) != str(user_data.user_id)]
            if norm_type == GameTypesEnum.LUDO.value:
                self.ludo_queuers.append(user_data)
            elif norm_type == GameTypesEnum.RISK.value:
                self.risk_queuers.append(user_data)
            elif norm_type == GameTypesEnum.UNO.value:
                self.uno_queuers.append(user_data)

        self.broadcast_queue_status(norm_type)
        self._try_matchmake_once()
        return True

    async def disconnect_user(self, socket_id):
        affected_types = []
        with self._lock:
            for user_data in list(self.ludo_queuers):
                if socket_id == user_data.socket_id:
                    self.ludo_queuers.remove(user_data)
                    affected_types.append(GameTypesEnum.LUDO.value)
                    break
            for user_data in list(self.risk_queuers):
                if socket_id == user_data.socket_id:
                    self.risk_queuers.remove(user_data)
                    affected_types.append(GameTypesEnum.RISK.value)
                    break
            for user_data in list(self.uno_queuers):
                if socket_id == user_data.socket_id:
                    self.uno_queuers.remove(user_data)
                    affected_types.append(GameTypesEnum.UNO.value)
                    break
        for gt in affected_types:
            self.broadcast_queue_status(gt)
