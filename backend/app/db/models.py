import uuid
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, ForeignKey, 
    Enum as SQLEnum, JSON, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

# ==========================================
# Domain Enums
# ==========================================

class EventFormat(str, enum.Enum):
    VIRTUAL = "VIRTUAL"
    HYBRID = "HYBRID"
    IN_PERSON = "IN_PERSON"

class EventStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIGURED = "CONFIGURED"
    PUBLISHED = "PUBLISHED"
    LIVE = "LIVE"
    CONCLUDED = "CONCLUDED"
    ARCHIVED = "ARCHIVED"

class SessionFormat(str, enum.Enum):
    KEYNOTE = "KEYNOTE"
    PANEL = "PANEL"
    WORKSHOP = "WORKSHOP"
    BREAKOUT = "BREAKOUT"
    LIGHTNING_TALK = "LIGHTNING_TALK"
    NETWORKING = "NETWORKING"

class SessionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    BACKSTAGE_READY = "BACKSTAGE_READY"
    LIVE = "LIVE"
    OVERRUN = "OVERRUN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"

class SpeakerRole(str, enum.Enum):
    KEYNOTE_SPEAKER = "KEYNOTE_SPEAKER"
    PANELIST = "PANELIST"
    MODERATOR = "MODERATOR"
    WORKSHOP_LEAD = "WORKSHOP_LEAD"
    MC = "MC"

class SponsorTier(str, enum.Enum):
    TITLE = "TITLE"
    PLATINUM = "PLATINUM"
    GOLD = "GOLD"
    SILVER = "SILVER"
    BRONZE = "BRONZE"
    COMMUNITY = "COMMUNITY"

class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentType(str, enum.Enum):
    SPEAKER_NO_SHOW = "SPEAKER_NO_SHOW"
    SESSION_OVERRUN = "SESSION_OVERRUN"
    STREAM_FAILURE = "STREAM_FAILURE"
    ROOM_CAPACITY_BREACH = "ROOM_CAPACITY_BREACH"

class IncidentStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    HITL_REVIEW = "HITL_REVIEW"
    APPLIED = "APPLIED"
    REVERTED = "REVERTED"
    DISMISSED = "DISMISSED"

# ==========================================
# Core Domain Models
# ==========================================

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events: Mapped[List["Event"]] = relationship("Event", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format: Mapped[EventFormat] = mapped_column(SQLEnum(EventFormat), default=EventFormat.VIRTUAL, nullable=False)
    status: Mapped[EventStatus] = mapped_column(SQLEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    branding: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    version_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_tenant_event_slug"),
        CheckConstraint("end_time > start_time", name="chk_event_dates"),
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="events")
    tracks: Mapped[List["Track"]] = relationship("Track", back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    rooms: Mapped[List["Room"]] = relationship("Room", back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    speakers: Mapped[List["Speaker"]] = relationship("Speaker", back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    sponsors: Mapped[List["Sponsor"]] = relationship("Sponsor", back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    ticket_tiers: Mapped[List["TicketTier"]] = relationship("TicketTier", back_populates="event", cascade="all, delete-orphan", lazy="selectin")


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_event_track_name"),
    )

    event: Mapped["Event"] = relationship("Event", back_populates="tracks")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="track", lazy="selectin")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    physical_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_virtual: Mapped[bool] = mapped_column(Boolean, default=True)
    stream_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    primary_stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    backup_stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_event_room_name"),
    )

    event: Mapped["Event"] = relationship("Event", back_populates="rooms")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="room", lazy="selectin")


class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio_embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_event_speaker_email"),
    )

    event: Mapped["Event"] = relationship("Event", back_populates="speakers")
    session_associations: Mapped[List["SessionSpeaker"]] = relationship("SessionSpeaker", back_populates="speaker", lazy="selectin")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    track_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True)
    room_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format: Mapped[SessionFormat] = mapped_column(SQLEnum(SessionFormat), default=SessionFormat.KEYNOTE, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.DRAFT, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_attendees: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prerecorded_asset_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract_embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    version_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="chk_session_times"),
    )

    event: Mapped["Event"] = relationship("Event", back_populates="sessions")
    track: Mapped[Optional["Track"]] = relationship("Track", back_populates="sessions", lazy="selectin")
    room: Mapped[Optional["Room"]] = relationship("Room", back_populates="sessions", lazy="selectin")
    speaker_associations: Mapped[List["SessionSpeaker"]] = relationship("SessionSpeaker", back_populates="session", cascade="all, delete-orphan", lazy="selectin")


class SessionSpeaker(Base):
    __tablename__ = "session_speakers"

    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    speaker_id: Mapped[str] = mapped_column(String(36), ForeignKey("speakers.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[SpeakerRole] = mapped_column(SQLEnum(SpeakerRole), default=SpeakerRole.KEYNOTE_SPEAKER)
    checkin_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="speaker_associations")
    speaker: Mapped["Speaker"] = relationship("Speaker", back_populates="session_associations", lazy="selectin")


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[SponsorTier] = mapped_column(SQLEnum(SponsorTier), default=SponsorTier.SILVER, nullable=False)
    logo_url: Mapped[str] = mapped_column(Text, nullable=False)
    website_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped["Event"] = relationship("Event", back_populates="sponsors")
    booth: Mapped[Optional["Booth"]] = relationship("Booth", back_populates="sponsor", uselist=False, cascade="all, delete-orphan", lazy="selectin")


class Booth(Base):
    __tablename__ = "booths"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    sponsor_id: Mapped[str] = mapped_column(String(36), ForeignKey("sponsors.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    booth_3d_template: Mapped[str] = mapped_column(String(50), default="standard_booth_v1")
    branding_assets: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    rep_emails: Mapped[List[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sponsor: Mapped["Sponsor"] = relationship("Sponsor", back_populates="booth")


class TicketTier(Base):
    __tablename__ = "ticket_tiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allowed_tracks: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["*"])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    event: Mapped["Event"] = relationship("Event", back_populates="ticket_tiers")
    attendees: Mapped[List["Attendee"]] = relationship("Attendee", back_populates="ticket_tier", lazy="selectin")


class Attendee(Base):
    __tablename__ = "attendees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    ticket_tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("ticket_tiers.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interests_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interests_embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    badge_qr_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_event_attendee_email"),
    )

    ticket_tier: Mapped["TicketTier"] = relationship("TicketTier", back_populates="attendees")


class LiveIncident(Base):
    __tablename__ = "live_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    incident_type: Mapped[IncidentType] = mapped_column(SQLEnum(IncidentType), nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(SQLEnum(IncidentSeverity), default=IncidentSeverity.MEDIUM, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(SQLEnum(IncidentStatus), default=IncidentStatus.DETECTED, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    proposed_remedy: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    operator_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AgentTransactionJournal(Base):
    """Saga Pattern Transaction Journal for Compensating Rollbacks."""
    __tablename__ = "agent_transaction_journal"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agent_run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False) # INSERT, UPDATE, DELETE
    forward_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    compensating_patch: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_reverted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
