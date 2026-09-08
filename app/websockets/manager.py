import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Map sender_id -> Set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Set of all active connections (for general listeners)
        self.all_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, client_id: str = "global"):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        self.all_connections.add(websocket)
        logger.info(f"WebSocket client connected: {client_id}. Total active: {len(self.all_connections)}")

    def disconnect(self, websocket: WebSocket, client_id: str = "global"):
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        self.all_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected: {client_id}. Remaining active: {len(self.all_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending direct WebSocket message: {e}")

    async def broadcast_to_client(self, client_id: str, message: Dict[str, Any]):
        """
        Broadcast alert specifically to the sender/client ID and to global subscribers.
        """
        payload = json.dumps(message, default=str)
        recipients = set()

        # Specific sender subscribers
        if client_id in self.active_connections:
            recipients.update(self.active_connections[client_id])

        # Global subscribers (e.g. admin or general dashboard)
        if "global" in self.active_connections and client_id != "global":
            recipients.update(self.active_connections["global"])

        dead_connections = []
        for connection in recipients:
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to send to connection, marking for removal: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead, client_id)

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected WebSocket clients.
        """
        payload = json.dumps(message, default=str)
        dead_connections = []
        for connection in list(self.all_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning(f"Failed to broadcast to connection: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.all_connections.discard(dead)


ws_manager = ConnectionManager()
