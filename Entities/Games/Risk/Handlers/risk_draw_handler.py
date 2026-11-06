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

        draw_type = int(draw_type) if draw_type is not None else 3
        if draw_type == 1:
            # Draw 2 Continent cards
            c1 = self.game.draw_continent_card()
            c2 = self.game.draw_continent_card()
            drawn = []
            if c1 is not None:
                player.add_continent(c1)
                drawn.append(c1.value)
            if c2 is not None:
                player.add_continent(c2)
                drawn.append(c2.value)
            self.game.update_domination_tokens()
            self.game.check_game_ended()
            return drawn
        elif draw_type == 2:
            # Draw 2 Strategy (Tactic) cards
            s1 = self.game.draw_strategy_card()
            s2 = self.game.draw_strategy_card()
            drawn = []
            if s1 is not None:
                player.add_strategy(s1)
                drawn.append(s1.value)
            if s2 is not None:
                player.add_strategy(s2)
                drawn.append(s2.value)
            return drawn
        elif draw_type == 3:
            # Draw 1 Continent card + 1 Strategy (Tactic) card
            c1 = self.game.draw_continent_card()
            s1 = self.game.draw_strategy_card()
            drawn = []
            if c1 is not None:
                player.add_continent(c1)
                drawn.append(c1.value)
            if s1 is not None:
                player.add_strategy(s1)
                drawn.append(s1.value)
            self.game.update_domination_tokens()
            self.game.check_game_ended()
            return drawn
        elif draw_type == 4:
            # End of turn / Pass turn draw (1 Strategy card if player did not attack, or standard pass draw)
            s1 = self.game.draw_strategy_card()
            if s1 is not None:
                player.add_strategy(s1)
                return [s1.value]
            return []
        return None
