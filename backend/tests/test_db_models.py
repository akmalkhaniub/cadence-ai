import uuid
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.session import Base
from app.db.models import (
    Tenant, Event, Track, Room, Speaker, Session, SessionSpeaker,
    Sponsor, Booth, TicketTier, Attendee, LiveIncident, AgentTransactionJournal,
    EventFormat, EventStatus, SessionFormat, SessionStatus, SpeakerRole,
    SponsorTier, IncidentType, IncidentSeverity, IncidentStatus
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_create_full_event_hierarchy(db_session: AsyncSession):
    # 1. Create Tenant
    tenant = Tenant(
        name="TechCorp Global",
        slug=f"techcorp-{uuid.uuid4().hex[:6]}"
    )
    db_session.add(tenant)
    await db_session.flush()
    assert tenant.id is not None

    # 2. Create Event
    now = datetime.utcnow()
    event = Event(
        tenant_id=tenant.id,
        title="Global AI Summit 2026",
        slug="ai-summit-2026",
        format=EventFormat.HYBRID,
        status=EventStatus.DRAFT,
        start_time=now + timedelta(days=30),
        end_time=now + timedelta(days=32),
        timezone="America/New_York",
        branding={"primary_color": "#2563EB", "logo_url": "https://example.com/logo.png"}
    )
    db_session.add(event)
    await db_session.flush()
    assert event.id is not None

    # 3. Create Track & Room
    track = Track(
        tenant_id=tenant.id,
        event_id=event.id,
        name="Autonomous Agents Track",
        color_hex="#10B981",
        display_order=1
    )
    room = Room(
        tenant_id=tenant.id,
        event_id=event.id,
        name="Main Auditorium A",
        physical_capacity=500,
        is_virtual=True,
        stream_provider="RTMP",
        primary_stream_url="rtmp://live.example.com/stream1"
    )
    db_session.add_all([track, room])
    await db_session.flush()

    # 4. Create Speaker & Session
    speaker = Speaker(
        tenant_id=tenant.id,
        event_id=event.id,
        email="dr.reed@ai-institute.org",
        full_name="Dr. Samantha Reed",
        title="Chief AI Scientist",
        company="AI Research Labs",
        bio="Pioneer in multi-agent reinforcement learning."
    )
    db_session.add(speaker)
    await db_session.flush()

    session_start = event.start_time + timedelta(hours=1)
    session_end = session_start + timedelta(minutes=45)
    session_obj = Session(
        tenant_id=tenant.id,
        event_id=event.id,
        track_id=track.id,
        room_id=room.id,
        title="Keynote: Scalable Agentic Systems with LangGraph",
        abstract="Deep dive into state machines and deterministic rollbacks.",
        format=SessionFormat.KEYNOTE,
        status=SessionStatus.SCHEDULED,
        start_time=session_start,
        end_time=session_end,
        duration_minutes=45,
        max_attendees=500
    )
    db_session.add(session_obj)
    await db_session.flush()

    # Link Speaker to Session
    session_speaker = SessionSpeaker(
        session_id=session_obj.id,
        speaker_id=speaker.id,
        role=SpeakerRole.KEYNOTE_SPEAKER
    )
    db_session.add(session_speaker)
    await db_session.flush()

    # 5. Create Sponsor & Booth
    sponsor = Sponsor(
        tenant_id=tenant.id,
        event_id=event.id,
        name="CloudScale Systems",
        tier=SponsorTier.PLATINUM,
        logo_url="https://example.com/cloudscale.svg",
        website_url="https://cloudscale.example.com"
    )
    db_session.add(sponsor)
    await db_session.flush()

    booth = Booth(
        tenant_id=tenant.id,
        event_id=event.id,
        sponsor_id=sponsor.id,
        name="CloudScale Pavilion",
        booth_3d_template="platinum_booth_v2",
        branding_assets={"banner": "https://example.com/banner.png"},
        rep_emails=["rep1@cloudscale.com", "rep2@cloudscale.com"]
    )
    db_session.add(booth)
    await db_session.flush()

    # 6. Create TicketTier & Attendee
    tier = TicketTier(
        tenant_id=tenant.id,
        event_id=event.id,
        name="VIP All-Access Pass",
        price_cents=49900,
        total_capacity=200,
        allowed_tracks=["*"]
    )
    db_session.add(tier)
    await db_session.flush()

    attendee = Attendee(
        tenant_id=tenant.id,
        event_id=event.id,
        ticket_tier_id=tier.id,
        email="alex.chen@enterprise.com",
        full_name="Alex Chen",
        company="Enterprise AI Corp",
        job_title="Lead Architect",
        badge_qr_hash=uuid.uuid4().hex
    )
    db_session.add(attendee)
    await db_session.flush()

    # 7. Test Saga Transaction Journal
    journal_entry = AgentTransactionJournal(
        tenant_id=tenant.id,
        agent_run_id="run_test_12345",
        idempotency_key=str(uuid.uuid4()),
        tool_name="sessions.schedule_session",
        target_table="sessions",
        target_id=session_obj.id,
        operation="INSERT",
        forward_payload={"title": session_obj.title, "room_id": room.id},
        compensating_patch={"tool_name": "sessions.delete_session", "session_id": session_obj.id}
    )
    db_session.add(journal_entry)
    await db_session.commit()

    # Eager load verification
    stmt = (
        select(Session)
        .where(Session.id == session_obj.id)
        .options(
            selectinload(Session.track),
            selectinload(Session.room),
            selectinload(Session.speaker_associations).selectinload(SessionSpeaker.speaker)
        )
    )
    result = await db_session.execute(stmt)
    loaded_session = result.scalar_one()

    # Assertions
    assert loaded_session.track.name == "Autonomous Agents Track"
    assert loaded_session.room.name == "Main Auditorium A"
    assert len(loaded_session.speaker_associations) == 1
    assert loaded_session.speaker_associations[0].speaker.full_name == "Dr. Samantha Reed"
    assert journal_entry.is_reverted is False
