import uuid
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.agents.state import ProvisioningState, PlanStep

async def planner_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Decomposes extracted event data into a topologically ordered list of PlanSteps.
    Applies corrective offsets if conflicts were flagged in prior iteration.
    """
    extracted = state["extracted_data"]
    plan: List[PlanStep] = []
    
    # 1. Infrastructure Steps (Tracks & Rooms)
    for i, t in enumerate(extracted.get("tracks", [])):
        plan.append({
            "id": f"step_track_{i}",
            "phase": "INFRASTRUCTURE",
            "action": "create_track",
            "target_entity": "track",
            "payload": {
                "name": t["name"],
                "color_hex": t.get("color_hex", "#3B82F6"),
                "display_order": i
            },
            "status": "PENDING"
        })

    for j, r in enumerate(extracted.get("rooms", [])):
        plan.append({
            "id": f"step_room_{j}",
            "phase": "INFRASTRUCTURE",
            "action": "create_room",
            "target_entity": "room",
            "payload": {
                "name": r["name"],
                "physical_capacity": r.get("capacity", 200),
                "is_virtual": True
            },
            "status": "PENDING"
        })

    # 2. Agenda Steps (Sessions)
    # Check if there were detected conflicts or feedback to self-correct
    conflicts = state.get("detected_conflicts", [])
    shift_offset_minutes = 0
    if conflicts:
        shift_offset_minutes = 60 # Shift colliding session by 1 hour

    for k, s in enumerate(extracted.get("sessions", [])):
        start_dt = datetime.fromisoformat(s["start_time"])
        if k > 0 and shift_offset_minutes > 0:
            start_dt += timedelta(minutes=shift_offset_minutes)

        end_dt = start_dt + timedelta(minutes=s["duration_minutes"])

        plan.append({
            "id": f"step_session_{k}",
            "phase": "AGENDA",
            "action": "schedule_session",
            "target_entity": "session",
            "payload": {
                "title": s["title"],
                "track_name": s["track_name"],
                "room_name": s["room_name"],
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "speaker_name": s["speaker_name"],
                "speaker_email": s["speaker_email"],
                "duration_minutes": s["duration_minutes"]
            },
            "status": "PENDING"
        })

    # 3. Sponsor Booth Steps
    for m, sp in enumerate(extracted.get("sponsors", [])):
        plan.append({
            "id": f"step_booth_{m}",
            "phase": "BOOTHS",
            "action": "provision_booth",
            "target_entity": "booth",
            "payload": {
                "sponsor_name": sp["name"],
                "tier": sp["tier"],
                "logo_url": f"https://assets.cadence.ai/logos/{sp['name'].lower().replace(' ', '_')}.svg"
            },
            "status": "PENDING"
        })

    return {
        "plan": plan,
        "detected_conflicts": [] # Clear conflicts for verifier to re-evaluate
    }
