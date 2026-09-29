import re
import html
import base64
import secrets
import urllib.parse
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


def convert_text_to_html(
    text: str,
    token: Optional[str] = None,
    base_url: Optional[str] = None,
    track_clicks: bool = True,
) -> str:
    """
    Converts normal/plain text into clean, modern email HTML.
    - Handles line breaks and paragraphs automatically.
    - Escapes HTML special characters to prevent corruption or injection.
    - Automatically detects URLs and converts them to clickable tracked links.
    - Wraps content in a responsive, clean email HTML template.
    """
    if not text:
        return ""

    # Normalize line endings
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    # If already a full HTML document, preserve it
    if normalized.lower().startswith("<!doctype") or normalized.lower().startswith("<html"):
        return normalized

    # Detect URLs and preserve them for conversion to links with click tracking
    url_pattern = re.compile(r"(https?://[^\s<>\"]+)")
    placeholders: List[str] = []

    def replacer(match: re.Match) -> str:
        raw_match = match.group(1)
        trailing = ""
        while raw_match and raw_match[-1] in ".,;:!?)]}":
            trailing = raw_match[-1] + trailing
            raw_match = raw_match[:-1]

        idx = len(placeholders)
        placeholders.append(raw_match)
        return f"__LINK_PLACEHOLDER_{idx}__{trailing}"

    processed_text = url_pattern.sub(replacer, normalized)

    # Escape HTML special characters in the text
    escaped_text = html.escape(processed_text)

    # Split into paragraphs (separated by 2 or more newlines)
    paragraphs = re.split(r"\n\s*\n", escaped_text)

    html_paragraphs = []
    host = (base_url or settings.BASE_URL).rstrip("/")

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        # Convert single newlines inside paragraph to <br/>
        p_html = p_clean.replace("\n", "<br/>")

        # Replace placeholders with HTML links
        for idx, orig_url in enumerate(placeholders):
            placeholder_tag = f"__LINK_PLACEHOLDER_{idx}__"
            if placeholder_tag in p_html:
                if track_clicks and token:
                    quoted_target = urllib.parse.quote(orig_url, safe="")
                    click_url = f"{host}{settings.API_V1_STR}/track/click/{token}?url={quoted_target}"
                else:
                    click_url = html.escape(orig_url)

                display_url = html.escape(orig_url)
                link_tag = (
                    f'<a href="{click_url}" target="_blank" rel="noopener noreferrer" '
                    f'style="color: #2563eb; text-decoration: underline;">{display_url}</a>'
                )
                p_html = p_html.replace(placeholder_tag, link_tag)

        html_paragraphs.append(
            f'    <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #222222;">{p_html}</p>'
        )

    body_content = "\n".join(html_paragraphs)

    return (
        '<!DOCTYPE html>\n'
        '<html>\n'
        '<head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '</head>\n'
        '<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, '
        '\'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; background-color: #ffffff;">\n'
        '  <div style="max-width: 600px; margin: 0 auto;">\n'
        f'{body_content}\n'
        '  </div>\n'
        '</body>\n'
        '</html>'
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
    text_content: Optional[str] = None,
    sender_name: str = "Email Alerts",
    sender_email: str = "nwolisaodinaka5@gmail.com",
    attachments: Optional[List[UploadFile]] = None,
) -> dict:
    """
    Sends an email using the Brevo API, including optional file attachments and plain text fallback.
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
    if text_content:
        payload["textContent"] = text_content

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
