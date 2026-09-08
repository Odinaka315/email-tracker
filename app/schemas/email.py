from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TrackedEmailCreate(BaseModel):
    recipient_email: str = Field(..., description="Recipient email address")
    subject: Optional[str] = Field(None, description="Email subject line")
    sender_id: Optional[str] = Field("default_sender", description="ID of sender or user account")
    html_body: Optional[str] = Field(None, description="Raw HTML email content to inject pixel into")
    meta_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata tags")


class TrackedEmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_id: str
    tracking_token: str
    recipient_email: str
    subject: Optional[str] = None
    status: str
    open_count: int
    click_count: int
    first_opened_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    tracking_pixel_url: Optional[str] = None
    tracking_pixel_html: Optional[str] = None
    injected_html: Optional[str] = None


class OpenEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tracked_email_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: str
    client_name: Optional[str] = None
    os_name: Optional[str] = None
    is_bot: bool
    is_proxy: bool
    proxy_type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    opened_at: datetime
    meta_data: Optional[Dict[str, Any]] = None


class TrackedEmailDetailResponse(TrackedEmailResponse):
    open_events: List[OpenEventResponse] = []

