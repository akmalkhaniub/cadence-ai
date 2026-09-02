import uuid
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.db.session import Base
from app.db.models import Tenant, Event, Session, EventFormat, SessionFormat, SponsorTier
from app.mcp_server.schemas import (
    CreateEventInput, CreateTrackInput, CreateRoomInput, 
    ScheduleSessionInput, DetectConflictsInput, ProvisionBoothInput
)
from app.mcp_server.service import MCPService

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
async def test_mcp_event_creation_and_conflict_detection(db_session: AsyncSession):
    # 1. Setup Tenant
    tenant_id = str(uuid.uuid4())
    tenant = Tenant(id=tenant_id, name="Apex Summits", slug=f"apex-{uuid.uuid4().hex[:6]}")
    db_session.add(tenant)
    await db_session.commit()

    # 2. Create Event via MCP Service
    now = datetime.utcnow()
    event_input = CreateEventInput(
        tenant_id=tenant_id,
        title="Cadence Agent Summit 2026",
        slug="cadence-agent-summit",
        format=EventFormat.VIRTUAL,
        start_time=now + timedelta(days=10),
        end_time=now + timedelta(days=12)
    )
    event_res = await MCPService.create_event(db_session, event_input)
    assert event_res["status"] == "SUCCESS"
    event_id = event_res["event_id"]

    # 3. Create Track and Room
    track_res = await MCPService.create_track(
        db_session,
        CreateTrackInput(tenant_id=tenant_id, event_id=event_id, name="Keynote Stream")
    )
    track_id = track_res["track_id"]

    room_res = await MCPService.create_room(
        db_session,
        CreateRoomInput(tenant_id=tenant_id, event_id=event_id, name="Hall A", physical_capacity=300)
    )
    room_id = room_res["room_id"]

    # 4. Schedule Session 1 (10:00 to 11:00 AM)
    start_s1 = event_input.start_time + timedelta(hours=10)
    end_s1 = start_s1 + timedelta(minutes=60)
    s1_idempotency = str(uuid.uuid4())

    s1_res = await MCPService.schedule_session(
        db_session,
        ScheduleSessionInput(
            tenant_id=tenant_id,
            event_id=event_id,
            track_id=track_id,
            room_id=room_id,
            title="Keynote: Future of Autonomy",
            format=SessionFormat.KEYNOTE,
            start_time=start_s1,
            end_time=end_s1,
            idempotency_key=s1_idempotency
        )
    )
    assert s1_res["status"] == "SUCCESS"
    s1_id = s1_res["session_id"]
    s1_tx = s1_res["transaction_id"]

    # 5. Idempotent Replay Test: re-send identical request
    s1_replay = await MCPService.schedule_session(
        db_session,
        ScheduleSessionInput(
            tenant_id=tenant_id,
            event_id=event_id,
            track_id=track_id,
            room_id=room_id,
            title="Keynote: Future of Autonomy",
            format=SessionFormat.KEYNOTE,
            start_time=start_s1,
            end_time=end_s1,
            idempotency_key=s1_idempotency
        )
    )
    assert s1_replay.get("idempotent_replay") is True
    assert s1_replay["target_id"] == s1_id

    # 6. Conflict Detection Test: Attempt to book overlapping time (10:30 to 11:30 AM) in Room A
    start_s2 = start_s1 + timedelta(minutes=30) # Overlaps with Session 1
    end_s2 = start_s2 + timedelta(minutes=60)

    conflict_res = await MCPService.schedule_session(
        db_session,
        ScheduleSessionInput(
            tenant_id=tenant_id,
            event_id=event_id,
            track_id=track_id,
            room_id=room_id,
            title="Conflicting Panel",
            format=SessionFormat.PANEL,
            start_time=start_s2,
            end_time=end_s2
        )
    )
    assert conflict_res["status"] == "ERROR_CONFLICT"
    assert len(conflict_res["conflicts"]) == 1
    assert conflict_res["conflicts"][0]["conflict_type"] == "ROOM_DOUBLE_BOOKING"
    assert conflict_res["conflicts"][0]["conflicting_session_id"] == s1_id

    # 7. Live Incident Triage Test: Swap session media asset
    swap_res = await MCPService.update_session_media(
        db_session,
        session_id=s1_id,
        asset_url="https://cdn.example.com/backup_keynote.mp4"
    )
    assert swap_res["status"] == "SUCCESS"
    assert swap_res["updated_media_url"] == "https://cdn.example.com/backup_keynote.mp4"

    # 8. Saga Rollback Test: Revert Session 1
    rollback_res = await MCPService.rollback_transaction(
        db_session,
        tenant_id=tenant_id,
        transaction_id=s1_tx
    )
    assert rollback_res["status"] == "SUCCESS"
    assert rollback_res["action_reverted"] == "sessions.delete_session"

    # Confirm Session 1 is deleted
    stmt = select(Session).where(Session.id == s1_id)
    deleted_check = (await db_session.execute(stmt)).scalar_one_or_none()
    assert deleted_check is None, "Session 1 should have been deleted by Saga rollback!"
