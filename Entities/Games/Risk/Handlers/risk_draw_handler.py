from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Entities.Games.Risk import RiskGameClass


class RiskDrawHandler:
    def __init__(self, game: "RiskGameClass"):
        self.game = game

    def draw_card(self, draw_type: int, player_index: int = None):
        if player_index is None:
            player_index = self.game.current_turn - 1
        if not (0 <= player_index < len(self.game.players_data)):
            return None

        player = self.game.players_data[player_index]
        try:
            draw_type = int(draw_type) if draw_type is not None else 3
        except (TypeError, ValueError):
            draw_type = 3

        if draw_type == 1:
            # Draw 2 Continent cards (fallback to Strategy card if all 42 Continent cards are held by players)
            drawn = []
            for _ in range(2):
                c = self.game.draw_continent_card()
                if c is not None:
                    player.add_continent(c)
                    drawn.append(c.value)
                else:
                    s = self.game.draw_strategy_card()
                    if s is not None:
                        player.add_strategy(s)
                        drawn.append(s.value)
            self.game.update_domination_tokens()
            self.game.check_game_ended()
            return drawn

        elif draw_type == 2:
            # Draw 2 Strategy (Tactic) cards
            drawn = []
            for _ in range(2):
                s = self.game.draw_strategy_card()
                if s is not None:
                    player.add_strategy(s)
                    drawn.append(s.value)
                else:
                    c = self.game.draw_continent_card()
                    if c is not None:
                        player.add_continent(c)
                        drawn.append(c.value)
            self.game.update_domination_tokens()
            self.game.check_game_ended()
            return drawn

        elif draw_type == 3:
            # Draw 1 Continent card + 1 Strategy (Tactic) card
            drawn = []
            c1 = self.game.draw_continent_card()
            if c1 is not None:
                player.add_continent(c1)
                drawn.append(c1.value)
            else:
                s_fallback = self.game.draw_strategy_card()
                if s_fallback is not None:
                    player.add_strategy(s_fallback)
                    drawn.append(s_fallback.value)

            s1 = self.game.draw_strategy_card()
            if s1 is not None:
                player.add_strategy(s1)
                drawn.append(s1.value)
            else:
                c_fallback = self.game.draw_continent_card()
                if c_fallback is not None:
                    player.add_continent(c_fallback)
                    drawn.append(c_fallback.value)

            self.game.update_domination_tokens()
            self.game.check_game_ended()
            return drawn

        elif draw_type == 4:
            # End of turn / Pass turn draw (1 Strategy card if player did not attack)
            s1 = self.game.draw_strategy_card()
            if s1 is not None:
                player.add_strategy(s1)
                return [s1.value]
            return []

        return None
