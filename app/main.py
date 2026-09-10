import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.websockets.manager import ws_manager
from app.websockets.redis_pubsub import redis_manager
from app.api.v1 import api_v1_router

# Ensure stdout and stderr flush immediately — critical for Render real-time logs
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("email_alerts")


async def _background_init_db():
    """Run database initialization in the background so the port binds immediately."""
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Background database initialization failed: {e}", exc_info=True)


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

# Request logging middleware to provide clear visibility on Render
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"--> {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"<-- {request.method} {request.url.path} {response.status_code} ({duration_ms:.1f}ms)")
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.exception(f"<-- {request.method} {request.url.path} FAILED ({duration_ms:.1f}ms): {e}")
        raise


# Catch-all exception handler to make 500 errors immediately diagnosable
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"CRITICAL 500 ERROR on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        },
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

