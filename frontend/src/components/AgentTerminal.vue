<template>
  <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col h-96">
    <div class="bg-slate-800/80 px-4 py-2.5 border-b border-slate-700/60 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <div class="w-3 h-3 rounded-full bg-red-500/80"></div>
        <div class="w-3 h-3 rounded-full bg-yellow-500/80"></div>
        <div class="w-3 h-3 rounded-full bg-green-500/80"></div>
        <span class="text-xs font-mono text-slate-400 ml-2">cadence-agent-runtime</span>
      </div>
      <div class="flex items-center space-x-2">
        <span v-if="currentNode" class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-mono">
          Node: {{ currentNode }}
        </span>
        <span :class="isConnected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'" class="text-xs px-2 py-0.5 rounded-full font-mono">
          {{ isConnected ? "CONNECTED" : "OFFLINE" }}
        </span>
      </div>
    </div>
    <div ref="terminalBody" class="p-4 flex-1 overflow-y-auto font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
      {{ tokenStream || "Awaiting task input..." }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";

const props = defineProps({
  tokenStream: String,
  currentNode: String,
  isConnected: Boolean
});

const terminalBody = ref(null);

watch(() => props.tokenStream, async () => {
  await nextTick();
  if (terminalBody.value) {
    terminalBody.value.scrollTop = terminalBody.value.scrollHeight;
  }
});
</script>
