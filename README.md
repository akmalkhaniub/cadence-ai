# Cadence AI

### Autonomous Multi-Agent Event Operations & Provisioning Platform

> **Cadence AI** is an enterprise-grade autonomous event orchestration system that plans, provisions, and operates complex virtual, hybrid, and in-person conferences from raw briefs, speaker rosters, and sponsor contracts. Built on **LangGraph**, **Model Context Protocol (MCP)**, **FastAPI**, **PostgreSQL + pgvector**, **Langfuse**, and **Vue 3**.

---

## 📚 Complete Enterprise Specification Suite

This repository is governed by formal specifications located in [`docs/specs/`](docs/specs/):

### Core Architecture & Agent Mechanics
1. [**SPEC 0: Product Requirements Document & Domain Taxonomy**](docs/specs/00_prd_and_taxonomy.md)
   - 3 Event Archetypes: Multi-Day Virtual Summits, Hybrid Hackathons, and Corporate Internal All-Hands.
   - Full lifecycle feature matrix: Pre-Event Setup, Real-Time Live Ops Incident Triage, and Post-Event Analytics.
2. [**SPEC 1: Domain Ontology & Entity Relationship Specification**](docs/specs/01_domain_ontology_and_schema.md)
   - PostgreSQL DDL with GiST exclusion constraints (`no_room_overlap`) ensuring physical room non-collision.
   - `pgvector` semantic indexes for speaker matching, abstract clustering, and 1:1 attendee speed-networking.
   - Finite State Machines (FSMs) for Session & Incident Lifecycles.
3. [**SPEC 2: Multi-Agent Architecture & LangGraph Specification**](docs/specs/02_multi_agent_langgraph_architecture.md)
   - Dual-Graph System: Pre-Event Provisioning Graph (Planner-Worker-Verifier) and Live Ops Triage Graph.
   - Native LangGraph `interrupt()` checkpoints for Human-in-the-Loop diff manifests and single-click triage.
   - Persistent checkpointing with `PostgresSaver`.
4. [**SPEC 3: Interface & Protocol Specifications (MCP + APIs)**](docs/specs/03_mcp_and_api_protocols.md)
   - Formal Model Context Protocol (MCP) server contract exposing standard tools and resources.
   - Real-time bi-directional WebSocket streaming protocol for token streaming and interactive pauses.
   - FastAPI gateway REST endpoints.
5. [**SPEC 4: Safety, Guardrails & Reversibility Specification**](docs/specs/04_safety_guardrails_and_rollbacks.md)
   - Saga Pattern with compensating rollback patches (LIFO database restoration).
   - Deterministic UUIDv5 idempotency engine preventing duplicate creation on retries.
   - 3-Tier Guardrails (Injection Defense, Pydantic Structural Validation, Dynamic Risk Scoring).
6. [**SPEC 5: Observability, Evaluation & Testing Harness Specification**](docs/specs/05_observability_and_eval_harness.md)
   - Mathematical evaluation metrics with a **0.00% Tool Hallucination SLA**.
   - Self-hosted **Langfuse** integration for trace telemetry, token economics, and prompt management.

### Native Cloud Deployments & Infrastructure
7. [**SPEC 6A: Complete Native AWS Production Deployment Architecture**](docs/specs/06a_aws_deployment_architecture.md)
   - AWS ECS Fargate, Aurora PostgreSQL Serverless v2 with `pgvector`, CloudFront, ALB, Secrets Manager, and Terraform.
8. [**SPEC 6B: Complete Native GCP Production Deployment Architecture**](docs/specs/06b_gcp_deployment_architecture.md)
   - Google Cloud Run v2 (WebSockets enabled), Cloud SQL PostgreSQL 16 HA with `pgvector`, Cloud Armor WAF, and Workload Identity.
9. [**SPEC 6C: Complete Native Azure Production Deployment Architecture**](docs/specs/06c_azure_deployment_architecture.md)
   - Azure Container Apps (KEDA auto-scaling), PostgreSQL Flexible Server (Zone Redundant HA), Front Door, and Key Vault.
10. [**SPEC 6D: Multi-Cloud Federation & Cross-Cloud Disaster Recovery**](docs/specs/06d_multi_cloud_and_hybrid_architecture.md)
    - Cloudflare Global Anycast failover, cross-cloud asynchronous logical replication (`pglogical`), and cross-cloud DR SLAs (RTO < 3m, RPO < 5s).
11. [**SPEC 6: Cloud Deployment & DevOps Summary**](docs/specs/06_cloud_deployment_and_devops.md)
    - Multi-stage Dockerfiles with `uv` and zero-downtime rolling update strategies.

### Asynchronous Scale, Frontend & Verification
12. [**SPEC 7: Autonomous Evaluation Studio & Edge-Case Benchmark Suite**](docs/specs/07_evaluation_studio_and_benchmarks.md)
    - In-platform Evaluation Studio with Vue 3 UI (`/eval-studio`) and developer CLI.
    - 25-Scenario benchmark suite with Chaos injection simulating network drops, speaker dropouts, and stream failures.
13. [**SPEC 8: Asynchronous Task Queue, Background Workers & Redis Caching**](docs/specs/08_async_jobs_and_event_bus.md)
    - ARQ async worker pool, Redis 7 task queues, mass attendee push fan-out, and semantic embedding cache.
14. [**SPEC 9: Frontend Architecture, Vue 3 Component Hierarchy & UI/UX Flows**](docs/specs/09_frontend_architecture_and_ui_ux.md)
    - Vue 3 SPA architecture, Pinia real-time WebSocket store (`useAgentStore`), and wireframes for Provisioning Studio & Live Ops Command HUD.
15. [**Visual Blueprints & Cloud Architecture Diagrams**](docs/specs/architecture_diagrams.md)
    - Comprehensive Mermaid diagrams for End-to-End System, AWS Native, GCP Native, Azure Native, Multi-Cloud Federation, and Live Incident Sequence.

### Interview & Presentation Asset
16. [**Executive Architecture Presentation & Interview Playbook**](docs/interview_playbook.md)
    - 90-second executive pitch, 5-box whiteboard diagram, and defense against tough technical questions.

---

## 🛠 Tech Stack (2025–2026 Production Standard)

- **Language & Runtime**: Python 3.12+ managed with `uv`
- **Agent Orchestration**: LangGraph (v0.2+), LangChain Core
- **Tool Protocol**: Anthropic Model Context Protocol (`mcp` SDK / FastMCP)
- **Validation**: Pydantic v2 (Rust validation core)
- **API Gateway**: FastAPI + WebSockets (async ASGI via Uvicorn)
- **Async Workers**: ARQ (Async Redis Queue) + Redis 7
- **Database**: PostgreSQL 16 with `pgvector` and `btree_gist`
- **Cloud Infrastructure**: Terraform (Native AWS, Native GCP, Native Azure, and Multi-Cloud Federation)
- **Frontend**: Vue 3 (Vite, Composition API, `<script setup>`, Pinia, Tailwind CSS, Radix Vue)
- **Observability**: Self-Hosted Langfuse + OpenTelemetry
- **Containerization**: Multi-stage Dockerfiles with non-root security
