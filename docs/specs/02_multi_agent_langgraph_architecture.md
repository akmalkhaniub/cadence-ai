# SPEC 2: Multi-Agent Architecture & LangGraph Specification

**Product Name**: EventCrafter AI  
**Document Version**: 1.0.0  
**Status**: DRAFT FOR REVIEW  
**Scope**: LangGraph Topologies, State Schemas, Sub-Agent Workers, HITL Breakpoint Protocols, Cyclic Recovery Loops, and Checkpointing  

---

## 1. Architectural Philosophy: Why LangGraph?

Traditional single-turn LLM chains and naive multi-agent frameworks (CrewAI, vanilla AutoGen) suffer from three fatal flaws when applied to mission-critical event management:
1. **Lack of Deterministic State Persistence**: If a 45-step event provisioning sequence fails at step 42, naive chains lose all progress or cannot resume safely.
2. **Inability to do Real Human-in-the-Loop Interrupts**: Enterprise organizers refuse to give agents unconstrained write access to publish live events, send 10,000 attendee invitations, or charge credit cards without review.
3. **Fragile Cyclic Recovery**: Real constraint resolution (e.g., room/speaker conflicts) requires cyclic looping (Plan $\rightarrow$ Verify $\rightarrow$ Re-Plan) with explicit recursion limits and memory retention.

**LangGraph** solves this natively via **directed cyclic state graphs**, **first-class `interrupt()` mechanisms**, and **PostgreSQL checkpoint persistence (`PostgresSaver`)**.

---

## 2. Dual-Graph System Topology

The platform operates two distinct, specialized LangGraph state machines:

```
┌────────────────────────────────────────────────────────────────────────┐
│            GRAPH A: Pre-Event Provisioning & Setup Graph               │
│                                                                        │
│   [ Ingestion / Brief ]                                                │
│             │                                                          │
│             ▼                                                          │
│   [ Intent Parser Node ]                                               │
│             │                                                          │
│             ▼                                                          │
│   [ Planner Node ] ◄────────────────────────┐ (Constraint Violation)   │
│             │                               │ (Max 3 retries)          │
│             ▼                               │                          │
│   [ Constraint Verifier Node ] ─────────────┘                          │
│             │ (Pass)                                                   │
│             ▼                                                          │
│   [ HITL Manifest Gate ] ──► (interrupt: Wait for Organizer Approval)  │
│             │ (Approved)                                               │
│             ▼                                                          │
│   [ Worker Dispatcher ]                                                │
│     ┌───────┼───────┐                                                  │
│     ▼       ▼       ▼                                                  │
│  [Agenda] [Booth] [Ticket]                                             │
│     └───────┼───────┘                                                  │
│             ▼                                                          │
│   [ Transaction Finalizer & Audit Node ] ──► (Done)                    │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│             GRAPH B: Live Ops Incident Triage Graph                    │
│                                                                        │
│   [ Live Alert / Telemetry Webhook ] (e.g. Speaker No-Show 15m prior)  │
│             │                                                          │
│             ▼                                                          │
│   [ Incident Ingestion & Context Node ]                                │
│             │                                                          │
│             ▼                                                          │
│   [ Triage Options Generator ] (Vector Search for Backup / Ripple Sim) │
│             │                                                          │
│             ▼                                                          │
│   [ HITL Urgent Gate ] ────► (interrupt: 3 Actionable Options to UI)   │
│             │ (Option Selected)                                        │
│             ▼                                                          │
│   [ Cascade Execution Node ] (MCP Update Session + Broadcast Push)     │
│             │                                                          │
│             ▼                                                          │
│   [ Impact Verification & Log Node ] ──► (Done)                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Graph A: Pre-Event Provisioning State Machine

### 3.1 State Definition & Reducers
```python
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages

def append_to_list(current: List[Any], new: List[Any]) -> List[Any]:
    return current + new

