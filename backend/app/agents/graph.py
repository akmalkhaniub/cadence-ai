from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import ProvisioningState, LiveIncidentState
from app.agents.nodes.parser import parse_brief_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.verifier import verifier_node
from app.agents.nodes.hitl_gate import hitl_manifest_gate_node
from app.agents.nodes.workers import worker_dispatcher_node
from app.agents.nodes.triage import incident_intake_node, hitl_triage_gate_node, cascade_execution_node

def route_verifier_decision(state: ProvisioningState) -> str:
    """Cyclic routing: self-correct if collision exists and iteration < 3."""
    if not state.get("verification_passed", False) and state.get("planning_iteration", 0) < 3:
        return "planner"
    return "hitl_gate"

def route_hitl_decision(state: ProvisioningState) -> str:
    """Routes based on human organizer approval or rejection."""
    if state.get("organizer_decision") == "APPROVED":
        return "workers"
    return "planner"

def compile_provisioning_graph(checkpointer=None):
    """Builds Graph A: Pre-Event Provisioning Engine."""
    workflow = StateGraph(ProvisioningState)

    workflow.add_node("parser", parse_brief_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("hitl_gate", hitl_manifest_gate_node)
    workflow.add_node("workers", worker_dispatcher_node)

    workflow.add_edge(START, "parser")
    workflow.add_edge("parser", "planner")
    workflow.add_edge("planner", "verifier")

    workflow.add_conditional_edges(
        "verifier",
        route_verifier_decision,
        {
            "planner": "planner",
            "hitl_gate": "hitl_gate"
        }
    )

    workflow.add_conditional_edges(
        "hitl_gate",
        route_hitl_decision,
        {
            "workers": "workers",
            "planner": "planner"
        }
    )

    workflow.add_edge("workers", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)

def compile_triage_graph(checkpointer=None):
    """Builds Graph B: Live Ops Incident Triage Engine."""
    workflow = StateGraph(LiveIncidentState)

    workflow.add_node("intake", incident_intake_node)
    workflow.add_node("hitl_triage", hitl_triage_gate_node)
    workflow.add_node("execute", cascade_execution_node)

    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "hitl_triage")
    workflow.add_edge("hitl_triage", "execute")
    workflow.add_edge("execute", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)
