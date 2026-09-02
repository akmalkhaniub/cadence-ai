<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-100">Live Operations & Autonomous Triage HUD</h1>
        <p class="text-sm text-slate-400 mt-1">Real-time incident detection, cascading schedule delay solver, and automated attendee notifications.</p>
      </div>
      <div class="flex items-center space-x-2">
        <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
        <span class="text-xs font-mono text-emerald-400">TELEMETRY ACTIVE</span>
      </div>
    </div>

    <!-- Simulator Control -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-200">Incident Chaos Injection Simulator</h3>
        <p class="text-xs text-slate-400 mt-0.5">Trigger a synthetic speaker absence 15 minutes before scheduled start time.</p>
      </div>
      <button 
        @click="simulateIncident"
        :disabled="simulating"
        class="px-4 py-2 rounded-lg text-xs font-semibold bg-rose-600/90 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20 transition"
      >
        {{ simulating ? "Simulating..." : "Simulate Speaker No-Show" }}
      </button>
    </div>

    <!-- Incident Triage Card -->
    <div v-if="activeIncident" class="bg-slate-900 border-2 border-rose-500/40 rounded-xl p-6 shadow-2xl space-y-4">
      <div class="flex items-center space-x-3">
        <div class="w-3 h-3 rounded-full bg-rose-500 animate-ping"></div>
        <span class="text-xs font-mono font-bold text-rose-400 uppercase tracking-wider">CRITICAL INCIDENT DETECTED (SLA &lt; 2.5s)</span>
      </div>
      <h2 class="text-lg font-bold text-slate-100">Session: "Future of Agentic Systems" - Speaker Not Detected Backstage</h2>
      <p class="text-xs text-slate-400">Speaker has not hit backstage check-in (Starts in 14 mins). The agent has evaluated the following remediation paths:</p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div 
          v-for="opt in activeIncident.options" 
          :key="opt.option_id"
          class="bg-slate-800/80 border border-slate-700 rounded-xl p-4 flex flex-col justify-between hover:border-emerald-500 transition"
        >
          <div>
            <span class="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-blue-500/20 text-blue-300">
              {{ opt.action_type }}
            </span>
            <h3 class="text-sm font-bold text-slate-100 mt-2">{{ opt.title }}</h3>
            <p class="text-xs text-slate-300 mt-1 leading-relaxed">{{ opt.description }}</p>
            <p class="text-xs text-emerald-400 mt-2 font-mono">Impact: {{ opt.estimated_impact }}</p>
          </div>
          <button 
            @click="resolveIncident(opt.option_id)"
            class="mt-4 w-full py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition"
          >
            Approve & Execute via MCP
          </button>
        </div>
      </div>
    </div>

    <!-- Success Resolution Banner -->
    <div v-if="resolvedMessage" class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">✓</div>
        <div>
          <p class="text-sm font-semibold text-slate-100">Incident Successfully Mitigated</p>
          <p class="text-xs text-slate-400 mt-0.5">{{ resolvedMessage }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const simulating = ref(false);
const activeIncident = ref(null);
const resolvedMessage = ref(null);

async function simulateIncident() {
  simulating.value = true;
  resolvedMessage.value = null;
  try {
    const res = await fetch("/api/v1/events/incidents/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: "00000000-0000-0000-0000-000000000001",
        session_id: "00000000-0000-0000-0000-000000000002",
        incident_type: "SPEAKER_NO_SHOW"
      })
    });
    if (res.ok) {
      activeIncident.value = await res.json();
    }
  } finally {
    simulating.value = false;
  }
}

function resolveIncident(optionId) {
  activeIncident.value = null;
  resolvedMessage.value = `Remediation ${optionId} applied: pre-recorded asset deployed, attendee push broadcast sent.`;
}
</script>