def merge_diff(current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    return {**current, **new}

class PlanStep(TypedDict):
    id: str
    phase: str                      # "INFRASTRUCTURE", "AGENDA", "BOOTHS", "TICKETS"
    action: str                     # "create_track", "schedule_session", "provision_booth"
    target_entity: str
    payload: Dict[str, Any]
    mcp_tool: str
    status: str                     # "PENDING", "EXECUTING", "COMPLETED", "FAILED"
    reversible: bool

class ProvisioningState(TypedDict):
    # Core Context
    messages: Annotated[List[Dict[str, Any]], add_messages]
    tenant_id: str
    event_id: Optional[str]
    raw_brief_text: str
    uploaded_files: List[Dict[str, str]] # [{ "filename": "speakers.csv", "s3_url": "..." }]
    
    # Planning & Decomposition
    extracted_entities: Dict[str, Any]
    plan: List[PlanStep]
    planning_iteration: int         # Prevents infinite loops (max 3)
    
    # Verification & Conflicts
    detected_conflicts: List[Dict[str, Any]]
    verification_passed: bool
    
    # Human-in-the-loop Gate
    diff_manifest: Annotated[Dict[str, Any], merge_diff]
    organizer_decision: Optional[str]    # "APPROVED", "REJECTED", "MODIFIED"
    rejection_feedback: Optional[str]
    
    # Worker Execution & Audit
    executed_steps: Annotated[List[str], append_to_list]
    transaction_ids: Annotated[List[str], append_to_list]
    budget_tokens_used: int
```

---

### 3.2 Graph A Node Logic

#### Node 1: `intent_parser_node`
- **Role**: Parses unstructured inputs (brief text, CSV URLs) into structured Pydantic domain models:
  - Event title, dates, timezone, format (Virtual/Hybrid/In-Person).
  - List of proposed tracks and rooms.
  - List of speakers with titles and tentative topics.
  - List of sponsors and tiers.
- **Model**: Fast model with structured outputs (`response_format=ParsedEventBrief`).

#### Node 2: `planner_node`
- **Role**: Decomposes the structured brief into an ordered list of `PlanStep` items:
  1. `INFRASTRUCTURE`: Create tracks, register rooms, establish stream endpoints.
  2. `AGENDA`: Schedule keynote sessions, schedule breakout sessions, map speakers to sessions.
  3. `BOOTHS`: Provision exhibitor booths, link sponsor tiers, assign reps.
  4. `TICKETING`: Create ticket tiers, bind track access rules.
- **Constraint**: Every step must bind to a specific MCP tool call.

#### Node 3: `constraint_verifier_node`
- **Role**: Deterministic verification (Python code, not LLM):
  - Check 1: Room temporal collisions ($Interval_A \cap Interval_B \neq \emptyset$ in same room).
  - Check 2: Speaker multi-session collisions.
  - Check 3: Missing assets (e.g., a speaker assigned to a keynote has no email/bio).
  - Check 4: Boundary check (all sessions within event `[start_time, end_time]`).
- **Conditional Edge**:
  - If `detected_conflicts` is non-empty AND `planning_iteration < 3`: Route back to `planner_node` with explicit conflict feedback string.
  - If `detected_conflicts` is non-empty AND `planning_iteration >= 3`: Route to `hitl_manifest_gate` with flagged unresolvable conflicts for human intervention.
  - If `detected_conflicts` is empty: Route to `hitl_manifest_gate`.

#### Node 4: `hitl_manifest_gate` (The Approval Checkpoint)
- **Role**: Generates a consolidated JSON diff manifest comparing the current database state with the proposed plan.
- **LangGraph Implementation**:
  ```python
  def hitl_manifest_gate(state: ProvisioningState):
      manifest = generate_diff_manifest(state["plan"])
      # HALT EXECUTION: Wait for human input from the frontend
      user_response = interrupt({
          "type": "PROVISIONING_APPROVAL_REQUIRED",
          "event_id": state["event_id"],
          "diff_manifest": manifest,
          "unresolved_conflicts": state["detected_conflicts"]
      })
      
      # Upon resumption with user feedback:
      return {
          "organizer_decision": user_response.get("decision"), # "APPROVED" or "REJECTED"
          "rejection_feedback": user_response.get("feedback")
      }
  ```
- **Conditional Edge**:
  - If `organizer_decision == "APPROVED"`: Route to `subagent_dispatcher`.
  - If `organizer_decision == "REJECTED"`: Route back to `planner_node` incorporating `rejection_feedback`.

#### Node 5: `subagent_dispatcher` & Parallel Worker Nodes
Once approved, the dispatcher fans out execution to specialized worker sub-agents:
- **`agenda_worker`**: Calls MCP `tracks.create`, `sessions.schedule_session`, `speakers.assign`.
- **`booth_worker`**: Calls MCP `sponsors.create`, `booths.provision_booth`, `booths.attach_assets`.
- **`ticketing_worker`**: Calls MCP `tickets.create_tier`, `tickets.set_access_rules`.
- Each worker executes its steps using transactional idempotency keys (`UUIDv5(event_id, step_id)`).

#### Node 6: `transaction_finalizer_node`
- Verifies that all `executed_steps` succeeded.
- Emits a final audit receipt and transitions `events.status` from `DRAFT` to `CONFIGURED`.

---

## 4. Graph B: Live Ops Incident Triage State Machine

### 4.1 Live State Schema
```python
class IncidentOption(TypedDict):
    option_id: str
    title: str
    description: str
    actions: List[Dict[str, Any]] # Pre-packaged MCP tool payloads
    estimated_impact: str         # "Affects 450 attendees across Track 1 & 2"
    confidence_score: float       # 0.0 - 1.0

class LiveIncidentState(TypedDict):
    tenant_id: str
    event_id: str
    session_id: str
    incident_type: str            # "SPEAKER_NO_SHOW", "OVERRUN", "STREAM_FAILURE"
    minutes_until_start: int
    raw_telemetry: Dict[str, Any]
    
    # Analysis & Solutions
    impacted_attendee_count: int
    ranked_options: List[IncidentOption]
    selected_option_id: Optional[str]
    operator_comment: Optional[str]
    
    # Execution
    executed_resolution: Dict[str, Any]
    broadcast_message_sent: bool
```

---

### 4.2 Graph B Node Logic

#### Node 1: `incident_intake_node`
- Triggered via webhook or polling heartbeat (e.g., speaker has not hit the WebRTC backstage check-in 15m prior to start).
- Pulls live session metadata, speaker contact info, and current attendee count.

#### Node 2: `triage_options_generator`
- **Algorithmic Evaluation**:
  1. **Option A (Instant Swap)**: Searches `sessions` table for pre-recorded backup sessions or talks by present speakers with similar embeddings (`vector_cosine_ops` on `abstract_embedding`).
  2. **Option B (Cascade Delay)**: Calculates the time-shift equation:
     $$\text{Shift}(S_{n \dots m}) = \text{CurrentTime} + \Delta t$$
     Checks if shifting the current session pushes downstream sessions past the hard boundary (e.g. venue closing or scheduled keynote).
  3. **Option C (Clean Cancellation & Reroute)**: Cancels current session and drafts dynamic notifications recommending parallel tracks to registered attendees.
- Generates 3 strictly validated `IncidentOption` structs.

#### Node 3: `hitl_triage_gate`
- Fast interrupt emitted over WebSocket to Event Director:
  ```python
  def hitl_triage_gate(state: LiveIncidentState):
      decision = interrupt({
          "type": "CRITICAL_LIVE_INCIDENT",
          "severity": "CRITICAL",
          "session_id": state["session_id"],
          "options": state["ranked_options"],
          "timeout_seconds": 300 # 5 min default fallback
      })
      return {"selected_option_id": decision["option_id"]}
  ```

#### Node 4: `cascade_execution_node`
- Applies the selected option through the MCP server:
  - Updates the session record (`sessions.update_session`).
  - Calls `notifications.broadcast_push` with localized text.
  - Updates WebSocket timeline channel for all live attendees.

---

## 5. Checkpointing, Persistence & State Recovery

### 5.1 Storage Backend (`PostgresSaver`)
All graph state is persisted using LangGraph's PostgreSQL checkpointer.
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def get_checkpointer(connection_pool):
    checkpointer = AsyncPostgresSaver(connection_pool)
    await checkpointer.setup()
    return checkpointer
```

### 5.2 Thread Key Semantics
To guarantee isolation between concurrent planning sessions and live incidents:
- Pre-event provisioning thread:  
  `thread_id = f"provisioning_{tenant_id}_{event_id}"`
- Live triage thread:  
  `thread_id = f"incident_{tenant_id}_{event_id}_{session_id}_{timestamp}"`

---

## 6. Loop Limits, Cost Guards & Self-Healing

| Guard | Mechanism | Failure Action |
| :--- | :--- | :--- |
| **Max Planning Loops** | `planning_iteration` counter in state | If $> 3$, abort autonomous cycle and escalate to human with diagnostic trace. |
| **Recursion Limit** | LangGraph `config={"recursion_limit": 50}` | Prevents rogue node executions from runaway API loops. |
| **Token Cost Guard** | Custom LangGraph step counter tracking cumulative input/output tokens | If cumulative tokens exceed 150k for a single event setup, halt and alert admin. |
| **Schema Rejection Self-Healing** | If an MCP tool returns a Pydantic schema validation error, the error message is fed back into the worker node's message history to self-correct the payload on the next step. |

---

## 7. Next Steps & Progression

With **SPEC 2 (Multi-Agent Architecture & LangGraph Spec)** defined, we proceed to:
- **SPEC 3**: Interface & Protocol Spec (Detailed JSONSchemas for all MCP Tools/Resources, WebSocket Streaming Protocols, and REST APIs).
- **SPEC 4**: Safety, Guardrails & Reversibility Spec (Saga rollback engine, Pydantic guardrails, audit logging).
- **SPEC 5**: Evaluation & Quality Benchmark Harness (Synthetic benchmark datasets, drift metrics, scoring).
