from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket] = {}

    async def connect(self, websocket: WebSocket, id: int):
        await websocket.accept()
        self.active_connections[id] = websocket
        print(self.active_connections.keys())

    def disconnect(self, id: int):
        self.active_connections.pop(id)

    async def send_partner_message(self, message: bytes, pid: int):
        print(self.active_connections.keys())
        if pid != -1:
            await self.active_connections.get(pid).send_bytes(message)