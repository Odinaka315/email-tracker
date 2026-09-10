from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.email import TrackedEmail
from app.schemas.email import (
    TrackedEmailCreate,
    TrackedEmailResponse,
    TrackedEmailDetailResponse,
)
from app.services.email_service import (
    generate_tracking_token,
    build_tracking_pixel_url,
    generate_tracking_pixel_html,
    inject_tracking_pixel,
    send_email_via_brevo,
)

router = APIRouter(prefix="/emails", tags=["Emails"])


def _format_email_response(email: TrackedEmail, base_url: str = None) -> TrackedEmailResponse:
    pixel_url = build_tracking_pixel_url(email.tracking_token, base_url)
    pixel_html = generate_tracking_pixel_html(email.tracking_token, base_url)
    return TrackedEmailResponse(
        id=email.id,
        index=email.index,
        sender_id=email.sender_id,
        tracking_token=email.tracking_token,
        recipient_email=email.recipient_email,
        subject=email.subject,
        status=email.status,
        open_count=email.open_count,
        click_count=email.click_count,
        first_opened_at=email.first_opened_at,
        last_opened_at=email.last_opened_at,
        meta_data=email.meta_data,
        created_at=email.created_at,
        updated_at=email.updated_at,
        tracking_pixel_url=pixel_url,
        tracking_pixel_html=pixel_html,
    )


@router.post("/track", response_model=TrackedEmailResponse, status_code=201)
async def create_tracked_email(
    payload: TrackedEmailCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new email for open tracking.
    Generates tracking token, tracking pixel URL, and optionally injects the pixel tag into provided HTML.
    """
    token = generate_tracking_token()
    base_url = str(request.base_url).rstrip("/")

    tracked_email = TrackedEmail(
        sender_id=payload.sender_id or "default_sender",
        tracking_token=token,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        status="SENT",
        meta_data=payload.meta_data or {},
    )

    db.add(tracked_email)
    await db.commit()
    await db.refresh(tracked_email)

    injected_html = None
    if payload.html_body:
        injected_html = inject_tracking_pixel(payload.html_body, token, base_url)

    res = _format_email_response(tracked_email, base_url)
    res.injected_html = injected_html
    return res


@router.post("/send", response_model=TrackedEmailResponse, status_code=201)
async def send_tracked_email(
    request: Request,
    recipient_email: str = Form(...),
    subject: str = Form(...),
    html_body: str = Form(...),
    sender_name: str = Form("Email Alerts"),
    sender_email: str = Form("no-reply@example.com"),
    sender_id: str = Form("default_sender"),
    attachments: Optional[List[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Sends an email with tracking pixel injected, and optional attachments.
    """
    token = generate_tracking_token()
    base_url = str(request.base_url).rstrip("/")

    # Inject tracking pixel into the provided HTML
    injected_html = inject_tracking_pixel(html_body, token, base_url)

    # Save to database
    tracked_email = TrackedEmail(
        sender_id=sender_id,
        tracking_token=token,
        recipient_email=recipient_email,
        subject=subject,
        status="SENT",
        meta_data={},
    )
    db.add(tracked_email)
    await db.commit()
    await db.refresh(tracked_email)

    # Send the email via Brevo
    try:
        await send_email_via_brevo(
            recipient_email=recipient_email,
            subject=subject,
            html_content=injected_html,
            sender_name=sender_name,
            sender_email=sender_email,
            attachments=attachments,
        )
    except Exception as e:
        # If sending fails, mark it in the DB and raise
        tracked_email.status = "FAILED"
        await db.commit()
        raise e

    res = _format_email_response(tracked_email, base_url)
    res.injected_html = injected_html
    return res


@router.get("", response_model=List[TrackedEmailResponse])
async def list_tracked_emails(
    request: Request,
    sender_id: Optional[str] = Query(None, description="Filter by sender ID"),
    status: Optional[str] = Query(None, description="Filter by status (SENT, OPENED)"),
    recipient: Optional[str] = Query(None, description="Filter by recipient email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists tracked emails with pagination and optional filters.
    """
    base_url = str(request.base_url).rstrip("/")
    stmt = select(TrackedEmail).order_by(desc(TrackedEmail.created_at)).offset(skip).limit(limit)

    if sender_id:
        stmt = stmt.where(TrackedEmail.sender_id == sender_id)
    if status:
        stmt = stmt.where(TrackedEmail.status == status)
    if recipient:
        stmt = stmt.where(TrackedEmail.recipient_email.ilike(f"%{recipient}%"))

    result = await db.execute(stmt)
    emails = result.scalars().all()

    return [_format_email_response(e, base_url) for e in emails]


@router.get("/{email_id}", response_model=TrackedEmailDetailResponse)
async def get_tracked_email_detail(
    email_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full details of a tracked email, including all recorded open events.
    """
    base_url = str(request.base_url).rstrip("/")
    stmt = (
        select(TrackedEmail)
        .where(TrackedEmail.id == email_id)
        .options(selectinload(TrackedEmail.open_events))
    )
    result = await db.execute(stmt)
    email = result.scalars().first()

    if not email:
        raise HTTPException(status_code=404, detail="Tracked email not found")

    res = _format_email_response(email, base_url)
    detail_res = TrackedEmailDetailResponse(**res.model_dump())
    detail_res.open_events = [e for e in email.open_events]
    return detail_res


@router.delete("/{email_id}", status_code=204)
async def delete_tracked_email(
    email_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a tracked email and its associated open/click events.
    """
    stmt = select(TrackedEmail).where(TrackedEmail.id == email_id)
    result = await db.execute(stmt)
    email = result.scalars().first()

    if not email:
        raise HTTPException(status_code=404, detail="Tracked email not found")

    await db.delete(email)
    await db.commit()
    return None
