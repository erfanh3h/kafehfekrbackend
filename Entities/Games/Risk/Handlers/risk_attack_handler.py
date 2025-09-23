from Entities.Games.Risk import RiskGameClass
from Entities.Games.Risk.Models.models import RiskContinentModel
from Entities.Games.Risk.Utils.continent_connections import is_two_continent_connected


class RiskAttackHandler:
    def __init__(self, game: RiskGameClass):
        self.game: RiskGameClass = game
        self.source_continent: RiskContinentModel = RiskContinentModel.ASIA
        self.target_continent: RiskContinentModel = RiskContinentModel.ASIA
        self.source_id: int = 0
        self.target_id: int = 0
        self.source_army: int = 0
        self.target_army: int = 0

    def reset(self):
        self.source_id = 0
        self.target_id = 0
        self.source_continent = RiskContinentModel.ASIA
        self.target_continent = RiskContinentModel.ASIA
        self.source_army = 0
        self.target_army = 0

    def check_declare_is_valid(self, source_continent, target_continent, target_id) -> bool:
        if self.game.players_data[self.source_id].continents[
            source_continent.value] == 0:  # check user have atleast 1 selected continent for attack
            print("error 1")
            return False
        if self.game.players_data[target_id - 1].continents[
            target_continent.value] == 0:  # check target user have atleast 1 target continent for attack
            print("error 2")
            return False
        if not is_two_continent_connected(source_continent, target_continent):
            print("error 3")
            return False
        return True

    def declare_war(self, source_continent, target_continent, target_id) -> bool:
        self.source_continent = RiskContinentModel.data_to_model(source_continent)
        self.target_continent = RiskContinentModel.data_to_model(target_continent)
        self.source_id = self.game.current_turn - 1
        self.target_id = target_id
        print(self.source_continent, self.target_continent, self.source_id, self.target_id)
        if not self.check_declare_is_valid(self.source_continent, self.target_continent, target_id):
            return False
        return True

    def add_attacker_army(self, count):
        self.source_army = count

    def add_defender_army(self, count):
        self.target_army = count
