import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.email import TrackedEmail
from app.models.event import OpenEvent
from app.schemas.alert import EmailOpenedAlertPayload
from app.utils.user_agent import parse_user_agent, get_client_ip
from app.websockets.redis_pubsub import redis_manager
from app.config import settings

logger = logging.getLogger(__name__)


async def record_open_event(
    db: AsyncSession,
    token: str,
    headers: Dict[str, str],
    client_host: str = "",
) -> Optional[TrackedEmail]:
    """
    Finds the tracked email by token, logs the OpenEvent, updates counts/timestamps,
    and fires real-time alert notifications via Redis/WebSockets.
    """
    # 1. Fetch tracked email by token
    stmt = select(TrackedEmail).where(TrackedEmail.tracking_token == token)
    result = await db.execute(stmt)
    tracked_email = result.scalars().first()

    if not tracked_email:
        logger.warning(f"Tracking token not found: {token}")
        return None

    # 2. Extract metadata from client request
    user_agent_str = headers.get("user-agent", "")
    client_ip = get_client_ip(headers, client_host)
    ua_info = parse_user_agent(user_agent_str)

    now = datetime.now(timezone.utc)
    is_first_open = tracked_email.open_count == 0

    # 3. Update TrackedEmail record
    tracked_email.open_count += 1
    tracked_email.status = "OPENED"
    if is_first_open or not tracked_email.first_opened_at:
        tracked_email.first_opened_at = now
    tracked_email.last_opened_at = now
    tracked_email.updated_at = now

    # 4. Create OpenEvent record
    open_event = OpenEvent(
        tracked_email_id=tracked_email.id,
        ip_address=client_ip,
        user_agent=user_agent_str,
        device_type=ua_info["device_type"],
        client_name=ua_info["client_name"],
        os_name=ua_info["os_name"],
        is_bot=ua_info["is_bot"],
        is_proxy=ua_info["is_proxy"],
        proxy_type=ua_info["proxy_type"],
        opened_at=now,
        meta_data={
            "referer": headers.get("referer"),
            "accept_language": headers.get("accept-language"),
        },
    )
    db.add(open_event)
    await db.commit()
    await db.refresh(tracked_email)

    # 5. Build Alert Payload
    alert_payload = EmailOpenedAlertPayload(
        event="EMAIL_OPENED",
        tracked_email_id=tracked_email.id,
        tracking_token=tracked_email.tracking_token,
        sender_id=tracked_email.sender_id,
        recipient_email=tracked_email.recipient_email,
        subject=tracked_email.subject,
        open_count=tracked_email.open_count,
        is_first_open=is_first_open,
        opened_at=now,
        client_info={
            "ip_address": client_ip,
            "device_type": ua_info["device_type"],
            "client_name": ua_info["client_name"],
            "os_name": ua_info["os_name"],
            "is_proxy": ua_info["is_proxy"],
            "proxy_type": ua_info["proxy_type"],
        },
        meta_data=tracked_email.meta_data or {},
    )

    # 6. Check alert frequency preferences and trigger alert
    should_alert = True
    if settings.ALERT_ON_FIRST_OPEN_ONLY and not is_first_open:
        should_alert = False

    if should_alert:
        try:
            await redis_manager.publish_alert(alert_payload.model_dump())
            logger.info(
                f"Alert dispatched for email {tracked_email.id} to recipient {tracked_email.recipient_email} (Open #{tracked_email.open_count})"
            )
        except Exception as e:
            logger.error(f"Failed to publish alert for email {tracked_email.id}: {e}")

    return tracked_email
