from Controllers.GameSession.base_multiplayer_game_session import BaseMultiplayerGameSession
from Entities.Games.Risk import RiskGameClass
from Entities.Games.Risk.Models.models import RiskGameState
from Entities.Games.game_types import GameTypesEnum
from Entities.Games.wait_times import Risk_Turn_Time, Start_Game_Time, Risk_Pass_Time
from Commons.static_functions import safe_run_async, make_command_json
from Commons import commands


class RiskGameSession(BaseMultiplayerGameSession):
    def __init__(self, game_id: str, game_type, game_score_type):
        super().__init__(game_id, game_type, game_score_type)
        self._combat_token: int = 0

    def start_game_timer(self):
        self.game_controller = RiskGameClass(send_data_function=self.send_command, players_count=len(self.gamers))
        self.game_type = GameTypesEnum.RISK
        super().start_game_timer()

    def _sync_all_private_user_data(self):
        from Entities.SocketIOManagerClass import send_private_command
        for index, gamer in enumerate(self.gamers):
            if gamer.socket_id:
                p_idx = (gamer.gamer_id - 1) if gamer.gamer_id > 0 else index
                safe_run_async(
                    send_private_command(
                        command=make_command_json(
                            id=commands.User_Data,
                            data=self.game_controller.get_user_private_game_data(p_idx),
                        ),
                        socket_id=gamer.socket_id,
                        game_id=self.game_id,
                    )
                )

    def send_game_data(self, function):
        self.game_controller.game_state = RiskGameState.DRAW
        game_data = {'gamers': [], 'game_data': self.game_controller.get_game_data()}
        for gamer in self.gamers:
            game_data['gamers'].append(gamer.to_json())
        self._sync_all_private_user_data()
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(command=make_command_json(id=commands.Game_Data, data=game_data), game_id=self.game_id)
        )
        self.timer.start(Start_Game_Time, self._start_first_turn)

    def _start_first_turn(self):
        if self.check_finish_game():
            return
        self.game_controller.game_state = RiskGameState.DRAW
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(
                    id=commands.Draw_Card,
                    data={'turn': self.game_controller.current_turn, 'game_state': self.game_controller.game_state.value}
                ),
                game_id=self.game_id,
            )
        )
        self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

    def send_reconnect_data(self, socket_id):
        if not self.is_game_running:
            return
        super().send_reconnect_data(socket_id)
        gamer_data = self.find_gamer_from_socket(socket_id)
        p_idx = (gamer_data.gamer_id - 1) if (gamer_data is not None and gamer_data.gamer_id > 0) else max(0, self.game_controller.current_turn - 1)
        from Entities.SocketIOManagerClass import send_private_command
        safe_run_async(
            send_private_command(
                command=make_command_json(id=commands.User_Data, data=self.game_controller.get_user_private_game_data(p_idx)),
                socket_id=socket_id,
                game_id=self.game_id,
            )
        )

    async def _broadcast_battle_result(self, battle_res: dict):
        if not battle_res:
            return
        self.timer.stop(False)
        payload = dict(battle_res)
        payload["players_data"] = [p.to_global_json() for p in self.game_controller.players_data]
        payload["tokens"] = list(self.game_controller.tokens)
        payload["game_state"] = self.game_controller.game_state.value
        await self.send_command(commands.Roll_Result, payload)
        await self.send_command(commands.Attack, payload)
        self._sync_all_private_user_data()
        if self.check_finish_game():
            return
        self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

    async def command_received(self, data, socket_id):
        gamer_id = await super().command_received(data, socket_id)
        if gamer_id is None:
            return
        if not self.game_controller.check_authority(data, gamer_id):
            return

        cmd_id = data['id']
        payload = data.get('data') if isinstance(data.get('data'), dict) else data

        if cmd_id == commands.Draw_Card:
            draw_type = payload.get('draw_type', data.get('draw_type', 3))
            draw_result = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if draw_result is None:
                return
            await self.send_command(
                commands.Draw_Result,
                {
                    'gamer_id': gamer_id,
                    'draw_type': draw_type,
                    'new_data': self.game_controller.players_data[gamer_id - 1].to_global_json(),
                    'tokens': list(self.game_controller.tokens),
                    'game_state': self.game_controller.game_state.value,
                },
            )
            await self.send_private_command(
                commands.Draw_Result_Private,
                {
                    'data': draw_result,
                    'draw_type': draw_type,
                    'new_user_data': self.game_controller.get_user_private_game_data(gamer_id - 1),
                },
                gamer_id,
            )
            if self.check_finish_game():
                self.timer.stop(False)
                return
            self.timer.stop(False)
            self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

        elif cmd_id == commands.Pass_Turn:
            draw_result = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            await self.pass_turn(draw_result, gamer_id)

        elif cmd_id == commands.Declare_Attack:
            ok = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if not ok:
                return
            src_c = payload.get('source_continent', data.get('source_continent'))
            tgt_c = payload.get('target_continent', data.get('target_continent'))
            tgt_idx = int(payload.get('target_index', data.get('target_index')))
            await self.send_command(
                commands.Declare_Attack,
                {
                    'gamer_id': gamer_id,
                    'source_continent': src_c,
                    'target_continent': tgt_c,
                    'target_index': tgt_idx,
                    'game_state': self.game_controller.game_state.value,
                },
            )
            self.timer.stop(False)
            self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

        elif cmd_id == commands.AttackerArmy:
            added = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            await self.send_command(
                commands.AttackerArmy,
                {
                    'gamer_id': gamer_id,
                    'count': added,
                    'target_index': self.game_controller.attack_handler.target_id,
                    'game_state': self.game_controller.game_state.value,
                },
            )
            self._sync_all_private_user_data()
            self.timer.stop(False)
            self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

        elif cmd_id in (commands.DefenderArmy, getattr(commands, "Cancel_Attack", "CancelAttack")):
            battle_res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if isinstance(battle_res, dict):
                await self._broadcast_battle_result(battle_res)

        elif cmd_id == commands.QuestArmy:
            added = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            q_type = payload.get('type', data.get('type', 'Attacker'))
            await self.send_command(
                commands.QuestArmy,
                {
                    'gamer_id': gamer_id,
                    'type': q_type,
                    'count': added,
                    'attacker_army': self.game_controller.attack_handler.source_army,
                    'defender_army': self.game_controller.attack_handler.target_army,
                },
            )
            self._sync_all_private_user_data()

        elif cmd_id in (commands.Attack, commands.Roll_Dice):
            battle_res = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if isinstance(battle_res, dict):
                await self._broadcast_battle_result(battle_res)

        elif cmd_id in (getattr(commands, "Use_Strategy", "UseStrategy"), commands.Select_Peace):
            effect = await self.game_controller.recieve_data(cmd_id, data, gamer_id)
            if not effect:
                return
            effect_payload = dict(effect)
            effect_payload["players_data"] = [p.to_global_json() for p in self.game_controller.players_data]
            effect_payload["tokens"] = list(self.game_controller.tokens)
            effect_payload["game_state"] = self.game_controller.game_state.value
            await self.send_command(getattr(commands, "Strategy_Result", "StrategyResult"), effect_payload)
            self._sync_all_private_user_data()
            if self.check_finish_game():
                self.timer.stop(False)
                return

    def on_turn_timeout(self):
        if self.is_game_finished or self.check_finish_game():
            return
        state = self.game_controller.game_state
        cur_turn = self.game_controller.current_turn

        # 1. If player timed out in DRAW phase, auto-draw 1 Continent + 1 Strategy and pass turn
        if state in (RiskGameState.STARTGAME, RiskGameState.DRAW):
            draw_res = self.game_controller.draw_handler.draw_card(3, cur_turn - 1)
            self.game_controller.game_state = RiskGameState.SELECTACTION
            safe_run_async(
                self.send_command(
                    commands.Draw_Result,
                    {
                        'gamer_id': cur_turn,
                        'draw_type': 3,
                        'new_data': self.game_controller.players_data[cur_turn - 1].to_global_json(),
                        'tokens': list(self.game_controller.tokens),
                        'game_state': self.game_controller.game_state.value,
                    },
                )
            )
            self._sync_all_private_user_data()
            if self.check_finish_game():
                return
            self.send_current_turn()
            return

        # 2. If timed out during an active attack (AttackerArmy or DefenderArmy), auto-resolve combat
        if self.game_controller.attack_handler.is_attack_active:
            battle_res = self.game_controller.attack_handler.resolve_attack()
            safe_run_async(self._broadcast_battle_result(battle_res))
            return

        # 3. Otherwise in SELECTACTION, auto-pass turn
        draw_res = self.game_controller.draw_handler.draw_card(4, cur_turn - 1) if not self.game_controller.attacked_this_turn else []
        safe_run_async(self.pass_turn(draw_res, cur_turn))

    def send_current_turn(self):
        if self.check_finish_game():
            return
        self.game_controller.change_turn()
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(
                    id=commands.Draw_Card,
                    data={'turn': self.game_controller.current_turn, 'game_state': self.game_controller.game_state.value}
                ),
                game_id=self.game_id,
            )
        )
        self.timer.start(Risk_Turn_Time, self.on_turn_timeout)

    def send_dice(self):
        from Entities.SocketIOManagerClass import send_command
        safe_run_async(
            send_command(
                command=make_command_json(id=commands.Roll_Result, data={'dice': self.game_controller.current_dice}),
                game_id=self.game_id,
            )
        )

    async def pass_turn(self, draw_result, gamer_id):
        self.timer.stop(False)
        p_idx = max(0, min(len(self.game_controller.players_data) - 1, gamer_id - 1))
        await self.send_command(
            commands.Pass_Turn,
            {
                'gamer_index': p_idx,
                'gamer_id': gamer_id,
                'new_data': self.game_controller.players_data[p_idx].to_global_json(),
                'tokens': list(self.game_controller.tokens),
            },
        )
        if draw_result:
            await self.send_private_command(
                commands.Draw_Result_Private,
                {
                    'data': draw_result,
                    'draw_type': 4,
                    'new_user_data': self.game_controller.get_user_private_game_data(p_idx),
                },
                gamer_id,
            )
        if self.check_finish_game():
            return
        self.send_current_turn()
