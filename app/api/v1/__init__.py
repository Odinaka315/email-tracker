from fastapi import APIRouter
from app.api.v1.tracking import router as tracking_router
from app.api.v1.emails import router as emails_router
from app.api.v1.stats import router as stats_router

api_v1_router = APIRouter()
api_v1_router.include_router(tracking_router)
api_v1_router.include_router(emails_router)
api_v1_router.include_router(stats_router)

__all__ = ["api_v1_router"]
