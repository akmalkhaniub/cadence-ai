# SPEC 3: Interface & Protocol Specifications (MCP + APIs)

**Product Name**: EventCrafter AI  
**Document Version**: 1.0.0  
**Status**: DRAFT FOR REVIEW  
**Scope**: Model Context Protocol (MCP) Server Schemas, WebSocket Real-Time Streaming Protocol, and FastAPI REST Gateway API  

---

## 1. Protocol Architecture Overview

The system standardizes all internal agent-to-platform communication on the **Model Context Protocol (MCP)**, while exposing modern **WebSockets** and **REST APIs** for client applications (Vue 3 frontend, core Laravel/PHP backend, and external microservices).

```
┌────────────────────────────────────────────────────────────────────────┐
│                   External Clients & Frontend                          │
│          (Vue 3 SPA, Mobile Apps, Laravel Core Backend)                │
└───────────────────▲────────────────────────────────▲───────────────────┘
                    │ REST (OpenAPI 3.1)             │ WebSocket Streaming
                    ▼                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Gateway Service                           │
│     • Authentication & Multi-Tenant Authorization                      │
│     • WebSocket Session Connection Pooling                             │
│     • LangGraph Invocation & Checkpoint Querying                       │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ Python MCP Client / In-Memory Transport
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     vFairs Core MCP Server                             │
│     • Transport: stdio / SSE (Server-Sent Events)                      │
│     • Protocol Standard: Model Context Protocol (MCP) 2024-11-05       │
│     • Implements: Tools, Resources, and Tool Audit Loggers             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Model Context Protocol (MCP) Server Specification

The MCP server acts as the authoritative database gatekeeper. Agents cannot issue raw SQL queries; they must discover and invoke MCP tools.

### 2.1 Server Metadata
- **Name**: `vfairs-event-operations-mcp`
- **Version**: `1.0.0`
- **Supported Capabilities**: `tools`, `resources`, `logging`

---

### 2.2 Complete MCP Tool Definitions

#### 1. `events.create_event`
* **Purpose**: Initializes a new top-level event entity.
* **Input Schema**:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string", "format": "uuid" },
    "title": { "type": "string", "minLength": 3, "maxLength": 255 },
    "slug": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "description": { "type": "string" },
    "format": { "type": "string", "enum": ["VIRTUAL", "HYBRID", "IN_PERSON"] },
    "timezone": { "type": "string", "example": "America/New_York" },
    "start_time": { "type": "string", "format": "date-time" },
    "end_time": { "type": "string", "format": "date-time" },
    "branding": {
      "type": "object",
      "properties": {
        "primary_color": { "type": "string", "pattern": "^#[0-9A-Fa-f]{6}$" },
        "logo_url": { "type": "string", "format": "uri" }
      }
    },
    "idempotency_key": { "type": "string", "format": "uuid" }
  },
  "required": ["tenant_id", "title", "slug", "format", "timezone", "start_time", "end_time", "idempotency_key"]
}
```
* **Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "status": { "type": "string" },
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["event_id", "status", "transaction_id"]
}
```

---

#### 2. `sessions.schedule_session`
* **Purpose**: Schedules a talk, panel, or workshop, assigning tracks, rooms, and speakers while verifying constraint non-collision.
* **Input Schema**:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string", "format": "uuid" },
    "event_id": { "type": "string", "format": "uuid" },
    "track_id": { "type": "string", "format": "uuid" },
    "room_id": { "type": "string", "format": "uuid" },
    "title": { "type": "string", "minLength": 3, "maxLength": 255 },
    "abstract": { "type": "string" },
    "format": { "type": "string", "enum": ["KEYNOTE", "PANEL", "WORKSHOP", "BREAKOUT", "LIGHTNING_TALK"] },
    "start_time": { "type": "string", "format": "date-time" },
    "end_time": { "type": "string", "format": "date-time" },
    "speaker_ids": {
      "type": "array",
      "items": { "type": "string", "format": "uuid" }
    },
    "prerecorded_asset_url": { "type": "string", "format": "uri" },
    "idempotency_key": { "type": "string", "format": "uuid" }
  },
  "required": ["tenant_id", "event_id", "title", "format", "start_time", "end_time", "idempotency_key"]
}
```
* **Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "session_id": { "type": "string", "format": "uuid" },
    "duration_minutes": { "type": "integer" },
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["session_id", "duration_minutes", "transaction_id"]
}
```

---

#### 3. `sessions.detect_conflicts` (Read-Only Validation Tool)
* **Purpose**: Allows the agent to simulate a proposed session time against existing schedules before committing.
* **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "room_id": { "type": "string", "format": "uuid" },
    "start_time": { "type": "string", "format": "date-time" },
    "end_time": { "type": "string", "format": "date-time" },
    "speaker_ids": {
      "type": "array",
      "items": { "type": "string", "format": "uuid" }
    }
  },
  "required": ["event_id", "start_time", "end_time"]
}
```
* **Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "has_conflict": { "type": "boolean" },
    "conflicts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "conflict_type": { "type": "string", "enum": ["ROOM_DOUBLE_BOOKING", "SPEAKER_COLLISION", "OUT_OF_BOUNDS"] },
          "conflicting_session_id": { "type": "string", "format": "uuid" },
          "conflicting_session_title": { "type": "string" },
          "overlap_start": { "type": "string", "format": "date-time" },
          "overlap_end": { "type": "string", "format": "date-time" }
        }
      }
    }
  },
  "required": ["has_conflict", "conflicts"]
}
```

---

#### 4. `booths.provision_booth`
* **Purpose**: Provisions an exhibitor booth, assigns 3D styling templates, attaches collateral, and links rep accounts.
* **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string", "format": "uuid" },
    "event_id": { "type": "string", "format": "uuid" },
    "sponsor_name": { "type": "string" },
    "tier": { "type": "string", "enum": ["TITLE", "PLATINUM", "GOLD", "SILVER", "BRONZE"] },
    "logo_url": { "type": "string", "format": "uri" },
    "booth_template": { "type": "string", "default": "standard_booth_v1" },
    "branding_assets": {
      "type": "object",
      "properties": {
        "banners": { "type": "array", "items": { "type": "string", "format": "uri" } },
        "brochure_urls": { "type": "array", "items": { "type": "string", "format": "uri" } }
      }
    },
    "rep_emails": { "type": "array", "items": { "type": "string", "format": "email" } },
    "idempotency_key": { "type": "string", "format": "uuid" }
  },
  "required": ["tenant_id", "event_id", "sponsor_name", "tier", "logo_url", "idempotency_key"]
}
```

