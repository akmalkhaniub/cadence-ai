# SPEC 1: Domain Ontology & Entity Relationship Specification

**Product Name**: EventCrafter AI  
**Document Version**: 1.0.0  
**Status**: DRAFT FOR REVIEW  
**Scope**: Relational Schemas (PostgreSQL), Vector Embeddings (pgvector), Constraint Invariants, Finite State Machines (FSMs), and Audit Journal  

---

## 1. Domain Ontology Overview

The domain model represents the complete operational lifecycle of virtual, hybrid, and in-person events. It enforces **strict multi-tenancy**, **temporal consistency**, **optimistic concurrency control**, and **full transaction reversibility**.

```
                           ┌──────────────────────────┐
                           │          Tenant          │
                           └────────────┬─────────────┘
                                        │ 1:N
                                        ▼
                           ┌──────────────────────────┐
                     ┌─────┤          Event           ├─────┐
                     │     └──────┬────────────┬──────┘     │
                     │ 1:N        │ 1:N        │ 1:N        │ 1:N
                     ▼            ▼            ▼            ▼
             ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐
             │   Track   │ │ Location/ │ │ Sponsor/  │ │ TicketTier │
             │           │ │   Room    │ │ Exhibitor │ │            │
             └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬──────┘
                   │             │             │ 1:1         │ 1:N
                   │ 1:N         │ 1:N         ▼             ▼
                   │       ┌─────┴─────┐ ┌───────────┐ ┌────────────┐
                   └──────►│  Session  │ │   Booth   │ │  Attendee  │
                           └─────┬─────┘ └───────────┘ └────────────┘
                                 │ M:N
                                 ▼
                           ┌───────────┐
                           │  Speaker  │
                           └───────────┘
```

---

## 2. PostgreSQL Relational Schema & DDL

### 2.1 Enums & Extensions
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

CREATE TYPE event_format AS ENUM ('VIRTUAL', 'HYBRID', 'IN_PERSON');
CREATE TYPE event_status AS ENUM ('DRAFT', 'CONFIGURED', 'PUBLISHED', 'LIVE', 'CONCLUDED', 'ARCHIVED');
CREATE TYPE session_format AS ENUM ('KEYNOTE', 'PANEL', 'WORKSHOP', 'BREAKOUT', 'LIGHTNING_TALK', 'NETWORKING');
CREATE TYPE session_status AS ENUM (
    'DRAFT',
    'SCHEDULED',
    'BACKSTAGE_READY',
    'LIVE',
    'OVERRUN',
    'COMPLETED',
    'CANCELLED',
    'RESCHEDULED'
);
CREATE TYPE speaker_role AS ENUM ('KEYNOTE_SPEAKER', 'PANELIST', 'MODERATOR', 'WORKSHOP_LEAD', 'MC');
CREATE TYPE sponsor_tier AS ENUM ('TITLE', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'COMMUNITY');
CREATE TYPE incident_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE incident_type AS ENUM ('SPEAKER_NO_SHOW', 'SESSION_OVERRUN', 'STREAM_FAILURE', 'ROOM_CAPACITY_BREACH');
CREATE TYPE incident_status AS ENUM ('DETECTED', 'ANALYZING', 'HITL_REVIEW', 'APPLIED', 'REVERTED', 'DISMISSED');
```

---

### 2.2 Core Relational Tables

#### 1. Tenants & Events
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    format event_format NOT NULL DEFAULT 'VIRTUAL',
    status event_status NOT NULL DEFAULT 'DRAFT',
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    branding JSONB NOT NULL DEFAULT '{}'::jsonb, -- { primary_color, logo_url, banner_url }
    version_id INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_event_dates CHECK (end_time > start_time),
    CONSTRAINT uq_tenant_event_slug UNIQUE (tenant_id, slug)
);
CREATE INDEX idx_events_tenant_status ON events(tenant_id, status);
```

#### 2. Tracks & Locations (Rooms / Streams)
```sql
CREATE TABLE tracks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    color_hex VARCHAR(7) DEFAULT '#3B82F6',
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_track_name UNIQUE (event_id, name)
);

CREATE TABLE rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    physical_capacity INT DEFAULT NULL, -- NULL for purely virtual rooms
    is_virtual BOOLEAN NOT NULL DEFAULT TRUE,
    stream_provider VARCHAR(50),        -- 'RTMP', 'ZOOM', 'WEBRTC', 'YOUTUBE'
    primary_stream_url TEXT,
    backup_stream_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_room_name UNIQUE (event_id, name)
);
```

#### 3. Speakers & Semantic Vectors
```sql
CREATE TABLE speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    company VARCHAR(255),
    bio TEXT,
    avatar_url TEXT,
    bio_embedding vector(1536), -- OpenAI / Vertex text-embedding-3-small
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_speaker_email UNIQUE (event_id, email)
);
CREATE INDEX idx_speakers_embedding ON speakers USING ivfflat (bio_embedding vector_cosine_ops) WITH (lists = 100);
```

