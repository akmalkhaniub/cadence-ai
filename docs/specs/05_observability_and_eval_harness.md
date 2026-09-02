# SPEC 5: Observability, Evaluation & Testing Harness Specification

**Product Name**: EventCrafter AI  
**Document Version**: 1.0.0  
**Status**: DRAFT FOR REVIEW  
**Scope**: Synthetic Benchmark Datasets, Quantitative Evaluation Metrics, Telemetry & Tracing, CI/CD Regression Gates, and Performance SLAs  

---

## 1. Evaluation Philosophy for Autonomous Agent Systems

Traditional software is tested with deterministic unit tests; simple LLM chat applications are evaluated on subjective human vibes. Neither is sufficient for an autonomous agent platform that mutates multi-million-dollar event databases.

**EventCrafter AI** employs a **rigorous quantitative evaluation harness** that treats agent prompts, model versions, and state machine graphs as code subject to:
1. **Zero Tolerance for Tool Hallucinations**: Every tool parameter must be schema-valid and bound to verified database entities.
2. **Deterministic Regression Gates**: Every PR must pass against a standardized 25-scenario benchmark suite before merging.
3. **State Integrity Invariance**: Rollback tests must prove 100% database checksum parity before and after aborted runs.

---

## 2. The 25-Scenario Synthetic Benchmark Suite (`evals/datasets/`)

The evaluation harness evaluates agents across three rigorously categorized test suites:

```
┌────────────────────────────────────────────────────────────────────────┐
│               THE 25-SCENARIO SYNTHETIC BENCHMARK SUITE                │
├───────────────────┬───────┬────────────────────────────────────────────┤
│ Suite Category    │ Count │ Test Objectives                            │
├───────────────────┼───────┼────────────────────────────────────────────┤
│ 1. Standard Event │ 5     │ • Green-field generation from clean briefs │
│    Archetypes     │       │ • Multi-track virtual summits, hackathons, │
│                   │       │   and corporate hybrid all-hands           │
├───────────────────┼───────┼────────────────────────────────────────────┤
│ 2. Adversarial &  │ 10    │ • Direct temporal conflicts in input briefs│
│    Edge Cases     │       │ • Missing speaker emails & malformed CSVs  │
│                   │       │ • Room capacity overflows & invalid dates  │
│                   │       │ • Prompt injection embedded in PDF briefs  │
├───────────────────┼───────┼────────────────────────────────────────────┤
│ 3. Live Incident  │ 10    │ • Speaker no-show 15m prior to start       │
│    Triage         │       │ • 30m keynote overrun with cascade ripple  │
│                   │       │ • Live RTMP broadcast link breakdown       │
│                   │       │ • Dual concurrent session collapse         │
└───────────────────┴───────┴────────────────────────────────────────────┘
```

### 2.1 Representative Benchmark Scenarios

#### Scenario `BENCH-ADV-03`: Speaker Double-Booking in PDF Brief
- **Input**: Organizer uploads a PDF describing a 2-day conference where "Dr. Samantha Reed" is scheduled to deliver a Keynote on Stage A at 10:00 AM and simultaneously moderate a Panel in Breakout Room B at 10:30 AM.
- **Expected Agent Behavior**:
  - `intent_parser_node` extracts both sessions accurately.
  - `constraint_verifier_node` flags the temporal collision.
  - `planner_node` autonomously executes a corrective shift, re-allocating the panel to 1:30 PM.
  - Zero tool calls made with conflicting time intervals.

#### Scenario `BENCH-LIV-01`: Speaker No-Show Triage Under 300 Seconds
- **Trigger**: Backstage telemetry emits `SPEAKER_ABSENT_15M` for Session `uuid-992`.
- **Expected Agent Behavior**:
  - Graph B initializes in $< 200\text{ms}$.
  - Agent queries semantic vector index and identifies pre-recorded backup video with similarity score $> 0.85$.
  - Generates 3 prioritized remediation options and pauses at HITL gate within $3.0\text{s}$.
  - Does NOT broadcast push notifications until human approval token is received.

---

## 3. Quantitative Evaluation Metrics & Scoring Rubric

The evaluation pipeline scores agent runs across five mathematical metrics:

### 3.1 Metrics Mathematical Definitions

$$\begin{array}{|l|l|c|}
\hline
\textbf{Metric Name} & \textbf{Mathematical Formula / Definition} & \textbf{Target SLA} \\
\hline
\textbf{Task Success Rate (TSR)} & \frac{\text{Runs Reaching Valid "CONFIGURED" or "RESOLVED" State}}{\text{Total Runs Evaluated}} & \ge 95.0\% \\
\hline
\textbf{Tool Hallucination Rate (THR)} & \frac{\text{Invalid Tool Names} + \text{Failed Schema Invocations} + \text{Fabricated IDs}}{\text{Total Tool Calls Executed}} & \mathbf{0.00\%} \\
\hline
\textbf{Conflict Resolution Rate (CRR)} & \frac{\text{Detected and Resolved Inherent Conflicts}}{\text{Total Ground-Truth Conflicts in Brief}} & 100.0\% \\
\hline
\textbf{Rollback Parity Checksum (RPC)} & \frac{\text{Database Entities Matching Pre-Run State After LIFO Rollback}}{\text{Total Pre-Run Database Entities}} & 100.0\% \\
\hline
\textbf{Plan Completeness Score (PCS)} & \text{Recall of Ground Truth (Tracks, Sessions, Speakers, Booths)} & \ge 98.0\% \\
\hline
\end{array}$$

