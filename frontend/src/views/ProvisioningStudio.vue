<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-100 tracking-tight">Autonomous Provisioning Studio</h1>
        <p class="text-sm text-slate-400 mt-1">Upload unstructured briefs or enter requirements to compile multi-track events autonomously.</p>
      </div>
      <div class="flex items-center space-x-3">
        <button 
          @click="loadSampleBrief"
          class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
        >
          Load Sample Brief
        </button>
      </div>
    </div>

    <!-- Main Grid: Input + Terminal -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Input Column -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
        <div>
          <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Event Brief & Constraints</label>
          <textarea 
            v-model="briefText"
            rows="12"
            placeholder="title: 3-Day Global Developer Summit\nFormat: Hybrid (In-Person + Virtual)\nTracks: AI Agents, Cloud Infrastructure\nSpeakers: Dr. Reed, Alex Murphy\nSponsors: OmniCorp (Platinum)..."
            class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition leading-relaxed resize-none"
          ></textarea>
        </div>
        <div class="mt-4 flex items-center justify-between pt-4 border-t border-slate-800/80">
          <span class="text-xs text-slate-500">Autonomous DAG Planner via LangGraph</span>
          <button 
            @click="handleStart"
            :disabled="agentStore.isProvisioning || !briefText.trim()"
            class="px-5 py-2.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2"
          >
            <span>{{ agentStore.isProvisioning ? "Agents Executing..." : "Generate Event Architecture" }}</span>
          </button>
        </div>
      </div>

      <!-- Real-Time Execution Terminal -->
      <AgentTerminal 
        :tokenStream="agentStore.tokenStream"
        :currentNode="agentStore.currentNode"
        :isConnected="agentStore.isConnected"
      />
    </div>

    <!-- Provisioned Event Canvas -->
    <ScheduleGrid 
      v-if="agentStore.activeEvent" 
      :manifest="agentStore.activeEvent" 
    />

    <!-- HITL Modal -->
    <ApprovalDiffModal 
      :isOpen="agentStore.isInterrupted"
      :diff="agentStore.hitlPayload?.diff_manifest"
      @decision="handleDecision"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useAgentStore } from "../stores/agentStore";
import AgentTerminal from "../components/AgentTerminal.vue";
import ApprovalDiffModal from "../components/ApprovalDiffModal.vue";
import ScheduleGrid from "../components/ScheduleGrid.vue";

const agentStore = useAgentStore();
const briefText = ref("");

onMounted(() => {
  // Connect to persistent demo event session
  agentStore.connect("demo-event-01");
});

function loadSampleBrief() {
  briefText.value = `title: Cadence Global Tech Summit 2026
Format: Virtual Summit with Global Multi-Timezone Streams
Tracks: Autonomous Systems, Cloud Native Scale
Rooms: Main Auditorium A, Breakout Room B
Keynote: "Scalable Agentic Systems with LangGraph" by Dr. Samantha Reed (sarah@ai-institute.org)
Breakout: "Deterministic Saga Rollbacks" by Alex Chen (alex@enterprise.com)
Sponsors: OmniCorp Global (Platinum Tier), Cyberdyne Labs (Gold Tier)`;
}

function handleStart() {
  agentStore.startProvisioning(briefText.value, "00000000-0000-0000-0000-000000000001");
}

function handleDecision(decision, feedback) {
  agentStore.submitDecision(decision, feedback);
}
</script>
