# SPEC 0: Master Product Requirements Document (PRD) & Domain Taxonomy

**Product Name**: EventCrafter AI (Autonomous Event Operations & Provisioning Platform)  
**Document Version**: 1.0.0  
**Status**: DRAFT FOR REVIEW  
**Scope**: Pre-Event Provisioning, Real-Time Live Ops Incident Triage, Post-Event Analytics  

---

## 1. Executive Summary & Product Vision

Modern event management platforms (vFairs, Cvent, Bizzabo, Hopin) require event organizers to spend tens to hundreds of hours manually inputting schedules, allocating rooms, configuring sponsor booths, handling speaker assets, and managing ticketing tiers. When live events happen, human organizers are overwhelmed by real-time disruptions (speaker no-shows, sessions running overtime, stream outages).

**EventCrafter AI** is an autonomous, multi-agent event orchestration platform that:
1. **Plans & Provisions**: Converts unstructured event briefs, speaker spreadsheets, and sponsor contracts into fully configured virtual, hybrid, and in-person events in minutes.
2. **Triages Live Incidents**: Autonomously manages real-time disruptions during the event (speaker no-shows, room overruns, broadcast failures) via constraint-solving and cascading schedule adjustments.
3. **Synthesizes & Closes**: Automatically generates post-event executive debriefs, sponsor ROI dossiers, and session summaries from recorded media.

All mutations occur through a standardized **Model Context Protocol (MCP)** interface with strict **Human-in-the-Loop (HITL)** risk gating, deterministic rollback mechanisms (Saga pattern), and end-to-end auditability.

---

## 2. Event Archetypes & Core Personas

### 2.1 Supported Event Archetypes

The platform is engineered to support three primary event archetypes, each with distinct constraints:

| Archetype | Format | Key Distinct Constraints |
| :--- | :--- | :--- |
| **1. Multi-Day Virtual Trade Show & Summit** | 100% Virtual | Global multi-timezone handling (APAC/EMEA/AMER); sponsor tiers with 3D booth assets; concurrent keynote broadcasts; digital lead capture. |
| **2. Hybrid Developer Conference & Hackathon** | Hybrid (In-Person + Virtual) | Physical room capacity vs. unlimited virtual streams; hackathon milestone deadlines; team breakout rooms; physical badge check-in + RTMP stream linkage. |
| **3. Corporate Internal Kickoff / All-Hands** | In-Person or Hybrid | Strict Enterprise SSO / role-based access gating; confidential internal session watermarking; mandatory breakout session distribution; executive approval workflows. |

---

### 2.2 Core Personas

```
                     ┌─────────────────────────────────────────┐
                     │          Platform Personas              │
                     └────────────────────┬────────────────────┘
          ┌──────────────────┬────────────┴────────────┬──────────────────┐
          ▼                  ▼                         ▼                  ▼
┌──────────────────┐ ┌───────────────┐        ┌────────────────┐ ┌────────────────┐
│  Event Director  │ │ Track Speaker │        │ Sponsor / Rep  │ │    Attendee    │
│  • Orchestrator  │ │ • Bio / Deck  │        │ • Booth assets │ │ • Schedule     │
│  • Approver      │ │ • Check-in    │        │ • Lead export  │ │ • Networking   │
│  • Crisis Lead   │ │ • Q&A Lead    │        │ • Live chat    │ │ • Live Q&A     │
└──────────────────┘ └───────────────┘        └────────────────┘ └────────────────┘
```

1. **Event Director / Organizer**:
   - *Needs*: High-level intent execution ("Setup my 3-day AI conference"), visibility into agent actions, total control over destructive/public changes, instant incident resolution when things go wrong live.
2. **Speaker / Presenter**:
   - *Needs*: Frictionless asset upload (bios, slides), transparent calendar invites with automatic timezone shifts, immediate updates if session times move.
3. **Exhibitor / Sponsor Manager**:
   - *Needs*: Guaranteed contractual deliverables (booth sizing, banner slots, rep seats), real-time visitor alerts, qualified lead exports.
4. **Attendee**:
   - *Needs*: Clear personalized agenda ("My Schedule"), zero broken stream links, real-time push alerts when rooms change, contextual networking recommendations.
5. **System / Platform Admin**:
   - *Needs*: Tenant isolation, deterministic rollback logs, token cost tracking, zero unauthorized data leakages.

---

## 3. Comprehensive Feature Matrix (Pre, Live, Post)

