from typing import Dict, Any
from user_agents import parse


def parse_user_agent(ua_string: str) -> Dict[str, Any]:
    """
    Parses the User-Agent string to extract client, device, OS, and proxy detection info.
    """
    if not ua_string:
        return {
            "device_type": "UNKNOWN",
            "client_name": "Unknown Client",
            "os_name": "Unknown OS",
            "is_bot": False,
            "is_proxy": False,
            "proxy_type": None,
        }

    ua_lower = ua_string.lower()

    # Detect Known Email Image Proxies
    is_proxy = False
    proxy_type = None

    if "googleimageproxy" in ua_lower:
        is_proxy = True
        proxy_type = "Google Image Proxy (Gmail)"
        return {
            "device_type": "PROXY",
            "client_name": "Gmail (Google Image Proxy)",
            "os_name": "Google Cloud",
            "is_bot": False,
            "is_proxy": True,
            "proxy_type": proxy_type,
        }

    if (
        "applemail" in ua_lower
        or "mailprivacyprotection" in ua_lower
        or ("mozilla/5.0" in ua_lower and "apple" in ua_lower and "mac os x 10_15_7" in ua_lower and "safari" not in ua_lower)
    ):
        is_proxy = True
        proxy_type = "Apple Mail Privacy Protection (MPP)"

    if "yahoo! slurp" in ua_lower or ("yahoo" in ua_lower and "image" in ua_lower):
        is_proxy = True
        proxy_type = "Yahoo Mail Proxy"

    # Standard User-Agent parsing
    user_agent = parse(ua_string)

    device_type = "DESKTOP"
    if user_agent.is_mobile:
        device_type = "MOBILE"
    elif user_agent.is_tablet:
        device_type = "TABLET"
    elif user_agent.is_bot:
        device_type = "BOT"
    elif user_agent.is_pc:
        device_type = "DESKTOP"

    # Identify Client/App
    client_name = f"{user_agent.browser.family} {user_agent.browser.version_string}".strip()
    if "outlook" in ua_lower or "office" in ua_lower:
        client_name = "Microsoft Outlook"
    elif "thunderbird" in ua_lower:
        client_name = "Mozilla Thunderbird"
    elif "apple mail" in ua_lower or "mail/" in ua_lower:
        client_name = "Apple Mail"

    os_name = f"{user_agent.os.family} {user_agent.os.version_string}".strip()

    return {
        "device_type": device_type,
        "client_name": client_name if client_name else "Generic Browser / Client",
        "os_name": os_name if os_name else "Unknown OS",
        "is_bot": bool(user_agent.is_bot),
        "is_proxy": is_proxy,
        "proxy_type": proxy_type,
    }


def get_client_ip(headers: Dict[str, str], client_host: str = "") -> str:
    """
    Extracts the real client IP from reverse proxy headers like X-Forwarded-For or CF-Connecting-IP.
    Case-insensitive header key lookup.
    """
    if not headers:
        return client_host or "127.0.0.1"

    # Normalize header keys to lowercase
    lower_headers = {k.lower(): v for k, v in headers.items()}

    # Check CF-Connecting-IP (Cloudflare)
    if "cf-connecting-ip" in lower_headers:
        return lower_headers["cf-connecting-ip"].strip()

    # Check X-Forwarded-For
    if "x-forwarded-for" in lower_headers:
        forwarded = lower_headers["x-forwarded-for"].split(",")
        if forwarded:
            return forwarded[0].strip()

    # Check X-Real-IP
    if "x-real-ip" in lower_headers:
        return lower_headers["x-real-ip"].strip()

    return client_host or "127.0.0.1"

