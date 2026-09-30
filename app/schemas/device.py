from pydantic import BaseModel, Field


class DeviceRegistrationRequest(BaseModel):
    device_token: str = Field(..., description="FCM device push registration token")
    platform: str = Field(default="android", description="Client platform (android, ios)")


class DeviceRegistrationResponse(BaseModel):
    success: bool
    message: str
    active_devices_count: int
