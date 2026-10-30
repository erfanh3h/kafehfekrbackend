import asyncio

from Entities.Games.Yinsh import YinshGameClass
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Yinsh_Turn_Time, Yinsh_Ring_Time
from Commons.static_functions import make_command_json
from Commons import commands
from Controllers.GameSession import BaseGameSession


def safe_run_async(coro):
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class YinshGameSession(BaseGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self.ring_removal_token = 0

    def start_game_timer(self):
        self.game_controller = YinshGameClass(send_data_function=self.send_command)
        self.game_type = GameTypesEnum.YINSH
        super().start_game_timer()

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if data["id"] == commands.Submit_Ring:
            peace_id = data["data"]
            is_selection_authorized = self.game_controller.check_setup_ring_authority(peace_id, gamer_id)
            if is_selection_authorized:
                await self.game_controller.recieve_data(data["id"], peace_id, gamer_id)
                self.timer.stop(False)
                self.send_current_turn()
        elif data["id"] == commands.Select_Remove_Peace or (
            (self.game_controller.current_remover != 0 or len(self.game_controller.pending_ring_removals) > 0)
            and data["id"] in (commands.Select_Peace, commands.Remove_Peace)
        ):
            peace_id = data["data"]
            if self.game_controller.current_remover == 0 and len(self.game_controller.pending_ring_removals) > 0:
                self.game_controller.current_remover = self.game_controller.pending_ring_removals[0]
            is_selection_authorized = self.game_controller.check_remove_ring_authority(peace_id, gamer_id)
            if is_selection_authorized:
                self.ring_removal_token += 1
                self.timer.stop(False)
                await self.game_controller.recieve_data(commands.Select_Remove_Peace, peace_id, gamer_id)
                self.send_current_turn()
        elif data["id"] == commands.Select_Peace:
            peace_id = data["data"]
            is_selection_authorized = self.game_controller.check_select_piece_authority(peace_id, gamer_id)
            if is_selection_authorized:
                await self.game_controller.recieve_data(data["id"], peace_id, gamer_id)
        elif data["id"] == commands.Move_Ring:
            peace_id = data["data"]["target_id"]
            is_selection_authorized = self.game_controller.check_move_ring_authority(peace_id, gamer_id)
            if is_selection_authorized:
                await self.game_controller.recieve_data(data["id"], data["data"], gamer_id)
                self.timer.stop(False)
                self.send_current_turn()

    def send_current_turn(self):
        from Entities.SocketIOManagerClass import send_command

        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()
            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                    game_id=self.game_id))
            self.finish_game(winner)
            return

        # If a 5-in-a-row occurred and player needs to pick a ring to remove:
        if self.game_controller.current_remover != 0 or len(self.game_controller.pending_ring_removals) > 0:
            if self.game_controller.current_remover == 0 and len(self.game_controller.pending_ring_removals) > 0:
                self.game_controller.current_remover = self.game_controller.pending_ring_removals[0]
            self.ring_removal_token += 1
            cur_token = self.ring_removal_token

            def auto_remove_ring_on_timeout():
                if cur_token != self.ring_removal_token:
                    return
                if self.game_controller.current_remover == 0 and len(self.game_controller.pending_ring_removals) == 0:
                    return
                if len(self.game_controller.pending_ring_removals) > 0:
                    remover_id = self.game_controller.pending_ring_removals.pop(0)
                    random_ring_id = self.game_controller.get_random_gamer_ring(remover_id)
                    self.game_controller.remove_gamer_ring(remover_id, random_ring_id)
                    self.game_controller.current_remover = (
                        self.game_controller.pending_ring_removals[0]
                        if len(self.game_controller.pending_ring_removals) > 0 else 0
                    )
                    safe_run_async(
                        send_command(
                            command=make_command_json(
                                id=commands.Win_Happened,
                                data={
                                    "win_data": [],
                                    "removed_rings": [random_ring_id],
                                    "gamer_id": remover_id,
                                    "current_remover": self.game_controller.current_remover,
                                },
                            ),
                            game_id=self.game_id,
                        )
                    )
                self.send_current_turn()

            safe_run_async(
                send_command(
                    command=make_command_json(
                        id=commands.Select_Remove_Peace,
                        data=self.game_controller.current_remover,
                    ),
                    game_id=self.game_id,
                )
            )
            self.timer.start(Yinsh_Ring_Time, auto_remove_ring_on_timeout)
            return

        # auto select ring if user didnt select on his turn
        if (self.game_controller.is_setup_ring_phase and not self.game_controller.is_ring_setuped and
                self.game_controller.current_round != 0):
            gamer_id = self.game_controller.current_turn
            random_id = self.game_controller.extract_random_piece_for_auto_ring()
            self.game_controller.submit_ring(gamer_id, random_id)
            safe_run_async(
                send_command(command=make_command_json(id=commands.Ring_Submited,
                                                       data={"gamer_id": gamer_id, "piece_id": random_id}),
                             game_id=self.game_id))
            self.game_controller.is_ring_setuped = True
        # auto remove selected peace if user didnt move ring
        if not self.game_controller.is_setup_ring_phase and self.game_controller.last_selected_piece_id != -1:
            piece_id = self.game_controller.last_selected_piece_id
            self.game_controller.remove_disk(piece_id)
            self.game_controller.last_selected_piece_id = -1
            safe_run_async(
                send_command(command=make_command_json(id=commands.Remove_Peace,
                                                       data={"piece_id": piece_id}),
                             game_id=self.game_id))
            self.game_controller.is_ring_setuped = True
        if self.game_controller.check_game_ended():
            winner = self.game_controller.get_game_winner()
            safe_run_async(
                send_command(
                    command=make_command_json(id=commands.Finish_Game, data={"Winner": winner}),
                    game_id=self.game_id))
            self.finish_game(winner)
            return
        self.game_controller.change_turn()
        safe_run_async(
            send_command(command=make_command_json(id=commands.Current_Turn,
                                                   data={"turn": self.game_controller.current_turn,
                                                         "is_setup_ring_phase": self.game_controller.is_setup_ring_phase}),
                         game_id=self.game_id))
        if self.game_controller.is_setup_ring_phase:
            self.timer.start(Yinsh_Ring_Time, self.send_current_turn)
        else:
            self.timer.start(Yinsh_Turn_Time, self.send_current_turn)

    def send_reconnect_data(self, socket_id):
        reconnect_data = {'gamers': [], 'game_type': 'Yinsh'}
        for gamer in self.gamers:
            reconnect_data['gamers'].append(gamer.to_json())
        reconnect_data['game_data'] = self.game_controller.get_game_data()
        reconnect_data['game_data']['game_type'] = 'Yinsh'
        if self.timer.is_user_turn:
            reconnect_data['timer_data'] = {'is_user_turn': True, 'time': self.timer.counter + 1}
        else:
            reconnect_data['timer_data'] = {'is_user_turn': False, 'time': 0}
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(command=make_command_json(id=commands.Reconnect_Data, data=reconnect_data),
                                 socket_id=socket_id, game_id=self.game_id))
