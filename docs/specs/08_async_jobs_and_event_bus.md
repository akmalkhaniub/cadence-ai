# SPEC 8: Asynchronous Task Queue, Background Workers & Redis Caching

**Product Name**: Cadence AI  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  
**Scope**: Async Background Tasks (ARQ / Celery), Redis 7 Infrastructure, Semantic Cache, and Event Bus  

---

## 1. Why Background Workers are Critical

In a production event operations platform, certain tasks cannot be performed synchronously within the FastAPI HTTP request cycle:
1. **Heavy Document Ingestion**: Ingesting 50-page PDF event briefs, speaker rosters (1,000-row CSVs), and slide decks with OCR takes 15–60 seconds.
2. **Mass Attendee Notification Fan-Out**: Broadcasting a live schedule shift alert to 15,000 registered attendees via Web Push, SMS, and Email requires asynchronous rate-limited workers.
3. **Comprehensive Benchmark Runs**: Running the 25-scenario Evaluation Suite takes several minutes and must run as a background batch job.

---

## 2. Background Architecture (ARQ + Redis 7)

We select **ARQ** (Async Redis Queue in Python) for high-performance, native asyncio background processing.

```
       FastAPI Gateway
             │
             ├──► Fast In-Memory State Machine (Immediate WS streaming)
             │
             └──► ARQ Job Dispatcher (enqueue_job)
                        │
                        ▼
                Redis 7 (Key-Value + Streams)
                 • Task Queues: [high, default, low]
                 • Semantic Vector Cache
                 • Idempotency Deduplication Keys
                        │
                        ▼
            ┌────────────────────────────────────────┐
            │   Cadence ARQ Worker Pool (x4 Replicas)│
            │                                        │
            │   • Worker 1: Document OCR & Embedding │
            │   • Worker 2: Mass Push Dispatcher     │
            │   • Worker 3: Evaluation Suite Runner  │
            │   • Worker 4: PDF Report Generator     │
            └────────────────────────────────────────┘
```

---

## 3. Queue Topology & Priorities

| Queue Name | Priority | Concurrency | Target Workloads |
| :--- | :--- | :--- | :--- |
| `queue:critical` | P0 (Highest) | 10 workers | Live Incident Push Broadcasts (SLA < 1.5s fan-out) |
| `queue:default` | P1 (Normal) | 20 workers | PDF Brief Ingestion, Schedule Vector Embeddings |
| `queue:batch` | P2 (Low/Batch) | 5 workers | 25-Scenario Evaluation Suite, Post-Event Sponsor PDF Dossiers |

---

## 4. Redis Semantic Cache & Rate Limiting

To reduce LLM costs and database roundtrips:
1. **Semantic Embedding Cache**:
   - Stores computed `text-embedding-3-small` vectors keyed by `sha256(text)`.
   - Hit rate reduces external embedding API calls by ~40% during speaker bio deduplication.
2. **Token Bucket Rate Limiting**:
   - Enforces per-tenant rate limits (e.g. max 100 agent runs per hour, max 500 WebSocket messages per minute).
   - Implemented via atomic Redis Lua scripts to prevent distributed race conditions.
