from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EmailOpenedAlertPayload(BaseModel):
    event: str = "EMAIL_OPENED"
    tracked_email_id: str
    tracking_token: str
    sender_id: str
    recipient_email: str
    subject: Optional[str] = None
    open_count: int
    is_first_open: bool
    opened_at: datetime
    client_info: Dict[str, Any] = Field(default_factory=dict)
    meta_data: Optional[Dict[str, Any]] = None
