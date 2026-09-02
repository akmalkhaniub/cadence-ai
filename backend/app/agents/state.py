from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages

def append_to_list(current: List[Any], new: List[Any]) -> List[Any]:
    return (current or []) + (new or [])

def merge_dict(current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    return {**(current or {}), **(new or {})}

class PlanStep(TypedDict):
    id: str
    phase: str                      # "INFRASTRUCTURE", "AGENDA", "BOOTHS"
    action: str                     # "create_track", "schedule_session", "provision_booth"
    target_entity: str
    payload: Dict[str, Any]
    status: str                     # "PENDING", "COMPLETED", "FAILED"

class ProvisioningState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], add_messages]
    tenant_id: str
    event_id: Optional[str]
    raw_brief_text: str
    
    # Decomposed Entities
    extracted_data: Dict[str, Any]
    plan: List[PlanStep]
    planning_iteration: int         # Prevents runaway loops (max 3)
    
    # Validation & Conflicts
    detected_conflicts: List[Dict[str, Any]]
    verification_passed: bool
    
    # Human-in-the-Loop Checkpoint
    diff_manifest: Annotated[Dict[str, Any], merge_dict]
    organizer_decision: Optional[str]    # "APPROVED" | "REJECTED"
    rejection_feedback: Optional[str]
    
    # Worker Execution & Output
    executed_steps: Annotated[List[str], append_to_list]
    execution_complete: bool

class IncidentOption(TypedDict):
    option_id: str
    title: str
    description: str
    action_type: str                # "SWAP_MEDIA", "CASCADE_SHIFT", "REROUTE"
    action_payload: Dict[str, Any]
    estimated_impact: str

class LiveIncidentState(TypedDict):
    tenant_id: str
    event_id: str
    session_id: str
    incident_type: str              # "SPEAKER_NO_SHOW", "OVERRUN", "STREAM_FAILURE"
    telemetry_data: Dict[str, Any]
    
    # Triage Analysis
    ranked_options: List[IncidentOption]
    selected_option_id: Optional[str]
    
    # Execution
    resolution_status: str
    executed_action: Optional[Dict[str, Any]]
