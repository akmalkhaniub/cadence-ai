import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.db.models import EventFormat, SessionFormat, SponsorTier

class CreateEventInput(BaseModel):
    tenant_id: str
    title: str = Field(..., min_length=3, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    format: EventFormat = EventFormat.VIRTUAL
    timezone: str = "UTC"
    start_time: datetime
    end_time: datetime
    branding: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("end_time")
    @classmethod
    def validate_dates(cls, v: datetime, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("Event end_time must be strictly after start_time.")
        return v

class CreateTrackInput(BaseModel):
    tenant_id: str
    event_id: str
    name: str = Field(..., min_length=2, max_length=150)
    color_hex: str = Field("#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    display_order: int = 0
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))

class CreateRoomInput(BaseModel):
    tenant_id: str
    event_id: str
    name: str = Field(..., min_length=2, max_length=150)
    physical_capacity: Optional[int] = Field(None, gt=0, lt=100000)
    is_virtual: bool = True
    stream_provider: Optional[str] = "RTMP"
    primary_stream_url: Optional[str] = None
    backup_stream_url: Optional[str] = None
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))

class ScheduleSessionInput(BaseModel):
    tenant_id: str
    event_id: str
    track_id: Optional[str] = None
    room_id: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=255)
    abstract: Optional[str] = None
    format: SessionFormat = SessionFormat.KEYNOTE
    start_time: datetime
    end_time: datetime
    speaker_ids: List[str] = Field(default_factory=list)
    max_attendees: Optional[int] = Field(None, gt=0)
    prerecorded_asset_url: Optional[str] = None
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("end_time")
    @classmethod
    def validate_duration(cls, v: datetime, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("Session end_time must be strictly after start_time.")
        if start:
            duration_mins = (v - start).total_seconds() / 60
            if duration_mins < 10 or duration_mins > 480:
                raise ValueError(f"Session duration ({duration_mins:.1f}m) must be between 10m and 8h.")
        return v

class DetectConflictsInput(BaseModel):
    event_id: str
    room_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    speaker_ids: List[str] = Field(default_factory=list)
    exclude_session_id: Optional[str] = None

class ProvisionBoothInput(BaseModel):
    tenant_id: str
    event_id: str
    sponsor_name: str = Field(..., min_length=2, max_length=255)
    tier: SponsorTier = SponsorTier.SILVER
    logo_url: str
    website_url: Optional[str] = None
    booth_3d_template: str = "standard_booth_v1"
    branding_assets: Dict[str, Any] = Field(default_factory=dict)
    rep_emails: List[str] = Field(default_factory=list)
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))

class RollbackTransactionInput(BaseModel):
    tenant_id: str
    transaction_id: str
