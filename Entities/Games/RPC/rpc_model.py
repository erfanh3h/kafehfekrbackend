from enum import Enum


class RPCModel(Enum):
    Rock = "rock"
    Paper = "paper"
    Cutter = "cutter"


def string_to_rpc_enum(string):
    if string == "rock":
        return RPCModel.Rock
    elif string == "paper":
        return RPCModel.Paper
    elif string == "cutter":
        return RPCModel.Cutter
    else:
        return RPCModel.Rock
