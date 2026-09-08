import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db, AsyncSessionLocal
from app.utils.pixel import TRANSPARENT_1X1_GIF, TRACKING_PIXEL_HEADERS
from app.services.tracking_service import record_open_event
from app.models.email import TrackedEmail
from app.models.event import ClickEvent
from app.utils.user_agent import parse_user_agent, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/track", tags=["Tracking"])


async def _process_open_background(token: str, headers: dict, client_host: str):
    """Background task to record open event without delaying pixel delivery."""
    async with AsyncSessionLocal() as db:
        try:
            await record_open_event(db, token, headers, client_host)
        except Exception as e:
            logger.error(f"Error in background open event processing: {e}")


@router.get("/open/{token}.gif")
@router.get("/open/{token}")
async def track_email_open(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Tracking pixel endpoint.
    Returns a 43-byte transparent 1x1 GIF with no-cache headers immediately,
    and logs the open event asynchronously.
    """
    # Clean token (remove .gif extension if matched in fallback route)
    clean_token = token.replace(".gif", "")
    
    headers_dict = dict(request.headers)
    client_host = request.client.host if request.client else ""

    # Process open event in background so image delivery is instant (< 5ms)
    background_tasks.add_task(
        _process_open_background,
        token=clean_token,
        headers=headers_dict,
        client_host=client_host,
    )

    return Response(
        content=TRANSPARENT_1X1_GIF,
        media_type="image/gif",
        headers=TRACKING_PIXEL_HEADERS,
    )


@router.get("/click/{token}")
async def track_link_click(
    token: str,
    url: str = Query(..., description="Target destination URL"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Link click tracking redirect proxy.
    Logs click event and redirects user to target destination.
    """
    clean_token = token.replace(".gif", "")

    # Look up email by token
    stmt = select(TrackedEmail).where(TrackedEmail.tracking_token == clean_token)
    result = await db.execute(stmt)
    tracked_email = result.scalars().first()

    if tracked_email:
        tracked_email.click_count += 1
        headers_dict = dict(request.headers) if request else {}
        client_host = request.client.host if request and request.client else ""
        client_ip = get_client_ip(headers_dict, client_host)
        ua_info = parse_user_agent(headers_dict.get("user-agent", ""))

        click_event = ClickEvent(
            tracked_email_id=tracked_email.id,
            target_url=url,
            ip_address=client_ip,
            user_agent=headers_dict.get("user-agent", ""),
            device_type=ua_info["device_type"],
        )
        db.add(click_event)
        await db.commit()

    return RedirectResponse(url=url, status_code=307)
