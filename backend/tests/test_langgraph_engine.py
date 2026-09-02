import uuid
import pytest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.db.models import Tenant, Event, Session, SessionStatus
from app.agents.graph import compile_provisioning_graph, compile_triage_graph

@pytest.mark.asyncio
async def test_provisioning_graph_full_lifecycle_with_hitl():
    await init_db()
    
    # 1. Setup Tenant
    tenant_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=tenant_id, name="Vanguard Tech", slug=f"vanguard-{uuid.uuid4().hex[:6]}")
        db.add(tenant)
        await db.commit()

    # 2. Compile Graph with MemorySaver checkpointer
    checkpointer = MemorySaver()
    graph = compile_provisioning_graph(checkpointer)

    thread_config = {"configurable": {"thread_id": f"test_thread_{uuid.uuid4().hex[:8]}"}}
    initial_input = {
        "tenant_id": tenant_id,
        "raw_brief_text": "title: Vanguard Global AI Expo 2026\nTwo tracks, main keynotes on Stage A.",
        "planning_iteration": 0,
        "detected_conflicts": [],
        "executed_steps": []
    }

    # 3. Initial Run: Should execute parser -> planner -> verifier -> interrupt at hitl_gate
    state_step1 = await graph.ainvoke(initial_input, config=thread_config)
    
    # Check interrupt occurred
    snapshot = graph.get_state(thread_config)
    assert len(snapshot.tasks) > 0
    assert len(snapshot.tasks[0].interrupts) > 0
    
    interrupt_payload = snapshot.tasks[0].interrupts[0].value
    assert interrupt_payload["type"] == "PROVISIONING_MANIFEST_APPROVAL"
    assert interrupt_payload["diff_manifest"]["sessions_count"] == 2
    assert interrupt_payload["diff_manifest"]["tracks_count"] == 2

    # 4. Resume with Human Approval
    resumed_state = await graph.ainvoke(
        Command(resume={"decision": "APPROVED"}),
        config=thread_config
    )

    # 5. Verify Workers executed and Event was created in Database
    assert resumed_state.get("execution_complete") is True
    event_id = resumed_state.get("event_id")
    assert event_id is not None

    async with AsyncSessionLocal() as db:
        stmt = select(Event).where(Event.id == event_id)
        evt = (await db.execute(stmt)).scalar_one_or_none()
        assert evt is not None
        assert "Vanguard Global AI Expo 2026" in evt.title

        sess_stmt = select(Session).where(Session.event_id == event_id)
        sessions = (await db.execute(sess_stmt)).scalars().all()
        assert len(sessions) == 2

@pytest.mark.asyncio
async def test_live_triage_graph_with_hitl():
    await init_db()
    
    # 1. Setup Event and Session
    tenant_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=tenant_id, name="Triage Corp", slug=f"triage-{uuid.uuid4().hex[:6]}")
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        event = Event(
            id=event_id,
            tenant_id=tenant_id,
            title="Live Incident Summit",
            slug=f"live-summit-{uuid.uuid4().hex[:6]}",
            start_time=now,
            end_time=now + timedelta(days=1)
        )
        session = Session(
            id=session_id,
            tenant_id=tenant_id,
            event_id=event_id,
            title="Opening Keynote",
            start_time=now,
            end_time=now + timedelta(minutes=45),
            status=SessionStatus.SCHEDULED
        )
        db.add_all([tenant, event, session])
        await db.commit()

    # 2. Compile Triage Graph
    checkpointer = MemorySaver()
    triage_graph = compile_triage_graph(checkpointer)
    thread_config = {"configurable": {"thread_id": f"triage_thread_{uuid.uuid4().hex[:8]}"}}

    # 3. Trigger Incident Ingestion
    triage_input = {
        "tenant_id": tenant_id,
        "event_id": event_id,
        "session_id": session_id,
        "incident_type": "SPEAKER_NO_SHOW",
        "telemetry_data": {"minutes_late": 15}
    }

    await triage_graph.ainvoke(triage_input, config=thread_config)

    # 4. Verify Interrupt occurred with options
    snapshot = triage_graph.get_state(thread_config)
    assert len(snapshot.tasks) > 0
    assert len(snapshot.tasks[0].interrupts) > 0
    interrupt_data = snapshot.tasks[0].interrupts[0].value
    assert interrupt_data["type"] == "CRITICAL_LIVE_INCIDENT"
    assert len(interrupt_data["options"]) == 2

    # 5. Resume with Option 1: Swap Asset
    final_state = await triage_graph.ainvoke(
        Command(resume={"selected_option_id": "opt_swap_asset"}),
        config=thread_config
    )

    assert final_state["resolution_status"] == "RESOLVED"

    # Verify session was updated in DB
    async with AsyncSessionLocal() as db:
        stmt = select(Session).where(Session.id == session_id)
        updated_s = (await db.execute(stmt)).scalar_one()
        assert updated_s.status == SessionStatus.BACKSTAGE_READY
        assert updated_s.prerecorded_asset_url == "https://assets.cadence.ai/backup/keynote_backup.mp4"
