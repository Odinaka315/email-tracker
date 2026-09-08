from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.email import TrackedEmail
from app.models.event import OpenEvent, ClickEvent

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/overview")
async def get_stats_overview(db: AsyncSession = Depends(get_db)):
    """
    Returns high-level statistics on emails, opens, device breakdowns, and click rates.
    """
    # Total tracked emails
    total_emails_stmt = select(func.count(TrackedEmail.id))
    total_emails = (await db.execute(total_emails_stmt)).scalar() or 0

    # Opened emails
    opened_emails_stmt = select(func.count(TrackedEmail.id)).where(TrackedEmail.status == "OPENED")
    opened_emails = (await db.execute(opened_emails_stmt)).scalar() or 0

    # Total open events
    total_opens_stmt = select(func.count(OpenEvent.id))
    total_opens = (await db.execute(total_opens_stmt)).scalar() or 0

    # Total click events
    total_clicks_stmt = select(func.count(ClickEvent.id))
    total_clicks = (await db.execute(total_clicks_stmt)).scalar() or 0

    # Device breakdown
    device_breakdown_stmt = (
        select(OpenEvent.device_type, func.count(OpenEvent.id))
        .group_by(OpenEvent.device_type)
    )
    device_results = (await db.execute(device_breakdown_stmt)).all()
    device_breakdown = {device: count for device, count in device_results}

    # Proxy vs Direct breakdown
    proxy_stmt = select(OpenEvent.is_proxy, func.count(OpenEvent.id)).group_by(OpenEvent.is_proxy)
    proxy_results = (await db.execute(proxy_stmt)).all()
    proxy_breakdown = {"proxy_opens": 0, "direct_opens": 0}
    for is_proxy, count in proxy_results:
        if is_proxy:
            proxy_breakdown["proxy_opens"] = count
        else:
            proxy_breakdown["direct_opens"] = count

    open_rate = round((opened_emails / total_emails * 100), 2) if total_emails > 0 else 0.0

    return {
        "total_emails_tracked": total_emails,
        "total_emails_opened": opened_emails,
        "open_rate_percentage": open_rate,
        "total_open_events": total_opens,
        "total_link_clicks": total_clicks,
        "device_breakdown": device_breakdown,
        "privacy_proxy_breakdown": proxy_breakdown,
    }
