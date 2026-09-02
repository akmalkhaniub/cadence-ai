<template>
  <div v-if="manifest" class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-4">
      <div>
        <span class="text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold">{{ manifest.format }} CONFERENCE</span>
        <h2 class="text-xl font-bold text-slate-100 mt-0.5">{{ manifest.title }}</h2>
      </div>
      <div class="flex items-center space-x-3">
        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
          {{ manifest.status }}
        </span>
      </div>
    </div>

    <!-- Tracks & Sessions -->
    <div>
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Provisioned Agenda & Sessions</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          v-for="session in manifest.sessions" 
          :key="session.id"
          class="bg-slate-800/60 border border-slate-700/60 rounded-lg p-4 hover:border-slate-600 transition"
        >
          <div class="flex items-center justify-between text-xs text-slate-400 mb-1.5">
            <span class="font-mono text-emerald-400">{{ session.duration }} mins</span>
            <span>{{ new Date(session.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
          <h4 class="text-sm font-semibold text-slate-100">{{ session.title }}</h4>
          <p v-if="session.speakers?.length" class="text-xs text-slate-400 mt-2">
            Speaker: <span class="text-slate-200">{{ session.speakers.join(', ') }}</span>
          </p>
        </div>
      </div>
    </div>

    <!-- Sponsors & Booths -->
    <div v-if="manifest.sponsors?.length">
      <h3 class="text-sm font-semibold text-slate-300 mb-3">Sponsors & Exhibitor Booths</h3>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div 
          v-for="sponsor in manifest.sponsors" 
          :key="sponsor.name"
          class="bg-slate-800/40 border border-slate-700/40 rounded-lg p-3 text-center"
        >
          <span class="text-xs px-2 py-0.5 rounded font-mono font-bold" :class="tierClass(sponsor.tier)">
            {{ sponsor.tier }}
          </span>
          <p class="text-sm font-semibold text-slate-100 mt-2">{{ sponsor.name }}</p>
          <p class="text-xs text-slate-400 mt-0.5">{{ sponsor.booth || 'Standard Booth' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  manifest: Object
});

function tierClass(tier) {
  switch (tier) {
    case 'PLATINUM': return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
    case 'GOLD': return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
    default: return 'bg-slate-700 text-slate-300';
  }
}
</script>