---

#### 5. `notifications.broadcast_push` (Live Ops Crisis Broadcast)
* **Purpose**: Sends immediate real-time push alerts to attendees during live schedule shifts.
* **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string", "format": "uuid" },
    "event_id": { "type": "string", "format": "uuid" },
    "target_session_id": { "type": "string", "format": "uuid" },
    "urgency": { "type": "string", "enum": ["INFO", "WARNING", "CRITICAL"] },
    "title": { "type": "string", "maxLength": 100 },
    "body": { "type": "string", "maxLength": 300 },
    "action_route": { "type": "string" }
  },
  "required": ["tenant_id", "event_id", "urgency", "title", "body"]
}
```

---

#### 6. `audit.rollback_transaction`
* **Purpose**: Executes compensating inverse patches for a previous transaction.
* **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tenant_id": { "type": "string", "format": "uuid" },
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["tenant_id", "transaction_id"]
}
```

---

### 2.3 MCP Resources

Agents query these read-only URIs to load contextual platform state into their context window without burning tool calls.

| Resource URI | MIME Type | Description |
| :--- | :--- | :--- |
| `event://{event_id}/manifest` | `application/json` | Full nested JSON tree of tracks, rooms, sessions, speakers, and booths. |
| `event://{event_id}/schedule_matrix` | `application/json` | 2D temporal allocation grid (Time $\times$ Room) showing open and booked slots. |
| `event://{event_id}/live_telemetry` | `application/json` | Real-time stream statuses, current session time deltas, and backstage speaker check-ins. |

