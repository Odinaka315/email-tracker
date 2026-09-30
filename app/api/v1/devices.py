import logging
from fastapi import APIRouter
from app.schemas.device import DeviceRegistrationRequest, DeviceRegistrationResponse
from app.services.fcm_service import register_device_token, load_device_tokens

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["Devices & Push Notifications"])


@router.post("/register", response_model=DeviceRegistrationResponse)
async def register_device(payload: DeviceRegistrationRequest):
    """
    Registers a mobile device FCM push token.
    Enables background push notifications when tracked emails are opened.
    """
    success = register_device_token(payload.device_token)
    active_count = len(load_device_tokens())

    return DeviceRegistrationResponse(
        success=success,
        message=(
            "Device token registered successfully for push notifications."
            if success
            else "Failed to register device token."
        ),
        active_devices_count=active_count,
    )
