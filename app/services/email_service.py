import re
import base64
import secrets
from typing import Tuple, List, Optional
import httpx
from fastapi import UploadFile, HTTPException
from app.config import settings


def generate_tracking_token() -> str:
    """
    Generates a secure, URL-safe random tracking token.
    """
    return f"trk_{secrets.token_urlsafe(24)}"


def build_tracking_pixel_url(token: str, base_url: str = None) -> str:
    """
    Constructs the absolute URL for the 1x1 tracking GIF.
    """
    host = base_url or settings.BASE_URL
    return f"{host.rstrip('/')}{settings.API_V1_STR}/track/open/{token}.gif"


def generate_tracking_pixel_html(token: str, base_url: str = None) -> str:
    """
    Generates the HTML <img> tag for the tracking pixel with hiding styles.
    """
    url = build_tracking_pixel_url(token, base_url)
    return (
        f'<img src="{url}" alt="" width="1" height="1" border="0" '
        f'style="height:1px!important;width:1px!important;border-width:0!important;'
        f'margin-top:0!important;margin-bottom:0!important;margin-right:0!important;'
        f'margin-left:0!important;padding-top:0!important;padding-bottom:0!important;'
        f'padding-right:0!important;padding-left:0!important;display:none!important;" />'
    )


def inject_tracking_pixel(html_content: str, token: str, base_url: str = None) -> str:
    """
    Injects the tracking pixel tag right before </body>, or appends it to the end of the HTML.
    """
    if not html_content:
        return ""

    pixel_tag = generate_tracking_pixel_html(token, base_url)

    # Check for closing </body> tag
    if re.search(r"</body>", html_content, flags=re.IGNORECASE):
        return re.sub(
            r"</body>",
            f"{pixel_tag}\n</body>",
            html_content,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        # If no body tag exists, append to end
        return f"{html_content}\n{pixel_tag}"


async def send_email_via_brevo(
    recipient_email: str,
    subject: str,
    html_content: str,
    sender_name: str = "Email Alerts",
    sender_email: str = "no-reply@example.com",
    attachments: Optional[List[UploadFile]] = None,
) -> dict:
    """
    Sends an email using the Brevo API, including optional file attachments.
    """
    if not settings.BREVO_API_KEY:
        raise HTTPException(
            status_code=500, detail="BREVO_API_KEY is not configured in environment."
        )

    brevo_url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    # Prepare payload
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    # Handle attachments
    if attachments:
        brevo_attachments = []
        for file in attachments:
            file_bytes = await file.read()
            b64_content = base64.b64encode(file_bytes).decode("utf-8")
            brevo_attachments.append({
                "name": file.filename,
                "content": b64_content
            })
        if brevo_attachments:
            payload["attachment"] = brevo_attachments

    async with httpx.AsyncClient() as client:
        response = await client.post(brevo_url, headers=headers, json=payload)

    if response.status_code not in (200, 201, 202):
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send email via Brevo. Status: {response.status_code}, Body: {response.text}"
        )

    return response.json()