---

## 3. WebSocket Real-Time Streaming Protocol

### 3.1 Endpoint & Authentication
* **URL**: `ws://{host}/api/v1/events/{event_id}/agent-stream?token={jwt}`
* **Protocols**: `eventcrafter-agent-v1`

---

### 3.2 Message Payloads (Server $\rightarrow$ Client)

#### 1. `NODE_EXECUTION_STATE`
Emitted when the state machine enters or completes a node.
```json
{
  "type": "NODE_EXECUTION_STATE",
  "thread_id": "provisioning_123_456",
  "node_name": "planner_node",
  "status": "RUNNING", // "RUNNING" | "COMPLETED" | "FAILED"
  "step_index": 2,
  "timestamp": "2026-09-03T01:17:00.000Z"
}
```

#### 2. `LLM_TOKEN_STREAM`
Emitted during streaming generation for real-time terminal rendering.
```json
{
  "type": "LLM_TOKEN_STREAM",
  "thread_id": "provisioning_123_456",
  "node_name": "planner_node",
  "delta": "Decomposing track schedule: creating 3 morning sessions..."
}
```

#### 3. `HITL_INTERRUPT_REQUIRED` (Human-in-the-Loop Trigger)
Sent when the state machine reaches an `interrupt()`. Pauses execution and requests organizer input.
```json
{
  "type": "HITL_INTERRUPT_REQUIRED",
  "thread_id": "provisioning_123_456",
  "interrupt_type": "PROVISIONING_MANIFEST_REVIEW",
  "payload": {
    "summary": "Plan generated with 4 tracks, 14 sessions, and 6 sponsor booths.",
    "diff_manifest": {
      "tracks_to_create": 4,
      "sessions_to_schedule": 14,
      "speakers_to_assign": 12,
      "booths_to_provision": 6
    },
    "detected_conflicts": []
  },
  "allowed_actions": ["APPROVE", "REJECT", "MODIFY"],
  "expires_at": "2026-09-03T02:17:00.000Z"
}
```

---

### 3.3 Message Payloads (Client $\rightarrow$ Server)

#### 1. `HITL_INTERRUPT_RESPONSE` (Resume Execution)
Sent by the Vue 3 frontend when the organizer clicks Approve or submits feedback.
```json
{
  "type": "HITL_INTERRUPT_RESPONSE",
  "thread_id": "provisioning_123_456",
  "decision": "APPROVED", // "APPROVED" | "REJECTED"
  "rejection_feedback": null,
  "client_modifications": {}
}
```

---

## 4. FastAPI REST Gateway API Surface

| Method | Endpoint | Description | Auth Scope |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/events/provision` | Initiates an autonomous event provisioning job. Returns `thread_id`. | `events:write` |
| `POST` | `/api/v1/events/{event_id}/brief/upload` | Multipart file upload for PDF brief or speaker CSV. | `events:write` |
| `GET` | `/api/v1/events/{event_id}/threads/{thread_id}/state` | Fetches the full LangGraph state checkpoint. | `events:read` |
| `POST` | `/api/v1/events/{event_id}/threads/{thread_id}/resume` | REST fallback for submitting HITL approval/rejection. | `events:write` |
| `POST` | `/api/v1/events/{event_id}/incidents/simulate` | Triggers a synthetic live incident (speaker no-show) for testing. | `events:admin` |
| `GET` | `/api/v1/events/{event_id}/audit-log` | Retrieves transactional history and rollback receipts. | `events:read` |

---

## 5. Next Steps & Progression

With **SPEC 3 (Interface & Protocol Specifications)** established, we proceed to:
- **SPEC 4**: Safety, Guardrails & Reversibility Spec (Saga rollback engine, Pydantic guardrails, tenant isolation, and audit logging).
- **SPEC 5**: Evaluation & Quality Benchmark Harness (Synthetic benchmark datasets, drift metrics, scoring).
