"""
SpectatorRoomManager
Manages dedicated Socket.IO rooms (`spectate_{game_id}`) completely isolated from active player rooms (`{game_id}`).
Supports emitting spectator events to `/social` and `/game` namespaces without interfering with player sessions.
"""

from Entities.SocketIOClass import Socket_Server


class SpectatorRoomManager:
    ROOM_PREFIX = "spectate_"

    @classmethod
    def get_room_name(cls, game_id: str) -> str:
        return f"{cls.ROOM_PREFIX}{game_id}"

    @classmethod
    async def join_spectator_room(cls, sid: str, game_id: str, namespace: str = "/social") -> str:
        room_name = cls.get_room_name(game_id)
        try:
            await Socket_Server.enter_room(sid, room_name, namespace=namespace)
        except Exception:
            pass
        return room_name

    @classmethod
    async def leave_spectator_room(cls, sid: str, game_id: str, namespace: str = "/social") -> None:
        room_name = cls.get_room_name(game_id)
        try:
            await Socket_Server.leave_room(sid, room_name, namespace=namespace)
        except Exception:
            pass

    @classmethod
    async def emit_to_spectator(cls, sid: str, command: dict, namespace: str = "/social") -> None:
        try:
            await Socket_Server.emit("command", command, to=sid, namespace=namespace)
        except Exception:
            pass

    @classmethod
    async def broadcast_to_spectators(cls, game_id: str, command: dict, namespaces: tuple[str, ...] = ("/social",)) -> None:
        room_name = cls.get_room_name(game_id)
        for ns in namespaces:
            try:
                await Socket_Server.emit("command", command, room=room_name, namespace=ns)
            except Exception:
                pass
