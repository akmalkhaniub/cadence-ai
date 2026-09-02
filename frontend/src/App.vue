<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
    <!-- Navbar -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center font-bold text-emerald-400 font-mono">
            C
          </div>
          <span class="font-bold text-lg tracking-tight">Cadence <span class="text-emerald-400 font-mono text-sm">AI</span></span>
          <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 ml-2 font-mono">Enterprise Event Ops</span>
        </div>

        <!-- Navigation Tabs -->
        <nav class="flex items-center space-x-1 bg-slate-800/60 p-1 rounded-xl border border-slate-700/60">
          <button 
            @click="currentTab = 'provisioning'"
            :class="currentTab === 'provisioning' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition"
          >
            Provisioning Studio
          </button>
          <button 
            @click="currentTab = 'live_ops'"
            :class="currentTab === 'live_ops' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5"
          >
            <span>Live Ops Command</span>
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
          </button>
        </nav>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <ProvisioningStudio v-if="currentTab === 'provisioning'" />
      <LiveOpsCommand v-if="currentTab === 'live_ops'" />
    </main>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ProvisioningStudio from "./views/ProvisioningStudio.vue";
import LiveOpsCommand from "./views/LiveOpsCommand.vue";

const currentTab = ref("provisioning");
</script>
