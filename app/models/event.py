import uuid
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from app.database import Base


class OpenEvent(Base):
    __tablename__ = "open_events"

    index = Column(Integer, autoincrement=True, unique=True, nullable=False)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tracked_email_id = Column(String(36), ForeignKey("tracked_emails.id", ondelete="CASCADE"), nullable=False, index=True)
    
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(1000), nullable=True)
    device_type = Column(String(50), default="UNKNOWN", nullable=False)
    client_name = Column(String(100), nullable=True)
    os_name = Column(String(100), nullable=True)
    
    is_bot = Column(Boolean, default=False, nullable=False)
    is_proxy = Column(Boolean, default=False, nullable=False)
    proxy_type = Column(String(100), nullable=True)
    
    country = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    meta_data = Column(JSON, nullable=True, default=dict)

    tracked_email = relationship("TrackedEmail", back_populates="open_events")


class ClickEvent(Base):
    __tablename__ = "click_events"

    index = Column(Integer, autoincrement=True, unique=True, nullable=False)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tracked_email_id = Column(String(36), ForeignKey("tracked_emails.id", ondelete="CASCADE"), nullable=False, index=True)
    
    target_url = Column(String(2048), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(1000), nullable=True)
    device_type = Column(String(50), default="UNKNOWN", nullable=False)
    
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    meta_data = Column(JSON, nullable=True, default=dict)

    tracked_email = relationship("TrackedEmail", back_populates="click_events")
