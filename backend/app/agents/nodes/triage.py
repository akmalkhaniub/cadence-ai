from typing import Dict, Any, List
from langgraph.types import interrupt
from app.agents.state import LiveIncidentState, IncidentOption
from app.db.session import AsyncSessionLocal
from app.mcp_server.service import MCPService

async def incident_intake_node(state: LiveIncidentState) -> Dict[str, Any]:
    """Ingests real-time alert and generates remediation options."""
    inc_type = state["incident_type"]
    options: List[IncidentOption] = []

    if inc_type == "SPEAKER_NO_SHOW":
        options = [
            {
                "option_id": "opt_swap_asset",
                "title": "Swap with Pre-Recorded Video Asset",
                "description": "Deploy backup recording 'Autonomous Tool Use' (Match: 89%, Asset Ready).",
                "action_type": "SWAP_MEDIA",
                "action_payload": {"asset_url": "https://assets.cadence.ai/backup/keynote_backup.mp4"},
                "estimated_impact": "Zero schedule delay to downstream tracks."
            },
            {
                "option_id": "opt_cascade_shift",
                "title": "Cascade Delay (+20 Minutes)",
                "description": "Shift session and subsequent track sessions forward by 20 minutes.",
                "action_type": "CASCADE_SHIFT",
                "action_payload": {"minutes": 20},
                "estimated_impact": "Shifts 3 subsequent sessions; reduces afternoon break."
            }
        ]

    return {"ranked_options": options}

async def hitl_triage_gate_node(state: LiveIncidentState) -> Dict[str, Any]:
    """Halts triage graph via interrupt() for single-click operator approval."""
    decision = interrupt({
        "type": "CRITICAL_LIVE_INCIDENT",
        "session_id": state["session_id"],
        "options": state["ranked_options"]
    })

    opt_id = decision.get("selected_option_id", "opt_swap_asset") if isinstance(decision, dict) else "opt_swap_asset"
    return {"selected_option_id": opt_id}

async def cascade_execution_node(state: LiveIncidentState) -> Dict[str, Any]:
    """Executes the chosen remediation option via FastMCP service."""
    selected_id = state.get("selected_option_id", "opt_swap_asset")
    chosen = next((o for o in state["ranked_options"] if o["option_id"] == selected_id), None)
    
    if not chosen:
        return {"resolution_status": "FAILED_NO_OPTION"}

    async with AsyncSessionLocal() as db:
        if chosen["action_type"] == "SWAP_MEDIA":
            asset_url = chosen["action_payload"]["asset_url"]
            res = await MCPService.update_session_media(db, state["session_id"], asset_url)
            return {
                "resolution_status": "RESOLVED",
                "executed_action": res
            }

    return {"resolution_status": "RESOLVED"}
