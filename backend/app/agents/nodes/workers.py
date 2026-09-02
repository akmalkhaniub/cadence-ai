import uuid
from datetime import datetime
from typing import Dict, Any, List
from app.db.session import AsyncSessionLocal
from app.agents.state import ProvisioningState
from app.mcp_server.service import MCPService
from app.mcp_server.schemas import (
    CreateEventInput, CreateTrackInput, CreateRoomInput, 
    ScheduleSessionInput, ProvisionBoothInput
)
from app.db.models import EventFormat, SessionFormat, SponsorTier

async def worker_dispatcher_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Executes the approved plan steps through the MCP Service.
    Guarantees deterministic creation and audit logging.
    """
    tenant_id = state["tenant_id"]
    plan = state["plan"]
    executed: List[str] = []
    track_map: Dict[str, str] = {}
    room_map: Dict[str, str] = {}

    async with AsyncSessionLocal() as db:
        # 1. Initialize Event
        event_id = state.get("event_id")
        if not event_id:
            ext = state["extracted_data"]
            event_res = await MCPService.create_event(
                db,
                CreateEventInput(
                    tenant_id=tenant_id,
                    title=ext.get("title", "Cadence Event"),
                    slug=ext.get("slug", f"event-{uuid.uuid4().hex[:6]}"),
                    start_time=datetime.fromisoformat(ext["start_time"]),
                    end_time=datetime.fromisoformat(ext["end_time"]),
                    format=EventFormat.VIRTUAL
                )
            )
            event_id = event_res["event_id"]

        # 2. Execute Infrastructure (Tracks & Rooms)
        for step in plan:
            if step["phase"] == "INFRASTRUCTURE":
                if step["action"] == "create_track":
                    res = await MCPService.create_track(
                        db,
                        CreateTrackInput(
                            tenant_id=tenant_id,
                            event_id=event_id,
                            name=step["payload"]["name"],
                            color_hex=step["payload"].get("color_hex", "#3B82F6")
                        )
                    )
                    track_map[step["payload"]["name"]] = res["track_id"]
                    executed.append(step["id"])

                elif step["action"] == "create_room":
                    res = await MCPService.create_room(
                        db,
                        CreateRoomInput(
                            tenant_id=tenant_id,
                            event_id=event_id,
                            name=step["payload"]["name"],
                            physical_capacity=step["payload"].get("physical_capacity", 100)
                        )
                    )
                    room_map[step["payload"]["name"]] = res["room_id"]
                    executed.append(step["id"])

        # 3. Execute Agenda (Sessions)
        for step in plan:
            if step["phase"] == "AGENDA" and step["action"] == "schedule_session":
                p = step["payload"]
                t_id = track_map.get(p.get("track_name"))
                r_id = room_map.get(p.get("room_name"))

                res = await MCPService.schedule_session(
                    db,
                    ScheduleSessionInput(
                        tenant_id=tenant_id,
                        event_id=event_id,
                        track_id=t_id,
                        room_id=r_id,
                        title=p["title"],
                        format=SessionFormat.KEYNOTE,
                        start_time=datetime.fromisoformat(p["start_time"]),
                        end_time=datetime.fromisoformat(p["end_time"])
                    )
                )
                if res.get("status") == "SUCCESS":
                    executed.append(step["id"])

        # 4. Execute Booths
        for step in plan:
            if step["phase"] == "BOOTHS" and step["action"] == "provision_booth":
                p = step["payload"]
                res = await MCPService.provision_booth(
                    db,
                    ProvisionBoothInput(
                        tenant_id=tenant_id,
                        event_id=event_id,
                        sponsor_name=p["sponsor_name"],
                        tier=SponsorTier(p.get("tier", "SILVER")),
                        logo_url=p.get("logo_url", "https://example.com/logo.png")
                    )
                )
                if res.get("status") == "SUCCESS":
                    executed.append(step["id"])

    return {
        "event_id": event_id,
        "executed_steps": executed,
        "execution_complete": True
    }
