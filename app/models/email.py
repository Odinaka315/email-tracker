import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class TrackedEmail(Base):
    __tablename__ = "tracked_emails"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(100), index=True, nullable=False, default="default_sender")
    tracking_token = Column(String(64), unique=True, index=True, nullable=False)
    recipient_email = Column(String(255), index=True, nullable=False)
    subject = Column(String(500), nullable=True)
    
    # Status: 'SENT', 'OPENED'
    status = Column(String(20), default="SENT", nullable=False)
    
    # Metrics
    open_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    
    first_opened_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True)
    
    # Metadata for tags, campaign names, client IDs, etc.
    meta_data = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    open_events = relationship(
        "OpenEvent",
        back_populates="tracked_email",
        cascade="all, delete-orphan",
        order_by="desc(OpenEvent.opened_at)",
    )
    click_events = relationship(
        "ClickEvent",
        back_populates="tracked_email",
        cascade="all, delete-orphan",
        order_by="desc(ClickEvent.clicked_at)",
    )
