import asyncio

import random

import threading

import time



from Commons import commands, static_functions

from Commons.static_functions import make_command_json, safe_run_async

from Entities.Games.base_game_class import BaseGameClass

from Entities.Games.wait_times import Start_Game_Time, Join_Game_Limit_Time

from Entities.RewardManagerClass import RewardManagerClass, GameScoreTypesEnum

from Entities.TimerClass import TimerClass

from Models.Gamer import GamerModel





class BaseGameSession:

    def __init__(self, game_play_id: str, game_type, game_score_type):

        # self.temp_gamers: list[GamerModel] = [GamerModel(user_id=i, username=str(i)) for i in range(2)]

        self.gamers: list[GamerModel] = []

        self.timer = TimerClass()

        self.game_controller: BaseGameClass = BaseGameClass(None)

        self.game_id = game_play_id

        self.game_history_id = ""

        self.is_game_running = False

        self.gamer_idies = []

        self.game_type = game_type

        self.game_score_type = game_score_type

        self.add_history_id()

        self.is_game_finished = False
        self.dc_timeout_user_id = None
        self.afk_user_id = None
        self.is_first_turn = True
        self._finish_lock = threading.RLock()



    def gamer_id_to_user_id(self, gamer_id):

        for gamer in self.gamers:

            if gamer.gamer_id == gamer_id:

                return gamer.user_id

        return None



    def add_history_id(self):

        self.game_history_id = static_functions.create_random_game_id(length=8)



    def start_game_timer(self):



        def entrypoint():

            self.check_start_game()



        t = threading.Thread(target=entrypoint, daemon=True)

        t.start()



    def check_all_players_joined(self):

        # Test : comment these

        for gamer in self.gamers:

            if not gamer.is_joined_game:

                return False

        return True



    def check_start_game(self):

        while not self.is_game_finished:

            if self.check_all_players_joined():

                time.sleep(0.8)

                self.is_game_running = True

                self.prepare_gamers()

                self.send_game_data(self.send_current_turn)

                break

            time.sleep(0.3)



    def find_gamer_from_socket(self, socket_id):
        if not socket_id:
            return None
        for gamer in self.gamers:
            if gamer.socket_id == socket_id:
                return gamer
        try:
            from Entities.SocketIOClass.game import socketid_userid_pairs, games
            uid = socketid_userid_pairs.get(socket_id)
            game_play = games.get(self.game_id)
            if uid is not None and game_play is not None and game_play.is_active_socket_for_user(uid, socket_id):
                for gamer in self.gamers:
                    if str(gamer.user_id) == str(uid):
                        gamer.socket_id = socket_id
                        return gamer
        except Exception:
            pass
        return None

    def find_gamer_from_gamer_id(self, gamer_id):

        for gamer in self.gamers:

            if gamer.gamer_id == gamer_id:

                return gamer

        return None



    def find_gamer_index_from_id(self, user_id):

        for index in range(0, len(self.gamers)):

            if str(self.gamers[index].user_id) == str(user_id):

                return index

        return None



    def find_gamer_id_from_user_id(self, user_id):

        for index in range(0, len(self.gamers)):

            if str(self.gamers[index].user_id) == str(user_id):

                return self.gamers[index].gamer_id

        return 0



    def add_gamer(self, gamer: GamerModel):

        self.gamers.append(gamer)

        self.gamer_idies.append(gamer.user_id)



    def join_gamer(self, user_id: int, socket_id):
        gamer_index = self.find_gamer_index_from_id(user_id)
        if gamer_index is not None:
            gamer = self.gamers[gamer_index]
            gamer.set_finish_reconnect_time_function(self.finish_reconnect_time)
            if gamer.is_joined_game:
                if not gamer.is_disconnected and gamer.socket_id not in ("", socket_id):
                    return
                self.timer.resume()
                gamer.reconnect(socket_id)
                safe_run_async(
                    self.send_command(commands.User_Reconnected,
                                      {"user_id": user_id, 'time': max(0, self.timer.max_time - self.timer.counter)}))
                self.send_reconnect_data(socket_id)
            else:
                gamer.join_game(socket_id)
                if self.is_game_running:
                    self.send_reconnect_data(socket_id)

    def send_game_data(self, function):

        game_data = {'gamers': []}

        for gamer in self.gamers:

            game_data['gamers'].append(gamer.to_json())

        from Entities.SocketIOManagerClass import send_command

        safe_run_async(

            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id=self.game_id))

        self.timer.start(Start_Game_Time, function)



    def send_reconnect_data(self, socket_id):
        if not self.is_game_running:
            return
        reconnect_data = {'gamers': []}

        for gamer in self.gamers:

            reconnect_data['gamers'].append(gamer.to_json())

        reconnect_data['game_data'] = self.game_controller.get_game_data()
        game_type_val = self.game_type.value if hasattr(self.game_type, "value") else str(self.game_type)
        reconnect_data['game_type'] = game_type_val
        if isinstance(reconnect_data.get('game_data'), dict):
            reconnect_data['game_data']['game_type'] = game_type_val

        if self.timer.is_user_turn:

            reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}

        else:

            reconnect_data['timer_data'] = {'is_user_turn': False, 'time': 0}

        from Entities.SocketIOManagerClass import send_private_command

        safe_run_async(

            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),

                                 socket_id=socket_id, game_id=self.game_id))



    def prepare_gamers(self):

        random.shuffle(self.gamers)

        random.shuffle(self.gamers)

        for gamer_id in range(0, len(self.gamers)):

            self.gamers[gamer_id].gamer_id = gamer_id + 1

            self.gamers[gamer_id].team_id = gamer_id + 1



    async def send_command(self, command_id, command_data):

        from Entities.SocketIOManagerClass import send_command

        await send_command(command=make_command_json(id=command_id, data=command_data), game_id=self.game_id)



    async def send_private_command(self, command_id, command_data, gamer_id):

        data = self.find_gamer_from_gamer_id(gamer_id)

        if data is not None:

            socket_id = data.socket_id

            from Entities.SocketIOManagerClass import send_private_command

            safe_run_async(

                send_private_command(command=make_command_json(id=command_id, data=command_data),

                                     socket_id=socket_id, game_id=self.game_id))



    async def command_received(self, data, socket_id):

        if not isinstance(data, dict) or "id" not in data:
            return None
        data.setdefault("data", None)
        if isinstance(data, dict) and data.get('id') in [commands.Reconnect_Data, "RequestReconnectData", "reconnect_data"]:
            self.send_reconnect_data(socket_id)
            return None

        cmd_id = data.get('id') if isinstance(data, dict) else None

        if not self.is_game_running and cmd_id not in [commands.Surrender, commands.Exit_Game]:
            return None

        gamer_data = self.find_gamer_from_socket(socket_id)

        if gamer_data is None:
            return None

        cur_turn = getattr(self.game_controller, "current_turn", 0) if hasattr(self, "game_controller") else 0
        if cmd_id not in (commands.Surrender, commands.Exit_Game) and cur_turn in (0, gamer_data.gamer_id):
            if hasattr(gamer_data, "reset_not_played_turns"):
                gamer_data.reset_not_played_turns()
            if hasattr(self, "game_controller") and hasattr(self.game_controller, "is_current_turn_played"):
                self.game_controller.is_current_turn_played = True

        if any(g.gamer_id == 0 for g in self.gamers):
            self.prepare_gamers()
        self.is_game_running = True

        gamer_id = gamer_data.gamer_id

        if cmd_id == commands.Surrender:
            from Entities.RewardManagerClass import GameScoreTypesEnum
            from Entities.Database import game_database
            if self.game_score_type != GameScoreTypesEnum.RANK and not str(gamer_data.user_id).startswith("bot_"):
                try:
                    game_database.users_manager.update_user(gamer_data.user_id, open_game_id="")
                except Exception as e:
                    print(f"[BaseGameSession] Error clearing open_game_id on surrender: {e}")

            await self.game_controller.surrender(gamer_id)
            self.game_controller.is_game_finished = True
            self.game_controller.leaver_id = gamer_id

            await self.send_command(commands.Surrender, {"gamer_id": gamer_id})

            self.timer.stop(False)

            self.check_finish_game()

            return None

        if cmd_id == commands.Exit_Game:
            from Entities.RewardManagerClass import GameScoreTypesEnum
            from Entities.Database import game_database
            if self.game_score_type != GameScoreTypesEnum.RANK and not str(gamer_data.user_id).startswith("bot_"):
                try:
                    game_database.users_manager.update_user(gamer_data.user_id, open_game_id="")
                except Exception as e:
                    print(f"[BaseGameSession] Error clearing open_game_id on exit_game: {e}")
            return None

        return gamer_id



    async def reaction_received(self, data, socket_id):

        gamer_data = self.find_gamer_from_socket(socket_id)

        if gamer_data is not None:

            gamer_id = gamer_data.gamer_id

            from Entities.SocketIOManagerClass import send_reaction

            await send_reaction(reaction_id=data, player_id=gamer_id, game_id=self.game_id)



    def send_current_turn(self):

        pass



    def disconnect_user(self, socket_id):

        for gamer_index in range(0, len(self.gamers)):

            if self.gamers[gamer_index].socket_id == socket_id:

                user_data = self.find_gamer_from_socket(socket_id)

                if user_data is not None:

                    safe_run_async(

                        self.send_command(commands.User_Disconnected,

                                          {"user_id": user_data.user_id, "time": user_data.timer.max_time}))

                self.gamers[gamer_index].disconnect()

                # Test : remove this

                self.timer.pause()

                break



    def finish_reconnect_time(self, user_id):
        with self._finish_lock:
            if self.is_game_finished:
                return
            self.dc_timeout_user_id = user_id

            safe_run_async(
                self.send_command(commands.Finish_Reconnect_Time, {"user_id": user_id}))

            gamer_id = self.find_gamer_id_from_user_id(user_id)

            if len(self.gamers) <= 2:  # this timer stop will stop in 2 player games and will resume on 4 players
                self.timer.stop(False)
                from Entities.Games.base_game_class import get_opponent_id
                opponent_id = get_opponent_id(gamer_id)
                opponent = self.find_gamer_from_gamer_id(opponent_id)
                # If opponent is ALSO disconnected, both players have abandoned the match
                if opponent is not None and getattr(opponent, "is_disconnected", False):
                    self.game_controller.finish_reconnect_time(gamer_id)
                    self.game_controller.leaver_id = 0
                    self.game_controller.is_game_finished = True
                    self.finish_game(0)
                    return
                else:
                    self.game_controller.finish_reconnect_time(gamer_id)
                    self.check_finish_game()
            else:
                self.game_controller.finish_reconnect_time(gamer_id)
                self.timer.resume()
                self.check_finish_game()



    def check_afk_turn(self):
        """Universal AFK check for 2-player turn-based games called in send_current_turn()."""
        if len(self.gamers) < 2:
            return False
        if (
            self.is_game_finished
            or getattr(self.game_controller, 'is_game_finished', False)
            or getattr(self.game_controller, 'is_round_finished', False)
        ):
            if hasattr(self, 'game_controller'):
                self.game_controller.is_current_turn_played = False
            return False
        if getattr(self, 'is_first_turn', True):
            self.is_first_turn = False
            if hasattr(self, 'game_controller'):
                self.game_controller.is_current_turn_played = False
            return False
        if not getattr(self.game_controller, 'is_current_turn_played', False):
            if self.check_finish_game_by_not_play_turn(self.game_controller.current_turn):
                return True
        if hasattr(self, 'game_controller'):
            self.game_controller.is_current_turn_played = False
        return False

    def check_finish_game_by_not_play_turn(self, current_turn):  # this used only on 2 players games

        from Entities.SocketIOManagerClass import send_command
        from Entities.RewardManagerClass import GameScoreTypesEnum

        if len(self.gamers) < 2:
            return False

        if current_turn == 1:
            gamer = self.gamers[0]
            winner = 2
        else:
            gamer = self.gamers[1]
            winner = 1

        gamer.not_played_turn()

        if gamer.not_played_turns >= 2:
            self.afk_user_id = gamer.user_id

            from Entities.SocketIOClass.game import games
            if self.game_score_type != GameScoreTypesEnum.RANK and self.game_id not in games:
                safe_run_async(
                    send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                                 game_id=self.game_id))

            self.finish_game(winner)
            return True
        else:
            safe_run_async(
                send_command(command=make_command_json(id=commands.Not_played_Turns,
                                                       data={"gamer_id": gamer.gamer_id,
                                                             "count": gamer.not_played_turns}),
                             game_id=self.game_id))
            return False

    def check_finish_game(self):

        from Entities.SocketIOManagerClass import send_command

        from Entities.RewardManagerClass import GameScoreTypesEnum

        if self.game_controller.is_game_finished:

            winner = self.game_controller.get_game_winner()

            # Only single-game modes (LOBBY, CLASSIC_RANK) emit Finish_Game immediately.

            # Multi-game series (RANK) has master BaseGamePlayClass that emits Finish_Game when the entire series concludes.

            from Entities.SocketIOClass.game import games
            if self.game_score_type != GameScoreTypesEnum.RANK and self.game_id not in games:

                safe_run_async(

                    send_command(command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),

                                 game_id=self.game_id))

            self.finish_game(winner)

            return True

        return False



    def finish_game(self, winner_gamer_id):
        with self._finish_lock:
            if self.is_game_finished:
                return

            self.is_game_finished = True
            self.timer.stop(False)

        for g in self.gamers:
            try:
                g.timer.stop()
            except Exception:
                pass
        user_idis = [g.user_id for g in self.gamers]

        from Entities.Database import game_database
        try:
            game_type_val = self.game_type.value if hasattr(self.game_type, "value") else str(self.game_type)
            game_score_val = self.game_score_type.value if hasattr(self.game_score_type, "value") else str(self.game_score_type)
            users_info = []
            for g in self.gamers:
                users_info.append({
                    "user_id": str(g.user_id),
                    "username": getattr(g, "username", getattr(g, "name", "")),
                    "image": int(getattr(g, "user_image", getattr(g, "image", 0))),
                })
            game_database.game_history_manager.create_game_history(self.game_history_id, self.game_id, user_idis,
                                                                   str(game_type_val), game_score_val,
                                                                   winner_gamer_id, users_info=users_info)
        except Exception as e:
            print(f"[BaseGameSession] Error creating game history: {e}")

        from Entities.SocketIOClass.game import finish_single_game

        user_id = "0"
        for g in self.gamers:
            if g.gamer_id == winner_gamer_id:
                user_id = g.user_id
                break

        finish_single_game(self.game_id, user_id)