---

### 3.2 Performance & Resource Consumption SLAs

| Metric | Target SLA | Hard Ceiling |
| :--- | :--- | :--- |
| **Pre-Event Provisioning Duration** | $< 35\text{ seconds}$ | $60\text{ seconds}$ |
| **Live Incident Triage Response** | $< 2.5\text{ seconds}$ | $4.0\text{ seconds}$ |
| **Token Budget (Full Event Build)** | $< 90,000\text{ tokens}$ | $150,000\text{ tokens}$ |
| **Monetary Cost per Event Provisioning** | $<\$0.25\text{ USD}$ | $\$0.50\text{ USD}$ |
| **Monetary Cost per Live Triage** | $<\$0.02\text{ USD}$ | $\$0.05\text{ USD}$ |

---

## 4. Telemetry & Observability Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI & LangGraph Engine                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ OpenTelemetry Spans
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Observability & Tracing Hub                        │
│                     (LangSmith / Arize Phoenix)                        │
│                                                                        │
│   • Hierarchical Tracing: Run ──► Node ──► LLM Call ──► MCP Tool Call │
│   • Real-Time Token & Dollar Accumulator per Tenant                    │
│   • Latency Waterfall Analysis across Agent State Transitions          │
│   • Tool Parameter Drift & Failure Heatmaps                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Alerts & Metrics
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Prometheus & Grafana Alerting                    │
│   • Alert: Tool Hallucination Rate > 0%                                │
│   • Alert: Planning Latency p95 > 45s                                  │
│   • Alert: Live Incident Triage p99 > 4.0s                             │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Trace Metadata Schema
Every trace emitted to the observability platform carries rich structural tags:
```json
{
  "trace_id": "tr_9a8b7c6d5e",
  "tenant_id": "tenant_123",
  "event_id": "evt_456",
  "archetype": "HYBRID_DEV_CONFERENCE",
  "graph_type": "PROVISIONING_GRAPH_A",
  "model": "gemini-1.5-pro",
  "step_count": 14,
  "tokens": { "prompt": 45120, "completion": 6240, "total": 51360 },
  "cost_usd": 0.185,
  "has_conflicts_resolved": true,
  "hitl_interrupted": true,
  "hitl_duration_seconds": 42.1,
  "final_status": "SUCCESS"
}
```

---

## 5. Automated CI/CD Regression Pipeline

In the repository, evaluations run via `pytest` with custom assertions against real local PostgreSQL and MCP servers.

### 5.1 Pytest Evaluation Runner (`tests/evals/test_agent_benchmarks.py`)
```python
import pytest
from app.agents.graph import compile_provisioning_graph
from app.evals.metrics import calculate_plan_completeness, verify_no_hallucinations

@pytest.mark.asyncio
async def test_adversarial_schedule_conflict(test_db_pool, test_mcp_client):
    # 1. Load ground truth scenario
    scenario = load_benchmark_scenario("BENCH-ADV-03")
    
    # 2. Execute graph
    graph = compile_provisioning_graph(test_db_pool, test_mcp_client)
    final_state = await graph.ainvoke({
        "tenant_id": scenario["tenant_id"],
        "raw_brief_text": scenario["input_brief"],
        "uploaded_files": []
    })

    # 3. Assertions on quantitative metrics
    assert verify_no_hallucinations(final_state["messages"]) == True, "Tool hallucination detected!"
    
    pcs = calculate_plan_completeness(final_state["plan"], scenario["ground_truth"])
    assert pcs >= 0.98, f"Plan completeness score was {pcs}, expected >= 0.98"
    
    assert len(final_state["detected_conflicts"]) == 0, "Agent failed to resolve scheduling conflict!"
    assert final_state["verification_passed"] == True
```

### 5.2 Pull Request Regression Gate Rule
A PR cannot be merged if:
1. `Task Success Rate (TSR)` falls below $95\%$.
2. Any `Tool Hallucination` occurs (strict $0.00\%$ requirement).
3. The average cost per event build increases by more than $15\%$ against the baseline.

---

## 6. Complete Spec-Driven Development Hierarchy Summary

With **SPEC 5** completed, all six foundational specifications of **EventCrafter AI** are formal, coherent, and locked down:

```
┌────────────────────────────────────────────────────────────────────────┐
│                THE COMPLETE SPECIFICATION SUITE                        │
├────────┬───────────────────────────────────────────────────────────────┤
│ SPEC 0 │ Master PRD & Domain Taxonomy (Archetypes, Personas, Matrix)   │
│ SPEC 1 │ Domain Ontology & Entity Relational Models (Postgres, Vectors)│
│ SPEC 2 │ Multi-Agent Architecture & LangGraph Spec (Dual-Graphs, HITL) │
│ SPEC 3 │ Interface & Protocol Spec (MCP Tools/Resources, WebSockets)   │
│ SPEC 4 │ Safety, Guardrails & Reversibility Spec (Saga Rollbacks, RLS) │
│ SPEC 5 │ Observability, Evaluation & Testing Harness Spec (Benchmarks) │
└────────┴───────────────────────────────────────────────────────────────┘
```

The system is now completely specified from business requirements down to database foreign keys, MCP schemas, state machine reducers, and evaluation equations.
