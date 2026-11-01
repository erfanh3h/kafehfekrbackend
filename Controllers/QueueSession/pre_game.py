from Commons.static_functions import safe_run_async
import random

from Commons import commands
from Commons.static_functions import make_command_json
from Entities.Database import game_database
from Entities.Games.game_types import GameTypesEnum
from Entities.TimerClass import TimerClass
from Models.Queuer import QueuerModel


class PreGameClass:
    def __init__(self, pre_game_id: str, queuers, start_game_function, delete_game_function):
        self.timer = TimerClass()
        self.dc_timer = TimerClass()
        self.start_game_function = start_game_function
        self.delete_game_function = delete_game_function
        self.pre_game_id: str = pre_game_id
        self.active_game_types = []
        self.queuers: list[QueuerModel] = queuers
        self.pre_bans: list[GameTypesEnum] = []
        self.system_selected_game: GameTypesEnum = None
        self.select_turn_index = 0
        self.is_current_pick_happens = True
        self.dced_user = None

    def remove_game_type_from_list(self, game_type):
        for game in list(self.active_game_types):
            if game.value == game_type:
                self.active_game_types.remove(game)
                return

    def find_gamer_from_user_id(self, user_id):
        for queuer in self.queuers:
            if queuer.user_id == user_id:
                return queuer
        return None

    def is_some_one_offline(self):
        for queuer in self.queuers:
            if queuer.is_disconnected:
                return True
        return False

    def find_gamer_from_socket_id(self, socket_id):
        for queuer in self.queuers:
            if queuer.socket_id == socket_id:
                return queuer
        return None

    def get_reconnect_data(self):
        queuers_data = []
        pre_bans = [game.value if hasattr(game, 'value') else str(game) for game in self.pre_bans]
        if self.system_selected_game is not None:
            system_selected_game = self.system_selected_game.value if hasattr(self.system_selected_game, 'value') else str(self.system_selected_game)
        else:
            system_selected_game = None
        for queuer in self.queuers:
            queuers_data.append(queuer.to_queue_json())
        if self.select_turn_index % 2 == 1:
            current_queuer_id = self.queuers[0].user_id
        else:
            current_queuer_id = self.queuers[1].user_id

        # Compile turn history so far for the selection timeline
        turn_history = {}
        if len(self.queuers) > 0 and len(self.queuers[0].banned_games) > 0:
            turn_history[1] = self.queuers[0].banned_games[0]
        if len(self.queuers) > 1 and len(self.queuers[1].banned_games) > 0:
            turn_history[2] = self.queuers[1].banned_games[0]
        if len(self.queuers) > 0 and self.queuers[0].selected_game is not None:
            turn_history[3] = self.queuers[0].selected_game
        if len(self.queuers) > 1 and self.queuers[1].selected_game is not None:
            turn_history[4] = self.queuers[1].selected_game
        if len(self.queuers) > 0 and len(self.queuers[0].banned_games) > 1:
            turn_history[5] = self.queuers[0].banned_games[1]
        if len(self.queuers) > 1 and len(self.queuers[1].banned_games) > 1:
            turn_history[6] = self.queuers[1].banned_games[1]
        if system_selected_game is not None:
            turn_history[7] = system_selected_game

        remaining_time = max(0, self.timer.max_time - self.timer.counter)
        data = {
            'pre_game_id': self.pre_game_id,
            'pre_bans': pre_bans,
            'queuers': queuers_data,
            'system_selected_game': system_selected_game,
            'active_index': self.select_turn_index,
            'active_user_id': current_queuer_id,
            'timer_value': remaining_time,
            'counter': self.timer.counter,
            'max_time': self.timer.max_time,
            'turn_history': turn_history,
        }
        return data

    def set_system_bans(self):
        from Entities.SocketIOManagerClass import send_pre_game_command
        import asyncio
        self.pre_bans = random.sample(list(GameTypesEnum.two_players_games()), 3)  # randomly ban 3 games
        self.active_game_types = [game for game in GameTypesEnum.two_players_games() if game not in self.pre_bans]
        readable_data = [game.value for game in self.pre_bans]
        safe_run_async(
            send_pre_game_command(command=make_command_json(id=commands.System_Banned_Games,
                                                            data=readable_data), pre_game_id=self.pre_game_id))
        self.timer.start(5, self.send_current_turn)

    def start_pre_game(self):
        self.set_pre_game_id_db(self.pre_game_id)
        for index, queuer in enumerate(self.queuers):
            queuer.set_index(index)
            queuer.set_finish_reconnect_time_function(self.finish_dc_timer)
        self.timer.start(5, self.set_system_bans)

    async def command_received(self, data, socket_id):
        gamer_data = self.find_gamer_from_socket_id(socket_id)
        if gamer_data is None:
            return
        if data.get('id') == commands.Select_Game:
            game_type = data.get('game_type')
            print(f"[PreGameClass] Player {gamer_data.queuer_index + 1} chosen: {game_type}")
            self.pick_game(game_type, gamer_data)
            self.timer.stop()

    def pick_game(self, game_type, gamer_data):
        from Entities.SocketIOManagerClass import send_pre_game_command
        import asyncio
        if gamer_data is None:
            return
        # Ensure chosen game is available
        if not any(g.value == game_type for g in self.active_game_types):
            print(f"[PreGameClass] Warning: {game_type} not in active game types.")
            return

        if self.select_turn_index == 1:
            if len(self.queuers[0].banned_games) != 0 or gamer_data.queuer_index != 0:
                return
            self.queuers[0].banned_games.append(game_type)
        elif self.select_turn_index == 2:
            if len(self.queuers[1].banned_games) != 0 or gamer_data.queuer_index != 1:
                return
            self.queuers[1].banned_games.append(game_type)
        elif self.select_turn_index == 3:
            if self.queuers[0].selected_game is not None or gamer_data.queuer_index != 0:
                return
            self.queuers[0].selected_game = game_type
        elif self.select_turn_index == 4:
            if self.queuers[1].selected_game is not None or gamer_data.queuer_index != 1:
                return
            self.queuers[1].selected_game = game_type
        elif self.select_turn_index == 5:
            if len(self.queuers[0].banned_games) != 1 or gamer_data.queuer_index != 0:
                return
            self.queuers[0].banned_games.append(game_type)
        elif self.select_turn_index == 6:
            if len(self.queuers[1].banned_games) != 1 or gamer_data.queuer_index != 1:
                return
            self.queuers[1].banned_games.append(game_type)

        self.is_current_pick_happens = True
        self.remove_game_type_from_list(game_type)
        safe_run_async(
            send_pre_game_command(command=make_command_json(id=commands.Selected_Game,
                                                            data={'active_index': self.select_turn_index,
                                                                  'game_type': game_type}),
                                  pre_game_id=self.pre_game_id))

    def send_current_turn(self):
        def call_new_pick():
            from Entities.SocketIOManagerClass import send_pre_game_command
            import asyncio
            self.is_current_pick_happens = False
            if self.select_turn_index % 2 == 1:
                current_queuer_id = self.queuers[0].user_id
            else:
                current_queuer_id = self.queuers[1].user_id
            safe_run_async(
                send_pre_game_command(command=make_command_json(id=commands.Select_Game,
                                                                data=current_queuer_id), pre_game_id=self.pre_game_id))
            self.timer.start(20, self.send_current_turn)

        if self.dced_user is not None:
            self.set_pre_game_id_db("")
            self.delete_game_function(self.pre_game_id, self.dced_user, self.queuers)
            return

        if not self.is_current_pick_happens:  # Fallback if player did not pick in time
            if self.select_turn_index % 2 == 1:
                current_queuer = self.queuers[0]
            else:
                current_queuer = self.queuers[1]
            if self.active_game_types:
                random_game = random.choice(self.active_game_types)
                self.pick_game(random_game.value, current_queuer)

        self.select_turn_index += 1
        if self.select_turn_index == 8:  # last turn
            self.set_pre_game_id_db("")
            self.start_game_function(self.queuers, [self.queuers[0].selected_game, self.queuers[1].selected_game,
                                                    self.system_selected_game], self.pre_game_id)
        elif self.select_turn_index == 7:
            from Entities.SocketIOManagerClass import send_pre_game_command
            import asyncio
            if self.active_game_types:
                selected_game = random.choice(self.active_game_types)
                readable_data = selected_game.value
            else:
                readable_data = "TicTacToe"
            self.system_selected_game = readable_data
            safe_run_async(
                send_pre_game_command(command=make_command_json(id=commands.Selected_Game,
                                                                data={'active_index': self.select_turn_index,
                                                                      'game_type': readable_data}),
                                      pre_game_id=self.pre_game_id))
            self.timer.start(13, self.send_current_turn)
        else:
            call_new_pick()

    def set_pre_game_id_db(self, pre_game_id):
        try:
            if len(self.queuers) > 0:
                game_database.users_manager.update_user(self.queuers[0].user_id, open_pre_game_id=pre_game_id)
            if len(self.queuers) > 1:
                game_database.users_manager.update_user(self.queuers[1].user_id, open_pre_game_id=pre_game_id)
        except Exception as e:
            print(f"[PreGameClass] set_pre_game_id_db note: {e}")

    def disconnect_user(self, socket_id):
        from Entities.SocketIOManagerClass import send_pre_game_command
        import asyncio
        user_data = self.find_gamer_from_socket_id(socket_id)
        if user_data is not None:
            self.timer.pause()
            user_data.disconnect()
            safe_run_async(
                send_pre_game_command(command=make_command_json(id=commands.User_Disconnected,
                                                                data={"user_id": user_data.user_id,
                                                                      "time": user_data.timer.max_time}),
                                      pre_game_id=self.pre_game_id))

    def reconnect_user(self, socket_id, user_id):
        from Entities.SocketIOManagerClass import send_pre_game_command
        import asyncio
        user_data = self.find_gamer_from_user_id(user_id)
        if user_data is not None:
            user_data.reconnect(socket_id)
            if not self.is_some_one_offline():
                self.timer.resume()
            safe_run_async(send_pre_game_command(
                command=make_command_json(id=commands.User_Reconnected,
                                          data={"user_id": user_data.user_id, "time": max(0, self.timer.max_time - self.timer.counter)}),
                pre_game_id=self.pre_game_id))

    def finish_dc_timer(self, user_id):
        self.dced_user = user_id
        self.timer.stop()
