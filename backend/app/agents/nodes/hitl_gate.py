from typing import Dict, Any
from langgraph.types import interrupt
from app.agents.state import ProvisioningState

async def hitl_manifest_gate_node(state: ProvisioningState) -> Dict[str, Any]:
    """
    Halts execution via LangGraph interrupt().
    Presents an interactive diff manifest to the human organizer for sign-off.
    """
    plan = state["plan"]
    tracks = [p for p in plan if p["action"] == "create_track"]
    rooms = [p for p in plan if p["action"] == "create_room"]
    sessions = [p for p in plan if p["action"] == "schedule_session"]
    booths = [p for p in plan if p["action"] == "provision_booth"]

    diff_manifest = {
        "summary": f"Plan validated: {len(tracks)} tracks, {len(rooms)} rooms, {len(sessions)} sessions, {len(booths)} booths.",
        "tracks_count": len(tracks),
        "rooms_count": len(rooms),
        "sessions_count": len(sessions),
        "booths_count": len(booths),
        "unresolved_conflicts": state.get("detected_conflicts", [])
    }

    # Yield control to human organizer
    user_response = interrupt({
        "type": "PROVISIONING_MANIFEST_APPROVAL",
        "diff_manifest": diff_manifest,
        "instructions": "Please review the proposed event manifest and approve or reject."
    })

    # Resumed with human response
    decision = user_response.get("decision", "APPROVED") if isinstance(user_response, dict) else "APPROVED"
    feedback = user_response.get("feedback") if isinstance(user_response, dict) else None

    return {
        "diff_manifest": diff_manifest,
        "organizer_decision": decision,
        "rejection_feedback": feedback
    }
