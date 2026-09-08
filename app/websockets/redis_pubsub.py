import asyncio
import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.config import settings
from app.websockets.manager import ws_manager

logger = logging.getLogger(__name__)

CHANNEL_EMAIL_ALERTS = "channel:email_alerts"


class RedisPubSubManager:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None
        self.is_connected: bool = False

    async def connect(self):
        if not settings.REDIS_ENABLED:
            logger.info("Redis is disabled in settings. Operating in standalone WebSocket mode.")
            return

        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
            )
            await self.redis.ping()
            self.is_connected = True
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
            
            # Start background subscriber
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(CHANNEL_EMAIL_ALERTS)
            self._listener_task = asyncio.create_task(self._listen_to_channel())
        except Exception as e:
            self.is_connected = False
            logger.warning(f"Failed to connect to Redis ({e}). Falling back to local in-memory broadcasting.")

    async def _listen_to_channel(self):
        """
        Subscribes to Redis Pub/Sub channel and routes messages to WebSocket manager.
        """
        logger.info(f"Subscribed to Redis channel: {CHANNEL_EMAIL_ALERTS}")
        try:
            async for message in self.pubsub.listen():
                if message and message.get("type") == "message":
                    try:
                        data = json.loads(message["data"])
                        sender_id = data.get("sender_id", "global")
                        await ws_manager.broadcast_to_client(sender_id, data)
                    except Exception as e:
                        logger.error(f"Error processing Redis PubSub message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis subscriber task cancelled.")
        except Exception as e:
            logger.error(f"Redis listener loop encountered error: {e}")

    async def publish_alert(self, alert_data: Dict[str, Any]):
        """
        Publish alert to Redis channel, or directly to local WebSockets if Redis is not active.
        """
        if self.is_connected and self.redis:
            try:
                payload = json.dumps(alert_data, default=str)
                await self.redis.publish(CHANNEL_EMAIL_ALERTS, payload)
                return
            except Exception as e:
                logger.error(f"Failed to publish to Redis ({e}), falling back to direct WS broadcast.")

        # Fallback to direct local WebSocket broadcasting
        sender_id = alert_data.get("sender_id", "global")
        await ws_manager.broadcast_to_client(sender_id, alert_data)

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.unsubscribe(CHANNEL_EMAIL_ALERTS)
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        self.is_connected = False
        logger.info("Redis Pub/Sub manager disconnected.")


redis_manager = RedisPubSubManager()
