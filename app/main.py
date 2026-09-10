import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.websockets.manager import ws_manager
from app.websockets.redis_pubsub import redis_manager
from app.api.v1 import api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _background_init_db():
    """Run database initialization in the background so the port binds immediately."""
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Background database initialization failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — launch DB init as background task so the server port opens immediately.
    # This prevents Render's "No open ports detected" timeout for slow DB cold-starts.
    db_task = asyncio.create_task(_background_init_db())
    
    await redis_manager.connect()
    yield
    # Shutdown
    logger.info("Shutting down backend service...")
    if not db_task.done():
        db_task.cancel()
    await redis_manager.disconnect()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance Email Open Tracking and Real-Time Alert Backend with WebSockets and Redis.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
origins = settings.BACKEND_CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "redis_connected": redis_manager.is_connected,
        "active_ws_connections": len(ws_manager.all_connections),
    }


@app.websocket("/ws/alerts")
@app.websocket("/ws/alerts/{client_id}")
async def websocket_alerts_endpoint(
    websocket: WebSocket,
    client_id: str = "global",
):
    """
    Real-time WebSocket endpoint for instant email open alerts.
    Clients can connect with a specific sender/client_id to receive targeted alerts,
    or connect without client_id to receive all broadcast alerts.
    """
    await ws_manager.connect(websocket, client_id)
    try:
        # Send initial connection confirmation
        await ws_manager.send_personal_message(
            {
                "event": "CONNECTED",
                "message": f"Subscribed to real-time email open alerts as '{client_id}'",
                "client_id": client_id,
            },
            websocket,
        )
        while True:
            # Keep connection alive and accept client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.warning(f"WebSocket connection error for {client_id}: {e}")
        ws_manager.disconnect(websocket, client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

