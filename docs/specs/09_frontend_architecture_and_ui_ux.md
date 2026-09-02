# SPEC 9: Frontend Architecture, Vue 3 Component Hierarchy & UI/UX Flows

**Product Name**: Cadence AI  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  
**Scope**: Vue 3 SPA Architecture, Pinia Reactive Stores, WebSocket Connection Manager, and Component Hierarchy  

---

## 1. Frontend Technology Foundation

- **Framework**: **Vue 3** (`<script setup>`, Composition API)
- **Build Tool**: **Vite 5+** (instant HMR and optimized production bundling)
- **State Management**: **Pinia 2+** (modular, type-safe stores)
- **Styling**: **Tailwind CSS 3/4** + **Radix Vue / shadcn-vue** (accessible unstyled UI primitives)
- **Graph & Telemetry Rendering**: `@vue-flow/core` (interactive agent node DAG visualizer) and `Chart.js` / `ApexCharts` (latency waterfalls and benchmark metrics)

---

## 2. Directory Structure (`frontend/src/`)

```
frontend/src/
├── assets/                     # Global styles, Tailwind base, SVGs
├── components/
│   ├── agent/
│   │   ├── AgentTerminal.vue   # Real-time token streaming terminal
│   │   ├── GraphFlow.vue       # Interactive visual node graph (@vue-flow)
│   │   ├── ApprovalDiffModal.vue # HITL green/red manifest diff review
│   │   └── StepProgress.vue    # Linear execution breadcrumb
│   ├── live_ops/
│   │   ├── IncidentAlertHUD.vue # Critical live alert banner
│   │   ├── TriageActionCard.vue # Single-click remediation option selector
│   │   └── LiveTimeline.vue    # Dynamic schedule matrix with overrun flags
│   ├── evals/
│   │   ├── ScorecardKPIs.vue   # TSR, THR (0.00%), Rollback Parity metrics
│   │   ├── ScenarioRunner.vue  # 25-scenario launcher and progress bar
│   │   └── LatencyWaterfall.vue# OpenTelemetry span duration chart
│   └── common/
│       ├── BaseButton.vue
│       ├── BaseModal.vue
│       └── StatusBadge.vue
├── composables/
│   ├── useWebSocketStream.js   # Reconnecting WebSocket manager with backoff
│   └── useDiffFormatter.js     # JSON diff generator for approval gates
├── stores/
│   ├── agentStore.js           # Active thread, execution status, token buffer
│   ├── eventStore.js           # Event manifest, tracks, rooms, sessions
│   └── evalStore.js            # Benchmark suites, scores, historical runs
├── views/
│   ├── ProvisioningStudio.vue  # Ingestion brief upload & autonomous setup
│   ├── LiveOpsCommand.vue      # Real-time incident monitoring HUD
│   └── EvaluationStudio.vue    # Benchmark and chaos testing dashboard
├── router/
│   └── index.js                # Vue Router definitions
├── App.vue
└── main.js
```

---

## 3. Real-Time Pinia Store: `agentStore.js`

```javascript
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAgentStore = defineStore('agent', () => {
  const isConnected = ref(false);
  const activeThreadId = ref(null);
  const currentNode = ref(null);
  const executionStatus = ref('IDLE'); // 'IDLE' | 'RUNNING' | 'INTERRUPTED' | 'COMPLETED'
  const tokenStreamBuffer = ref('');
  const hitlPayload = ref(null);

  let socket = null;

  function connect(eventId, token) {
    const wsUrl = `wss://${window.location.host}/api/v1/events/${eventId}/agent-stream?token=${token}`;
    socket = new WebSocket(wsUrl);

    socket.onopen = () => { isConnected.value = true; };
    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    };
    socket.onclose = () => { isConnected.value = false; };
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case 'NODE_EXECUTION_STATE':
        currentNode.value = msg.node_name;
        executionStatus.value = msg.status;
        break;
      case 'LLM_TOKEN_STREAM':
        tokenStreamBuffer.value += msg.delta;
        break;
      case 'HITL_INTERRUPT_REQUIRED':
        executionStatus.value = 'INTERRUPTED';
        hitlPayload.value = msg.payload;
        break;
      case 'RUN_COMPLETED':
        executionStatus.value = 'COMPLETED';
        break;
    }
  }

  function submitApproval(decision, feedback = null) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'HITL_INTERRUPT_RESPONSE',
        thread_id: activeThreadId.value,
        decision,
        rejection_feedback: feedback
      }));
      hitlPayload.value = null;
      executionStatus.value = 'RUNNING';
    }
  }

  return {
    isConnected,
    activeThreadId,
    currentNode,
    executionStatus,
    tokenStreamBuffer,
    hitlPayload,
    connect,
    submitApproval
  };
});
```

---

## 4. Key UI Flows & Wireframes

### 4.1 Flow 1: Provisioning Studio (Pre-Event Setup)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ CADENCE AI | Provisioning Studio                         [Tenant: TechCorp] [●] │
├───────────────────────────────────────┬─────────────────────────────────────────┤
│ 1. Event Brief Ingestion              │ 2. Autonomous Agent Execution           │
│                                       │                                         │
│ [Drag & drop PDF / CSV brief here]    │ Node Status: [planner_node] RUNNING     │
│ - Summit_Brief_2026.pdf (1.2MB)       │ ┌─────────────────────────────────────┐ │
│                                       │ │ > Parsing tracks and keynote times  │ │
│ Constraints Input:                    │ │ > Flagged room conflict in Room 2   │ │
│ "Ensure 15m buffers between sessions" │ │ > Rerouting panel to Room 4...      │ │
│                                       │ └─────────────────────────────────────┘ │
│ [ Generate Event Architecture ]       │                                         │
├───────────────────────────────────────┴─────────────────────────────────────────┤
│ [MODAL: HITL Approval Gate - Diff Review]                                       │
│ + Proposed: 4 Tracks, 14 Sessions, 6 Sponsor Booths                            │
│ + Conflicts Resolved: 1 (Dr. Reed double-booking moved to 1:30 PM)              │
│ [ Approve & Commit via MCP ]   [ Reject with Feedback ]   [ Manual Edit ]       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Flow 2: Live Ops Command HUD (Incident Triage)
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ CADENCE AI | Live Ops Command HUD                 [Event: AI Summit 2026] [LIVE]│
├─────────────────────────────────────────────────────────────────────────────────┤
│ [!] CRITICAL LIVE ALERT (13:45:10 UTC)                                          │
│ Session 402: "Future of Agentic Systems" - Speaker Absent (Starts in 14 mins)   │
│                                                                                 │
│ Recommended Autonomous Remediation:                                             │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ (Recommended) Option 1: Swap with Pre-Recorded Video Asset                  │ │
│ │ Match: "Autonomous Tool Use" (Similarity 89%, 42m duration, Asset Verified) │ │
│ │ Impact: 0 ripple delays to downstream Track 1 schedule                      │ │
│ │ [ Apply Swap & Push Broadcast ]                                             │ │
│ ├─────────────────────────────────────────────────────────────────────────────┤ │
│ │ Option 2: Cascade Delay (+20 mins)                                          │ │
│ │ Impact: Shifts 3 subsequent sessions; reduces afternoon coffee break by 10m │ │
│ │ [ Apply Cascade Delay ]                                                     │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```