Features are prioritized using **MoSCoW** (Must, Should, Could, Won't for initial release):

### 3.1 Pre-Event: Planning, Provisioning & Configuration

| Module | Feature ID | Feature Description | Priority | Agent Autonomy Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | `PRE-ING-01` | **Multimodal Ingestion**: Extract event parameters from PDF briefs, CSV/Excel speaker rosters, and raw natural language prompts. | **MUST** | Full Autonomous |
| | `PRE-ING-02` | **Brand & Asset Normalization**: Ingest logos, colors, and banner assets; validate aspect ratios, formats, and contrast standards. | **SHOULD** | Full Autonomous |
| **Scheduling** | `PRE-SCH-01` | **Multi-Track DAG Scheduler**: Sequence sessions across tracks while respecting hard dependencies (e.g., keynote first). | **MUST** | Full Autonomous |
| | `PRE-SCH-02` | **Physics & Constraint Engine**: Detect and resolve room capacity limits, speaker double-booking, and minimum buffer gaps. | **MUST** | Full Autonomous + HITL if unresolved |
| | `PRE-SCH-03` | **Timezone Matrix Generator**: Produce synchronized multi-timezone schedule matrices with automatic day boundary shifts. | **MUST** | Full Autonomous |
| **Booths** | `PRE-BTH-01` | **Sponsor Tier Allocator**: Generate booth layouts matching tier specs (Platinum/Gold/Silver) with brochure and video slots. | **MUST** | Full Autonomous |
| | `PRE-BTH-02` | **Rep Scheduling & Shifts**: Assign sponsor booth representatives to active event operating hours. | **SHOULD** | Full Autonomous |
| **Ticketing** | `PRE-TCK-01` | **Tier & Access Gating**: Configure ticket types (VIP, Early Bird, General, Hackathon Hacker) and link to session permissions. | **MUST** | Full Autonomous |
| | `PRE-TCK-02` | **Physical Badge Template Designer**: Auto-generate print-ready badge templates with QR code payload specifications. | **COULD** | Full Autonomous |
| **Broadcast** | `PRE-BRD-01` | **Stream Infrastructure Wiring**: Auto-allocate RTMP endpoints, WebRTC rooms, or meeting IDs per session with fallback streams. | **MUST** | Full Autonomous |
| **Review** | `PRE-REV-01` | **Interactive Diff & Manifest Review**: Visual green/red diff of entire event configuration with HITL approve/reject/modify gates. | **MUST** | Strict HITL Gate |

---

### 3.2 During-Event: Live Operations & Incident Triage

| Module | Feature ID | Feature Description | Priority | Agent Autonomy Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Triage** | `LIV-TRG-01` | **Speaker No-Show Detection & Resolution**: Auto-flag missing speaker 15m prior; propose swap with backup session or delay. | **MUST** | HITL Confirmation |
| | `LIV-TRG-02` | **Overrun & Cascade Delay Engine**: When a session runs 15m over, dynamically calculate ripple effect on subsequent sessions and breaks. | **MUST** | HITL Confirmation |
| | `LIV-TRG-03` | **Room Emergency Re-routing**: If physical room or virtual stream fails, migrate session to backup target and update all routes. | **MUST** | HITL Confirmation |
| **Comms** | `LIV-COM-01` | **Automated Crisis Broadcast**: Auto-draft and dispatch targeted push notifications, emails, and lobby banners to affected attendees. | **MUST** | HITL (Single Click) |
| **Engagement**| `LIV-ENG-01` | **AI Matchmaker & Networking**: Real-time vector-similarity pairing of attendees for 1:1 networking based on session attendance and profile. | **SHOULD** | Full Autonomous |
| | `LIV-ENG-02` | **Smart Q&A & Chat Moderation**: Deduplicate, categorize, and rank questions from live attendees for stage moderators. | **SHOULD** | Full Autonomous |

---

### 3.3 Post-Event: Analytics, Synthesis & Debriefs

| Module | Feature ID | Feature Description | Priority | Agent Autonomy Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Synthesis** | `PST-SYN-01` | **Multimodal Session Summarizer**: Process session recordings to produce executive summaries, key quotes, and timestamped agendas. | **MUST** | Full Autonomous |
| | `PST-SYN-02` | **Social Clip Highlight Identifier**: Pinpoint highest-engagement transcript segments for marketing video clipping. | **COULD** | Full Autonomous |
| **ROI** | `PST-ROI-01` | **Sponsor Lead Dossier Generator**: Generate branded PDF debriefs for exhibitors detailing booth dwell time, visits, and lead scores. | **MUST** | Full Autonomous |
| | `PST-ROI-02` | **Event Health & Drop-Off Analytics**: Comprehensive analysis of attendance retention curves, room utilization, and sentiment. | **SHOULD** | Full Autonomous |

---

## 4. End-to-End User Scenarios & Edge Cases

### Scenario A: Green-Field Multi-Day Hybrid Summit Setup
1. **User Action**: Organizer uploads `Summit_Brief_2026.pdf` (containing 20 speakers, 4 tracks, Gold/Silver sponsors) and enters: *"Build our 3-day hybrid conference. Keynote starts at 9:00 AM each day. No overlapping sessions for sponsors."*
2. **Agent Execution**:
   - `Parser Node` extracts raw entities into structured schema.
   - `Planner Node` computes DAG: Venue -> Tracks -> Rooms -> Sessions -> Speakers -> Booths.
   - `Verifier Node` flags 1 conflict: *"Speaker Dr. Aris is requested for Track 1 and Track 3 at the same time on Day 2."*
   - `Planner Node` autonomously resolves the conflict by moving Track 3 session to 2:00 PM.
   - Graph reaches `human_review_checkpoint`.
3. **HITL Interaction**:
   - Organizer sees complete interactive schedule grid and booth previews.
   - Organizer clicks **Approve & Commit**.
4. **Outcome**: All entities provisioned in vFairs database via MCP server with transactional audit receipts.

---

### Scenario B: Live Incident - Speaker No-Show with Cascading Delay
1. **Trigger**: 15 minutes before the 2:00 PM session *"Future of Agentic Systems"*, Speaker Sarah Connor has not checked in to the virtual backstage.
2. **Agent Triage**:
   - Agent triggers `LIV-TRG-01` (Speaker No-Show Policy).
   - Evaluates options:
     - *Option 1*: Swap with 4:00 PM pre-recorded session on similar track.
     - *Option 2*: Extend networking break by 30 mins and compress 4:30 PM panel.
     - *Option 3*: Announce cancellation and re-route attendees to parallel Track 2.
   - Scores Option 1 highest based on topic relevance and availability of pre-recorded media.
3. **HITL Urgent Notification**:
   - Urgent prompt sent to Event Director's dashboard:
     > **CRITICAL ALERT**: Speaker Sarah Connor has not checked in (Starts in 15 mins).  
     > **Recommended Action**: Swap with pre-recorded session *"Autonomous Tool Use"* (Asset Ready).  
     > [**Approve Swap & Notify Attendees**] | [**Delay 15m**] | [**Dismiss**]
4. **Resolution**: Director clicks **Approve**.
   - Agent calls MCP `sessions.update_session_media`.
   - Agent calls MCP `notifications.broadcast_push` notifying 450 registered attendees.
   - Dashboard timeline updates in real-time.

---

### Scenario C: Edge Cases & Failure Modes

| Edge Case | Failure Mode / Threat | Mitigation Strategy |
| :--- | :--- | :--- |
| **Circular Dependency in Plan** | Agent creates infinite loop (e.g., Session A requires Booth B, which requires Session A). | Topological sort verification in `Verifier Node`; cycle detection aborts plan with human clarification request. |
| **MCP Server Partial Failure** | Network drops after creating 8 out of 10 sessions. | **Saga Compensating Transactions**: The orchestrator triggers inverse rollback tools (`sessions.delete`) for all orphan sessions created in the failed batch. |
| **Hallucinated Tool Parameters** | Agent invents a room ID `room_9999` that does not exist in the database. | Pydantic validation on MCP server interface rejects the call with strict schema errors, triggering LangGraph self-correction node. |
| **Conflicting Human Overrides** | Human manually edits a session in the UI while the agent is midway through a multi-step batch update. | Optimistic concurrency control via `version_id` on all event entities. Conflicting versions trigger an immediate agent state reload. |

---

## 5. Non-Functional Requirements (NFRs)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        NON-FUNCTIONAL SLAs                             │
├───────────────────────┬────────────────────────────────────────────────┤
│ Metric                │ Specification & Target                         │
├───────────────────────┼────────────────────────────────────────────────┤
│ Planning Latency      │ < 30 seconds to parse and produce 50-item plan │
│ Live Triage Response  │ < 3 seconds from alert trigger to triage options│
│ Streaming Latency     │ < 250ms WebSocket latency for state emissions  │
│ Tool Idempotency      │ 100% of MCP write tools must accept a UUID     │
│                       │ idempotency key to prevent duplicate creation  │
│ Tenant Isolation      │ Strict logical row-level security per tenant_id│
│ Audit Trail           │ 100% of agent mutations logged with reversible │
│                       │ patch, LLM prompt tokens, and timestamp        │
└───────────────────────┴────────────────────────────────────────────────┘
```

---

## 6. Next Steps & Progression

With **SPEC 0 (PRD & Domain Taxonomy)** established, the development progression is:
- **SPEC 1**: Domain Ontology & Entity Relationship Spec (PostgreSQL schemas, state machines, vector embeddings).
- **SPEC 2**: Multi-Agent Architecture & LangGraph Spec (State schemas, node topologies, HITL interrupts, recovery cycles).
- **SPEC 3**: Interface & Protocol Spec (MCP Tools/Resources, WebSocket messages, REST contracts).
- **SPEC 4**: Safety, Guardrails & Reversibility Spec (Saga rollback engine, Pydantic guardrails, audit logging).
- **SPEC 5**: Evaluation & Quality Benchmark Harness (Synthetic benchmark datasets, drift metrics, scoring).
