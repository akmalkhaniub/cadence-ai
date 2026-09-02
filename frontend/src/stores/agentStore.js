import { defineStore } from "pinia";
import { ref } from "vue";

export const useAgentStore = defineStore("agent", () => {
  const isConnected = ref(false);
  const currentNode = ref(null);
  const tokenStream = ref("");
  const isInterrupted = ref(false);
  const hitlPayload = ref(null);
  const isProvisioning = ref(false);
  const activeEvent = ref(null);
  const activeThreadId = ref(null);

  let socket = null;

  function connect(eventId) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/events/${eventId}/agent-stream`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      isConnected.value = true;
      tokenStream.value += "[System] Connected to Cadence Agent Gateway.\n";
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    socket.onclose = () => {
      isConnected.value = false;
      tokenStream.value += "[System] Disconnected from stream.\n";
    };
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "NODE_EXECUTION_STATE":
        currentNode.value = msg.node_name;
        tokenStream.value += `[Node: ${msg.node_name}] ${msg.status}\n`;
        break;
      case "LLM_TOKEN_STREAM":
        tokenStream.value += msg.delta;
        break;
      case "HITL_INTERRUPT_REQUIRED":
        isInterrupted.value = true;
        hitlPayload.value = msg.payload;
        tokenStream.value += "\n[HITL] Execution paused. Human review required for proposed manifest.\n";
        break;
      case "RUN_COMPLETED":
        isProvisioning.value = false;
        isInterrupted.value = false;
        tokenStream.value += `\n[Success] Event provisioned successfully! ID: ${msg.event_id}\n`;
        if (msg.event_id) {
          fetchManifest(msg.event_id);
        }
        break;
    }
  }

  function startProvisioning(rawBriefText, tenantId) {
    isProvisioning.value = true;
    tokenStream.value = `[Agent] Initializing LangGraph provisioning pipeline...\n`;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: "START_PROVISIONING",
        raw_brief_text: rawBriefText,
        tenant_id: tenantId
      }));
    }
  }

  function submitDecision(decision, feedback = null) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      tokenStream.value += `[HITL] Decision submitted: ${decision}\n`;
      socket.send(JSON.stringify({
        type: "HITL_INTERRUPT_RESPONSE",
        decision: decision,
        rejection_feedback: feedback
      }));
      isInterrupted.value = false;
      hitlPayload.value = null;
    }
  }

  async function fetchManifest(eventId) {
    try {
      const res = await fetch(`/api/v1/events/${eventId}/manifest`);
      if (res.ok) {
        activeEvent.value = await res.json();
      }
    } catch (e) {
      console.error("Failed to load event manifest:", e);
    }
  }

  return {
    isConnected,
    currentNode,
    tokenStream,
    isInterrupted,
    hitlPayload,
    isProvisioning,
    activeEvent,
    activeThreadId,
    connect,
    startProvisioning,
    submitDecision,
    fetchManifest
  };
});
