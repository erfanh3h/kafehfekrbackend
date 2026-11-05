import asyncio
import random
import threading
import time

from Commons import commands
from Commons.static_functions import make_command_json, safe_run_async
from Controllers.GamePlay.game_type_class_pairs import game_type_class_pairs
from Entities.Games.wait_times import Join_Game_Limit_Time, Start_Game_Time, Game_Play_Round_Time
from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum
from Entities.TimerClass import TimerClass
from Models.Gamer import GamerModel


class BaseGamePlayClass:
    def __init__(self, game_play_id, gamers, game_types, game_score_type):
        self.timer = TimerClass()
        self.game_play_id = game_play_id
        self.gamers = gamers
        for g in self.gamers:
            g.socket_id = ""
            g.is_disconnected = False
        self.has_connected_once: set[str] = set()
        self.active_user_sockets: dict[str, str] = {}
        self.disconnected_user_ids: set[str] = set()
        self.game_types = game_types
        self.game_score_type = game_score_type
        self.game_session = None
        self.gamer_scores = [0 for g in gamers]
        # self.gamer1_score = 0
        # self.gamer2_score = 0
        self.current_game_index = 0
        self.game_winners = []
        self.is_gamers_join_game = {}
        self.is_game_started = False
        self.is_game_running = False
        self.is_game_terminated = False
        self.is_game_finished = False
        self.active_game_id = ""
        self.game_winner_id = None
        self.afk_or_dc_penalty_user_id = None
        self.score_manager = RewardManagerClass(game_score_type)

    def select_random_games(self):
        if self.game_score_type == GameScoreTypesEnum.RANK:
            games_length = 3
            self.game_winners = [-1, -1, -1]
        else:
            games_length = 1
            self.game_winners = [-1]
        if len(self.game_types) == games_length:
            self.game_types = list(self.game_types)
            return
        games_types = []
        for i in range(min(games_length, len(self.game_types))):
            random_type = random.choice(self.game_types)
            games_types.append(random_type)
            self.game_types.remove(random_type)
        self.game_types = games_types
        random.shuffle(self.game_types)

    def prepare_database(self):
        from Entities.Database import game_database
        user_idis = [g.user_id for g in self.gamers]
        self.score_manager.set_user_data(user_idis)
        game_database.game_play_history_manager.delete_game_play_history(self.game_play_id)
        users_info = []
        for g in self.gamers:
            users_info.append({
                "user_id": str(g.user_id),
                "username": getattr(g, "username", getattr(g, "name", "")),
                "image": int(getattr(g, "user_image", getattr(g, "image", 0))),
                "score": int(getattr(g, "user_score", getattr(g, "score", 0))),
            })
        score_val = self.game_score_type.value if hasattr(self.game_score_type, "value") else str(self.game_score_type)
        game_database.game_play_history_manager.create_game_play_history(
            self.game_play_id, user_idis, self.game_types, score_val, users_info=users_info
        )
        for user_id in user_idis:
            if not str(user_id).startswith("bot_"):
                game_database.users_manager.update_user(user_id, open_game_id=self.game_play_id)

    def join_game_limit_time(self):
        if not self.is_game_started:
            self.is_game_terminated = True

    def start_game_timer(self):
        user_idis = [g.user_id for g in self.gamers]
        for user_id in user_idis:
            self.is_gamers_join_game[user_id] = False

        def entrypoint():
            self.check_start_game()

        self.timer.start(Join_Game_Limit_Time, self.join_game_limit_time)
        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def check_all_players_joined(self):
        if not self.is_gamers_join_game:
            return False
        for is_gamer_joined in self.is_gamers_join_game.values():
            if not is_gamer_joined:
                return False
        return True

    def send_game_play_data(self, socket_id):
        is_between = (self.game_session is None or self.game_session.is_game_finished) and not self.is_game_finished
        game_data = {'gamers': [], 'games': self.game_types, 'game_score_type': self.game_score_type.value,
                     'current_game_index': self.current_game_index, 'winners': self.game_winners,
                     'is_game_finished': self.is_game_finished, 'is_between_games': is_between,
                     'scores': self.gamer_scores,
                     'game_winner_id': self.game_winner_id,
                     'xp_awarded': getattr(self.score_manager, 'last_awarded_xp', {}),
                     'score_awarded': getattr(self.score_manager, 'last_awarded_score', {}),
                     'coin_awarded': getattr(self.score_manager, 'last_awarded_coin', {})}
        session_gamer_map = {}
        if self.game_session is not None:
            for sg in getattr(self.game_session, 'gamers', []):
                if getattr(sg, 'gamer_id', 0) > 0:
                    session_gamer_map[str(sg.user_id)] = sg.gamer_id
        for gamer in self.gamers:
            g_json = gamer.to_json()
            if str(gamer.user_id) in session_gamer_map:
                g_json['gamer_id'] = session_gamer_map[str(gamer.user_id)]
                g_json['team_id'] = session_gamer_map[str(gamer.user_id)]
            game_data['gamers'].append(g_json)
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(command=make_command_json(id=commands.Game_Play_Data, data=game_data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def navigate_to_game(self, socket_id, is_reconnect=False):
        game_data = {'current_game_index': self.current_game_index, 'games': self.game_types, 'is_reconnect': is_reconnect}
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(command=make_command_json(id=commands.Game_Play_Navigate, data=game_data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def send_timer_value(self, socket_id):
        max_t = self.timer.max_time if self.timer.max_time > 0 else Game_Play_Round_Time
        rem_t = max(1, max_t - self.timer.counter)
        data = {'time': rem_t, 'max_time': max_t}
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(command=make_command_json(id=commands.Game_Play_Time, data=data),
                                 game_id=self.game_play_id, socket_id=socket_id))

    def check_start_game(self):
        def start_new_game_function():
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id, is_reconnect=False)
            self.start_current_game()

        while True:
            if self.is_game_terminated:
                self.is_game_finished = True
                from Entities.SocketIOClass.game import delete_game
                delete_game(self.game_play_id)
                break
            if self.check_all_players_joined():
                time.sleep(0.3)
                self.is_game_started = True
                self.timer.stop(False)
                self.select_random_games()
                self.prepare_database()
                for gamer in self.gamers:
                    self.send_game_play_data(gamer.socket_id)
                start_new_game_function()
                break
            time.sleep(0.3)

    def can_user_join_or_reconnect(self, user_id, socket_id) -> bool:
        if self.is_game_finished or self.is_game_terminated:
            return False
        if not self.is_user_id_valid(user_id):
            return False
        uid_str = str(user_id)
        # First time joining this game session
        if uid_str not in self.has_connected_once:
            return True
        # Same socket that was already registered
        active_sid = self.active_user_sockets.get(uid_str, "")
        if active_sid == socket_id and uid_str not in self.disconnected_user_ids:
            return True
        # Already joined before: ONLY allow reconnect if the user was disconnected
        session_gamer = None
        if self.game_session is not None and hasattr(self.game_session, "gamers"):
            for sg in self.game_session.gamers:
                if str(sg.user_id) == uid_str:
                    session_gamer = sg
                    break
        is_socket_alive = False
        if active_sid:
            try:
                from Entities.SocketIOManagerClass import Socket_Server
                is_socket_alive = bool(Socket_Server.manager.is_connected(active_sid, "/game"))
            except Exception:
                is_socket_alive = True
        is_marked_disconnected = (
            uid_str in self.disconnected_user_ids
            or not active_sid
            or not is_socket_alive
            or (session_gamer is not None and getattr(session_gamer, "is_disconnected", False))
        )
        if not is_marked_disconnected:
            return False
        return True

    def register_user_connection(self, user_id, socket_id):
        uid_str = str(user_id)
        self.has_connected_once.add(uid_str)
        self.active_user_sockets[uid_str] = socket_id
        self.disconnected_user_ids.discard(uid_str)
        self.change_gamer_socket_id(user_id, socket_id)
        for gamer in self.gamers:
            if str(gamer.user_id) == uid_str:
                gamer.is_disconnected = False
                break

    def is_active_socket_for_user(self, user_id, socket_id) -> bool:
        if not socket_id:
            return False
        return self.active_user_sockets.get(str(user_id)) == socket_id

    def is_active_socket(self, socket_id) -> bool:
        if not socket_id:
            return False
        return socket_id in self.active_user_sockets.values()

    def join_gamer(self, user_id, socket_id):
        if not self.can_user_join_or_reconnect(user_id, socket_id):
            return False
        self.register_user_connection(user_id, socket_id)
        if self.is_game_started:
            self.send_game_play_data(socket_id)
            if self.game_session is not None:
                if self.game_session.is_game_running:
                    self.navigate_to_game(socket_id, is_reconnect=True)
                self.game_session.join_gamer(user_id, socket_id)
            elif not self.is_game_finished:
                self.send_timer_value(socket_id)
        else:
            for g in self.gamers:
                if str(g.user_id) == str(user_id):
                    self.is_gamers_join_game[g.user_id] = True
                    break
            else:
                self.is_gamers_join_game[user_id] = True
        return True

    async def command_received(self, data, socket_id):
        if not self.is_active_socket(socket_id):
            return
        if isinstance(data, dict) and data.get('id') in [commands.Reconnect_Data, "RequestReconnectData", "reconnect_data"]:
            if self.game_session is not None:
                self.game_session.send_reconnect_data(socket_id)
            return
        if isinstance(data, dict) and data.get('id') == commands.Surrender:
            if self.game_session is None or getattr(self.game_session, 'is_game_finished', False):
                # Surrender occurred between games in a series or before game_session initialized
                surrender_user_id = None
                for gamer in self.gamers:
                    if gamer.socket_id == socket_id:
                        surrender_user_id = gamer.user_id
                        break
                if surrender_user_id is None:
                    return
                winner_user_id = 0
                for gamer in self.gamers:
                    if str(gamer.user_id) != str(surrender_user_id):
                        winner_user_id = gamer.user_id
                        break
                # Surrender is a normal loss - NO AFK/DC penalty!
                self.timer.stop(False)
                self.finish_game_play(winner_user_id)
                return
        if self.game_session is not None:
            await self.game_session.command_received(data, socket_id)

    def disconnect_user(self, socket_id):
        disconnected_uid = None
        for uid_str, active_sid in list(self.active_user_sockets.items()):
            if active_sid == socket_id:
                disconnected_uid = uid_str
                self.active_user_sockets[uid_str] = ""
                self.disconnected_user_ids.add(uid_str)
                break
        if disconnected_uid is None:
            # Ignore disconnect from duplicate/rejected socket
            return
        for gamer in self.gamers:
            if str(gamer.user_id) == disconnected_uid:
                gamer.is_disconnected = True
                gamer.socket_id = ""
                if not self.is_game_started:
                    self.is_gamers_join_game[gamer.user_id] = False
                break
        if self.game_session is not None:
            self.game_session.disconnect_user(socket_id)

    async def reaction_received(self, data, socket_id):
        if not self.is_active_socket(socket_id):
            return
        if self.game_session is not None:
            await self.game_session.reaction_received(data, socket_id)

    def start_current_game(self):
        if self.is_game_finished or self.current_game_index >= len(self.game_types):
            return
        game_type = self.game_types[self.current_game_index]
        self.game_session = game_type_class_pairs[game_type](game_id=self.game_play_id, game_type=game_type,
                                                              game_score_type=self.game_score_type)
        for gamer in self.gamers:
            self.game_session.add_gamer(
                GamerModel(user_id=gamer.user_id, username=gamer.username, user_image=gamer.user_image,
                           user_score=gamer.user_score, user_coin=gamer.user_coin))
            self.game_session.join_gamer(gamer.user_id, gamer.socket_id)
            if getattr(gamer, "is_disconnected", False) or str(gamer.user_id) in self.disconnected_user_ids:
                for sg in self.game_session.gamers:
                    if str(sg.user_id) == str(gamer.user_id):
                        sg.is_disconnected = True
                        break
        self.game_session.start_game_timer()

    def is_user_id_valid(self, user_id):
        for user_data in self.gamers:
            if str(user_data.user_id) == str(user_id):
                return True
        return False

    def check_is_game_finished(self):
        for index, gamer_score in enumerate(self.gamer_scores):
            if len(self.game_types) == 1 and gamer_score == 1:
                return True, self.gamers[index].user_id
            if len(self.game_types) == 3 and gamer_score >= 2:
                return True, self.gamers[index].user_id
        if self.current_game_index >= len(self.game_types):
            if len(self.gamer_scores) >= 2:
                if self.gamer_scores[0] > self.gamer_scores[1]:
                    return True, self.gamers[0].user_id
                elif self.gamer_scores[1] > self.gamer_scores[0]:
                    return True, self.gamers[1].user_id
            return True, 0
        return False, None

    def finish_current_game(self, currnet_game_winner_id):
        if self.is_game_finished:
            return
        if self.game_session is not None:
            self.game_session.is_game_finished = True
            try:
                self.game_session.timer.stop(False)
            except Exception:
                pass
            # ONLY penalize if full disconnect timeout occurred (1 min expired) or detected as AFK (2 consecutive missed turns)
            afk_uid = getattr(self.game_session, 'afk_user_id', None)
            dc_uid = getattr(self.game_session, 'dc_timeout_user_id', None)
            if afk_uid is not None:
                self.afk_or_dc_penalty_user_id = afk_uid
            elif dc_uid is not None:
                self.afk_or_dc_penalty_user_id = dc_uid
            else:
                for sg in getattr(self.game_session, 'gamers', []):
                    if getattr(sg, 'not_played_turns', 0) >= 2:
                        self.afk_or_dc_penalty_user_id = sg.user_id
                        break

        def start_new_game_function():
            if self.is_game_finished or self.current_game_index >= len(self.game_types):
                return
            for gamer_data in self.gamers:
                self.navigate_to_game(gamer_data.socket_id, is_reconnect=False)
            self.start_current_game()

        winner_index = self.user_id_to_index(currnet_game_winner_id)
        if self.current_game_index < len(self.game_winners):
            if winner_index != -1:  # prevent drow
                self.gamer_scores[winner_index] += 1
                self.game_winners[self.current_game_index] = winner_index + 1
            else:
                self.game_winners[self.current_game_index] = 0
        self.current_game_index += 1
        is_game_finished, winner_id = self.check_is_game_finished()
        if is_game_finished:
            self.finish_game_play(winner_id)
        else:
            for gamer in self.gamers:
                self.send_game_play_data(gamer.socket_id)
            self.timer.start(Game_Play_Round_Time, start_new_game_function)
            for gamer in self.gamers:
                self.send_timer_value(gamer.socket_id)

    def finish_multiplayer_game(self, rank1_id, rank2_id):
        self.game_winners = []
        rank1_index = self.user_id_to_index(rank1_id)
        if rank1_index != -1:
            self.gamer_scores[rank1_index] = 2
            self.game_winners.append(rank1_index + 1)
        rank2_index = self.user_id_to_index(rank2_id)
        if rank2_index != -1:
            self.gamer_scores[rank2_index] = 1
            self.game_winners.append(rank2_index + 1)
        from Entities.Database import game_database
        finished_game_types = [self.game_types[0]]
        try:
            self.score_manager.finish_multiplayer_game(rank1_id, rank2_id, finished_game_types)
        except Exception as e:
            print(f"[BaseGamePlayClass] Error in score_manager.finish_multiplayer_game: {e}")
        for gamer in self.gamers:
            if not str(gamer.user_id).startswith("bot_"):
                try:
                    game_database.users_manager.update_user(gamer.user_id, open_game_id="")
                except Exception as e:
                    print(f"[BaseGamePlayClass] Error clearing open_game_id for {gamer.user_id}: {e}")
        try:
            game_database.game_play_history_manager.update_game_play_history(
                self.game_play_id, self.game_winners, self.gamer_scores, winner_id=rank1_id
            )
        except Exception as e:
            print(f"[BaseGamePlayClass] Error updating game_play_history: {e}")
        self.is_game_finished = True
        self.game_winner_id = rank1_id
        rank1_gid = self.game_session.find_gamer_id_from_user_id(rank1_id) if self.game_session is not None else 0
        rank2_gid = self.game_session.find_gamer_id_from_user_id(rank2_id) if self.game_session is not None else 0
        from Entities.SocketIOManagerClass import send_private_command
        last_xp = getattr(self.score_manager, "last_awarded_xp", {})
        last_score = getattr(self.score_manager, "last_awarded_score", {})
        last_coin = getattr(self.score_manager, "last_awarded_coin", {})
        for gamer in self.gamers:
            self.send_game_play_data(gamer.socket_id)
            if gamer.socket_id:
                try:
                    earned = last_xp.get(gamer.user_id, 0)
                    s_earned = last_score.get(gamer.user_id, 0)
                    c_earned = last_coin.get(gamer.user_id, 0)
                    safe_run_async(
                        send_private_command(
                            command=make_command_json(
                                id=commands.Finish_Game,
                                data={
                                    "rank1": rank1_gid,
                                    "rank2": rank2_gid,
                                    "Winner": rank1_gid,
                                    "winner": rank1_gid,
                                    "game_winner_id": rank1_id,
                                    "series_scores": self.gamer_scores,
                                    "xp_earned": earned,
                                    "score_earned": s_earned,
                                    "coin_earned": c_earned,
                                }
                            ),
                            socket_id=gamer.socket_id,
                            game_id=self.game_play_id
                        )
                    )
                except Exception as e:
                    print(f"[BaseGamePlayClass] Error sending multiplayer Finish_Game: {e}")
        from Entities.SocketIOClass.game import delete_game
        try:
            delete_game(self.game_play_id)
        except Exception as e:
            print(f"[BaseGamePlayClass] Error deleting game {self.game_play_id}: {e}")

    def change_gamer_socket_id(self, user_id, socket_id):
        for gamer in self.gamers:
            if str(gamer.user_id) == str(user_id):
                gamer.socket_id = socket_id
                break
        if self.game_session is not None:
            for sg in getattr(self.game_session, 'gamers', []):
                if str(sg.user_id) == str(user_id):
                    sg.socket_id = socket_id
                    break

    def finish_game_play(self, winner_id, afk_or_dc_user_id=None):
        from Entities.Database import game_database
        finished_game_types = []
        finished_game_winners = []
        for index, item in enumerate(self.game_types):
            if self.game_winners[index] != -1:
                finished_game_types.append(item)
                finished_game_winners.append(self.game_winners[index])
        w_idx_lookup = self.user_id_to_index(winner_id) if (winner_id != 0 and winner_id is not None) else -1
        winner_idx = (w_idx_lookup + 1) if w_idx_lookup != -1 else 0
        penalty_user = afk_or_dc_user_id or self.afk_or_dc_penalty_user_id
        try:
            self.score_manager.finish_game(
                winner_idx,
                finished_game_types,
                finished_game_winners,
                gamer_scores=self.gamer_scores,
                afk_or_dc_user_id=penalty_user
            )
        except Exception as e:
            print(f"[BaseGamePlayClass] Error in score_manager.finish_game: {e}")
        for gamer in self.gamers:
            if not str(gamer.user_id).startswith("bot_"):
                try:
                    game_database.users_manager.update_user(gamer.user_id, open_game_id="")
                except Exception as e:
                    print(f"[BaseGamePlayClass] Error clearing open_game_id for {gamer.user_id}: {e}")
        try:
            game_database.game_play_history_manager.update_game_play_history(
                self.game_play_id, self.game_winners, self.gamer_scores, winner_id=winner_id
            )
        except Exception as e:
            print(f"[BaseGamePlayClass] Error updating game_play_history: {e}")
        self.is_game_finished = True
        self.game_winner_id = winner_id

        from Entities.SocketIOManagerClass import send_private_command
        last_xp = getattr(self.score_manager, 'last_awarded_xp', {})
        last_score = getattr(self.score_manager, 'last_awarded_score', {})
        last_coin = getattr(self.score_manager, 'last_awarded_coin', {})

        client_winner = winner_idx
        if self.game_session is not None and winner_id not in (0, None, "0", ""):
            session_gid = self.game_session.find_gamer_id_from_user_id(winner_id)
            if session_gid > 0:
                client_winner = session_gid

        rank1_val = None
        rank2_val = None
        if self.game_session is not None and hasattr(self.game_session, "game_controller"):
            rank1_val = getattr(self.game_session.game_controller, "rank1", None)
            rank2_val = getattr(self.game_session.game_controller, "rank2", None)

        for gamer in self.gamers:
            self.send_game_play_data(gamer.socket_id)
            if not gamer.socket_id:
                continue
            try:
                earned = last_xp.get(gamer.user_id, 0)
                s_earned = last_score.get(gamer.user_id, 0)
                c_earned = last_coin.get(gamer.user_id, 0)
                finish_payload = {
                    "Winner": client_winner,
                    "winner": client_winner,
                    "game_winner_id": winner_id,
                    "series_scores": self.gamer_scores,
                    "xp_earned": earned,
                    "score_earned": s_earned,
                    "coin_earned": c_earned,
                }
                if rank1_val is not None:
                    finish_payload["rank1"] = rank1_val
                if rank2_val is not None:
                    finish_payload["rank2"] = rank2_val
                safe_run_async(
                    send_private_command(
                        command=make_command_json(
                            id=commands.Finish_Game,
                            data=finish_payload
                        ),
                        socket_id=gamer.socket_id,
                        game_id=self.game_play_id
                    )
                )
            except Exception as e:
                print(f"[BaseGamePlayClass] Error sending Finish_Game: {e}")

        from Entities.SocketIOClass.game import delete_game
        delete_game(self.game_play_id)

    def user_id_to_index(self, user_id):
        for index, gamer in enumerate(self.gamers):
            if str(gamer.user_id) == str(user_id):
                return index
        return -1  # -1 for draw
