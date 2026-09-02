<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl">
      <div class="flex items-center justify-between pb-4 border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-lg">
            !
          </div>
          <div>
            <h3 class="text-lg font-semibold text-slate-100">Human-in-the-Loop Approval Required</h3>
            <p class="text-xs text-slate-400">Review proposed event structure before committing to platform database.</p>
          </div>
        </div>
      </div>

      <div class="my-6 space-y-4">
        <div class="p-4 bg-slate-800/60 rounded-xl border border-slate-700/60">
          <h4 class="text-sm font-semibold text-emerald-400 mb-2">Proposed Architecture</h4>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              <span class="text-2xl font-bold text-slate-100">{{ diff?.tracks_count || 0 }}</span>
              <p class="text-xs text-slate-400 mt-1">Tracks</p>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              <span class="text-2xl font-bold text-slate-100">{{ diff?.rooms_count || 0 }}</span>
              <p class="text-xs text-slate-400 mt-1">Rooms</p>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              <span class="text-2xl font-bold text-slate-100">{{ diff?.sessions_count || 0 }}</span>
              <p class="text-xs text-slate-400 mt-1">Sessions</p>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800">
              <span class="text-2xl font-bold text-slate-100">{{ diff?.booths_count || 0 }}</span>
              <p class="text-xs text-slate-400 mt-1">Sponsors</p>
            </div>
          </div>
        </div>

        <div v-if="feedbackVisible" class="mt-4">
          <label class="block text-xs font-medium text-slate-300 mb-1">Rejection Feedback / Change Request</label>
          <textarea 
            v-model="feedbackText"
            placeholder="e.g. Move the morning keynote to 10:00 AM..."
            class="w-full h-20 bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          ></textarea>
        </div>
      </div>

      <div class="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
        <button 
          v-if="!feedbackVisible"
          @click="feedbackVisible = true"
          class="px-4 py-2 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-500/10 border border-rose-500/30 transition"
        >
          Request Changes / Reject
        </button>
        <button 
          v-if="feedbackVisible"
          @click="submitRejection"
          class="px-4 py-2 rounded-lg text-xs font-medium bg-rose-600 hover:bg-rose-500 text-white transition"
        >
          Submit Feedback
        </button>
        <button 
          @click="$emit('decision', 'APPROVED')"
          class="px-5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition"
        >
          Approve & Provision via MCP
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  isOpen: Boolean,
  diff: Object
});

const emit = defineEmits(["decision"]);

const feedbackVisible = ref(false);
const feedbackText = ref("");

function submitRejection() {
  emit("decision", "REJECTED", feedbackText.value);
  feedbackVisible.value = false;
  feedbackText.value = "";
}
</script>