#### 4. Sessions (with Strict PostgreSQL Exclusion Invariants)
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    track_id UUID REFERENCES tracks(id) ON DELETE SET NULL,
    room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    abstract TEXT,
    format session_format NOT NULL DEFAULT 'KEYNOTE',
    status session_status NOT NULL DEFAULT 'DRAFT',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_minutes INT GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (end_time - start_time))/60) STORED,
    schedule_interval tstzrange GENERATED ALWAYS AS (tstzrange(start_time, end_time, '[)')) STORED,
    max_attendees INT DEFAULT NULL,
    prerecorded_asset_url TEXT,         -- Fallback media for live no-show triage
    abstract_embedding vector(1536),
    version_id INT NOT NULL DEFAULT 1,  -- Optimistic concurrency control
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_session_times CHECK (end_time > start_time),
    
    -- INVARIANT: No two active sessions may occupy the same room at overlapping times
    CONSTRAINT no_room_overlap EXCLUDE USING gist (
        room_id WITH =,
        schedule_interval WITH &&
    ) WHERE (status NOT IN ('CANCELLED', 'DRAFT'))
);
CREATE INDEX idx_sessions_event_interval ON sessions USING gist (schedule_interval);
CREATE INDEX idx_sessions_abstract_embedding ON sessions USING ivfflat (abstract_embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE session_speakers (
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker_id UUID NOT NULL REFERENCES speakers(id) ON DELETE CASCADE,
    role speaker_role NOT NULL DEFAULT 'KEYNOTE_SPEAKER',
    checkin_time TIMESTAMPTZ DEFAULT NULL,
    PRIMARY KEY (session_id, speaker_id)
);
```

#### 5. Sponsors & Exhibitor Booths
```sql
CREATE TABLE sponsors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tier sponsor_tier NOT NULL DEFAULT 'SILVER',
    logo_url TEXT NOT NULL,
    website_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE booths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    sponsor_id UUID NOT NULL REFERENCES sponsors(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    booth_3d_template VARCHAR(50) DEFAULT 'standard_booth_v1',
    branding_assets JSONB NOT NULL DEFAULT '{}'::jsonb, -- { banners: [], colors: {}, brochure_urls: [] }
    rep_emails JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_sponsor_booth UNIQUE (sponsor_id)
);
```

#### 6. Ticketing, Registration & Attendee Matchmaking
```sql
CREATE TABLE ticket_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- 'VIP Pass', 'General Admission', 'Hackathon Hacker'
    price_cents INT NOT NULL DEFAULT 0,
    total_capacity INT NOT NULL,
    sold_count INT NOT NULL DEFAULT 0,
    allowed_tracks JSONB DEFAULT '["*"]'::jsonb, -- Access gating control
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE attendees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    ticket_tier_id UUID NOT NULL REFERENCES ticket_tiers(id),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255),
    company VARCHAR(255),
    interests_text TEXT,
    interests_embedding vector(1536), -- For real-time 1:1 networking matchmaking
    badge_qr_hash VARCHAR(64) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_event_attendee_email UNIQUE (event_id, email)
);
CREATE INDEX idx_attendee_embedding ON attendees USING ivfflat (interests_embedding vector_cosine_ops) WITH (lists = 100);
```

---

### 2.3 Live Incidents & Triage Journal
```sql
CREATE TABLE live_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    incident_type incident_type NOT NULL,
    severity incident_severity NOT NULL DEFAULT 'MEDIUM',
    status incident_status NOT NULL DEFAULT 'DETECTED',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details JSONB NOT NULL DEFAULT '{}'::jsonb, -- { minutes_late, affected_speaker_id, failure_log }
    proposed_remedy JSONB DEFAULT NULL,         -- { action: "SWAP_SESSION", target_session_id, time_shift_mins }
    operator_decision VARCHAR(50) DEFAULT NULL, -- 'APPROVED', 'REJECTED', 'MANUAL_OVERRIDE'
    resolved_at TIMESTAMPTZ DEFAULT NULL
);
CREATE INDEX idx_incidents_active ON live_incidents(event_id, status) WHERE status NOT IN ('APPLIED', 'DISMISSED');
```

---

### 2.4 Transaction Journal for Saga Compensating Rollbacks
```sql
CREATE TABLE agent_transaction_journal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_run_id VARCHAR(100) NOT NULL, -- LangGraph thread_id
    idempotency_key UUID NOT NULL UNIQUE,
    tool_name VARCHAR(100) NOT NULL,    -- e.g. "sessions.schedule_session"
    target_table VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    operation VARCHAR(20) NOT NULL,     -- 'INSERT', 'UPDATE', 'DELETE'
    forward_payload JSONB NOT NULL,     -- What was applied
    compensating_patch JSONB NOT NULL,  -- Exact reverse tool call and payload to undo action
    is_reverted BOOLEAN NOT NULL DEFAULT FALSE,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_journal_agent_run ON agent_transaction_journal(agent_run_id);
