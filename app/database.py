import asyncio
import logging
import ssl as ssl_module
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "asyncpg" in settings.DATABASE_URL:
    # asyncpg requires SSL to be passed via connect_args, not the URL
    ssl_ctx = ssl_module.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl_module.CERT_NONE
    connect_args["ssl"] = ssl_ctx
    # Increase the connection timeout for serverless DB cold starts (e.g. Neon)
    connect_args["timeout"] = 60

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(retries: int = 3, base_delay: float = 2.0) -> None:
    """Initialize database tables with retry logic for serverless DB cold starts."""
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Connecting to database (attempt {attempt}/{retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            if attempt < retries:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Database connection attempt {attempt}/{retries} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {retries} database connection attempts failed. Last error: {e}"
                )
                raise
