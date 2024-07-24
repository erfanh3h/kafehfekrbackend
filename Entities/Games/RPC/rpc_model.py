from enum import Enum


class RPCModel(Enum):
    Rock = "Rock"
    Paper = "Paper"
    Cutter = "Cutter"


def string_to_rpc_enum(string):
    if string == "Rock":
        return RPCModel.Rock
    elif string == "Paper":
        return RPCModel.Paper
    elif string == "Cutter":
        return RPCModel.Cutter
    else:
        return RPCModel.Rock