```

---

## 3. Finite State Machines (FSMs)

### 3.1 Session Lifecycle FSM
```
  [ DRAFT ] ──────────► [ SCHEDULED ] ──────────► [ BACKSTAGE_READY ]
     │                         │                          │
     │                         │                          ▼
     │                         │                     [ LIVE ]
     │                         │                        │  ▲
     │                         │     Overrun Detected   │  │ Delayed Resume
     │                         │     ────────────────►  ▼  │
     │                         │                   [ OVERRUN ]
     │                         ▼                        │
     └────────────────► [ CANCELLED ]                   ▼
                               ▲                  [ COMPLETED ]
                               │
                        [ RESCHEDULED ]
```

| Source State | Event Trigger | Guard Condition | Target State |
| :--- | :--- | :--- | :--- |
| `DRAFT` | `VERIFY_AND_SCHEDULE` | Room & Speaker constraints satisfied | `SCHEDULED` |
| `SCHEDULED` | `SPEAKER_CHECKIN` | Check-in <= 30m before `start_time` | `BACKSTAGE_READY` |
| `BACKSTAGE_READY` | `START_BROADCAST` | Current time >= `start_time` - 1m | `LIVE` |
| `LIVE` | `EXCEED_DURATION` | Current time > `end_time` + 5m | `OVERRUN` |
| `OVERRUN` | `TERMINATE_SESSION` | Stream ended | `COMPLETED` |
| `SCHEDULED` | `INCIDENT_NO_SHOW` | Speaker missing <= 10m before start | `RESCHEDULED` or `CANCELLED` |

---

### 3.2 Live Incident Triage FSM
```
  [ DETECTED ] ──► [ ANALYZING ] ──► [ HITL_REVIEW ] ──► [ APPLIED ]
        │                                  │
        ▼                                  ▼
   [ DISMISSED ]                     [ REVERTED ]
```
1. **`DETECTED`**: System health monitor or check-in monitor triggers incident (e.g., speaker not detected backstage).
2. **`ANALYZING`**: The Triage Sub-Agent queries schedule vectors, checks room physics, and evaluates replacement options.
3. **`HITL_REVIEW`**: Interrupt emitted to Event Director UI via WebSocket with ranked recommendations and diff view.
4. **`APPLIED`**: Director accepts; compensating patches and schedule shifts are executed via MCP server.
5. **`REVERTED`**: If an emergency shift causes downstream failure, the transaction journal rolls back the shift.

---

## 4. Constraint Invariants & Integrity Rules

1. **Room Temporal Non-Collision (`no_room_overlap`)**:
   - Enforced by PostgreSQL GiST exclusion index. Any attempt by an agent to double-book a room is rejected at the database level with a SQL error, ensuring zero race conditions.
2. **Speaker Temporal Non-Collision**:
   - Evaluated via database trigger and pre-tool verification:
   ```sql
   CREATE OR REPLACE FUNCTION verify_speaker_availability()
   RETURNS TRIGGER AS $$
   BEGIN
       IF EXISTS (
           SELECT 1
           FROM session_speakers ss
           JOIN sessions s ON ss.session_id = s.id
           WHERE ss.speaker_id = NEW.speaker_id
             AND s.id != NEW.session_id
             AND s.status NOT IN ('CANCELLED', 'DRAFT')
             AND s.schedule_interval && (SELECT schedule_interval FROM sessions WHERE id = NEW.session_id)
       ) THEN
           RAISE EXCEPTION 'Speaker % is already booked in an overlapping session.', NEW.speaker_id;
       END IF;
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;
   ```
3. **Event Date Boundary Containment**:
   - All session `start_time` and `end_time` must reside within `[events.start_time, events.end_time]`.
4. **Tenant Data Wall**:
   - Every single table possesses a non-nullable `tenant_id`. All foreign keys are strictly checked against the same `tenant_id` to guarantee tenant isolation.

---

## 5. Next Steps & Progression

With **SPEC 1 (Domain Ontology & Entity Relationship Spec)** defined, we proceed to:
- **SPEC 2**: Multi-Agent Architecture & LangGraph Spec (State schema, node graph topologies, HITL interrupt protocols, cyclic recovery loops).
- **SPEC 3**: Interface & Protocol Spec (MCP Tools/Resources, WebSocket messages, REST contracts).
- **SPEC 4**: Safety, Guardrails & Reversibility Spec (Saga rollback engine, Pydantic guardrails, audit logging).
- **SPEC 5**: Evaluation & Quality Benchmark Harness (Synthetic benchmark datasets, drift metrics, scoring).
