import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.agents.graph import compile_provisioning_graph, compile_triage_graph
from app.mcp_server.service import MCPService
from app.config import settings

router = APIRouter(prefix="/events", tags=["events"])

# In-memory thread checkpointer registry for gateway runtime
checkpointer = MemorySaver()
provisioning_engine = compile_provisioning_graph(checkpointer)
triage_engine = compile_triage_graph(checkpointer)

class ProvisionRequest(BaseModel):
    tenant_id: Optional[str] = None
    raw_brief_text: str

class ResumeRequest(BaseModel):
    decision: str = "APPROVED" # "APPROVED" | "REJECTED"
    feedback: Optional[str] = None

class IncidentSimulateRequest(BaseModel):
    tenant_id: Optional[str] = None
    event_id: str
    session_id: str
    incident_type: str = "SPEAKER_NO_SHOW"

@router.post("/provision")
async def start_event_provisioning(payload: ProvisionRequest):
    tenant_id = payload.tenant_id or settings.DEFAULT_TENANT_ID
    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "tenant_id": tenant_id,
        "raw_brief_text": payload.raw_brief_text,
        "planning_iteration": 0,
        "detected_conflicts": [],
        "executed_steps": []
    }

    # Execute up to HITL interrupt
    await provisioning_engine.ainvoke(initial_state, config=config)

    # Check state snapshot
    snapshot = provisioning_engine.get_state(config)
    interrupt_payload = None
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        interrupt_payload = snapshot.tasks[0].interrupts[0].value

    return {
        "thread_id": thread_id,
        "status": "INTERRUPTED" if interrupt_payload else "RUNNING",
        "hitl_payload": interrupt_payload
    }

@router.post("/brief/upload")
async def upload_event_brief(
    file: UploadFile = File(...),
    tenant_id: Optional[str] = Form(None)
):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    
    # Forward to provisioning engine
    return await start_event_provisioning(
        ProvisionRequest(tenant_id=tenant_id, raw_brief_text=text)
    )

@router.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = provisioning_engine.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    interrupt_payload = None
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        interrupt_payload = snapshot.tasks[0].interrupts[0].value

    return {
        "thread_id": thread_id,
        "next_nodes": list(snapshot.next),
        "values": snapshot.values,
        "is_interrupted": interrupt_payload is not None,
        "interrupt_payload": interrupt_payload
    }

@router.post("/threads/{thread_id}/resume")
async def resume_thread_execution(thread_id: str, payload: ResumeRequest):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = provisioning_engine.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    resumed_state = await provisioning_engine.ainvoke(
        Command(resume={"decision": payload.decision, "feedback": payload.feedback}),
        config=config
    )

    return {
        "thread_id": thread_id,
        "status": "COMPLETED" if resumed_state.get("execution_complete") else "RUNNING",
        "event_id": resumed_state.get("event_id"),
        "executed_steps": resumed_state.get("executed_steps", [])
    }

@router.get("/{event_id}/manifest")
async def get_event_manifest(event_id: str, db: AsyncSession = Depends(get_db)):
    manifest = await MCPService.get_event_manifest(db, event_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Event manifest not found.")
    return manifest

@router.post("/incidents/simulate")
async def simulate_live_incident(payload: IncidentSimulateRequest):
    tenant_id = payload.tenant_id or settings.DEFAULT_TENANT_ID
    thread_id = f"inc_thread_{uuid.uuid4().hex[:12]}"
    config = {"configurable": {"thread_id": thread_id}}

    incident_state = {
        "tenant_id": tenant_id,
        "event_id": payload.event_id,
        "session_id": payload.session_id,
        "incident_type": payload.incident_type,
        "telemetry_data": {"simulated": True}
    }

    await triage_engine.ainvoke(incident_state, config=config)
    snapshot = triage_engine.get_state(config)
    
    interrupt_payload = None
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        interrupt_payload = snapshot.tasks[0].interrupts[0].value

    return {
        "incident_thread_id": thread_id,
        "status": "INTERRUPTED",
        "options": interrupt_payload.get("options", []) if interrupt_payload else []
    }
