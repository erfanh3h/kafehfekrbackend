from typing import List

from Entities.Games.Risk.Models.models import RiskContinentModel

continent_connections: {RiskContinentModel: List[RiskContinentModel]} = {
    RiskContinentModel.ASIA: [RiskContinentModel.ASIA, RiskContinentModel.AUSTRALIA, RiskContinentModel.EUROPE,
                              RiskContinentModel.AFRICA, RiskContinentModel.NORTHAMERICA],
    RiskContinentModel.AUSTRALIA: [RiskContinentModel.AUSTRALIA, RiskContinentModel.ASIA],
    RiskContinentModel.EUROPE: [RiskContinentModel.EUROPE, RiskContinentModel.ASIA, RiskContinentModel.NORTHAMERICA,
                                RiskContinentModel.AFRICA],
    RiskContinentModel.AFRICA: [RiskContinentModel.AFRICA, RiskContinentModel.EUROPE, RiskContinentModel.ASIA,
                                RiskContinentModel.SOUTHAMERICA],
    RiskContinentModel.SOUTHAMERICA: [RiskContinentModel.SOUTHAMERICA, RiskContinentModel.NORTHAMERICA,
                                      RiskContinentModel.AFRICA],
    RiskContinentModel.NORTHAMERICA: [RiskContinentModel.NORTHAMERICA, RiskContinentModel.EUROPE,
                                      RiskContinentModel.ASIA, RiskContinentModel.SOUTHAMERICA]
}


def is_two_continent_connected(source, target):
    return target in continent_connections[source]
