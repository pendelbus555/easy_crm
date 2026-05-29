import json
from collections.abc import Iterable

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, event: str, payload: dict) -> None:
        disconnected: list[WebSocket] = []
        message = json.dumps({"event": event, "payload": payload}, default=str)

        for connection in self._connections_snapshot():
            try:
                await connection.send_text(message)
            except RuntimeError:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)

    def _connections_snapshot(self) -> Iterable[WebSocket]:
        return tuple(self.active_connections)


manager = ConnectionManager()
