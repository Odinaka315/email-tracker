import os
import json
import logging
from typing import Optional, Set
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

TOKENS_FILE = "device_tokens.json"


def init_firebase() -> bool:
    """
    Initializes the Firebase Admin SDK using serviceAccountKey.json
    or the FIREBASE_CREDENTIALS_JSON environment variable.
    """
    if firebase_admin._apps:
        return True

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

    try:
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized via FIREBASE_CREDENTIALS_JSON env var.")
            return True
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized via file: {cred_path}")
            return True
        else:
            logger.warning(
                f"Firebase service account not found at '{cred_path}'. "
                "Push notifications to closed apps will be disabled until configured."
            )
            return False
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False


def load_device_tokens() -> Set[str]:
    """Loads all registered device tokens from disk."""
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.error(f"Error reading {TOKENS_FILE}: {e}")
    return set()


def register_device_token(token: str) -> bool:
    """Adds a new FCM device token and persists it to disk."""
    if not token or not isinstance(token, str):
        return False

    tokens = load_device_tokens()
    if token in tokens:
        return True

    tokens.add(token)
    try:
        with open(TOKENS_FILE, "w") as f:
            json.dump(list(tokens), f, indent=2)
        logger.info(f"FCM device token registered. Total active devices: {len(tokens)}")
        return True
    except Exception as e:
        logger.error(f"Failed to write to {TOKENS_FILE}: {e}")
        return False


async def send_email_opened_push(
    recipient_email: str,
    subject: str,
    email_id: str,
    open_count: int = 1,
) -> int:
    """
    Sends an FCM push notification to all registered device tokens.
    Wakes up the mobile device and displays an alert in the system notification tray,
    even if the Flutter app is completely killed or the screen is locked.
    """
    if not init_firebase():
        logger.warning("FCM Push skipped: Firebase Admin is not initialized.")
        return 0

    tokens = load_device_tokens()
    if not tokens:
        logger.info("FCM Push skipped: No registered device tokens.")
        return 0

    title = "🔔 Email Opened!"
    body = f"{recipient_email} opened '{subject}' (Open #{open_count})"

    success_count = 0
    dead_tokens = []

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    "email_id": str(email_id),
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                token=token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="email_alerts_channel",
                        icon="@mipmap/ic_launcher",
                        color="#26C6DA",
                        sound="default",
                    ),
                ),
            )
            response = messaging.send(message)
            logger.info(f"FCM push delivered to device: {response}")
            success_count += 1
        except messaging.UnregisteredError:
            logger.info(f"Stale FCM token detected ({token[:15]}...), marking for cleanup.")
            dead_tokens.append(token)
        except Exception as e:
            logger.error(f"Failed to deliver FCM push to device {token[:15]}...: {e}")

    # Remove expired or invalidated device tokens
    if dead_tokens:
        remaining = tokens - set(dead_tokens)
        try:
            with open(TOKENS_FILE, "w") as f:
                json.dump(list(remaining), f, indent=2)
        except Exception as e:
            logger.error(f"Error updating {TOKENS_FILE} after token cleanup: {e}")

    return success_count
