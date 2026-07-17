import { reactive } from "vue";
import { api, streamAssistantMessage, type ChatMessage } from "../api/client";

const state = reactive<{
  messages: ChatMessage[];
  loading: boolean;
  sending: boolean;
  statusText: string | null;
  error: string | null;
}>({ messages: [], loading: true, sending: false, statusText: null, error: null });

async function loadHistory() {
  state.loading = true;
  try {
    state.messages = await api.listChatMessages();
  } finally {
    state.loading = false;
  }
}

async function sendMessage(text: string) {
  if (!text.trim() || state.sending) return;
  state.error = null;
  state.sending = true;
  state.statusText = null;

  state.messages.push({ id: crypto.randomUUID(), role: "user", content: text, created_at: new Date().toISOString() });
  const assistantMsg: ChatMessage = {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "",
    created_at: new Date().toISOString(),
  };
  state.messages.push(assistantMsg);

  try {
    await streamAssistantMessage(text, {
      onStatus: (msg) => {
        state.statusText = msg;
      },
      onDelta: (chunk) => {
        assistantMsg.content += chunk;
        state.statusText = null;
      },
      onError: (msg) => {
        state.error = msg;
      },
      onDone: () => {},
    });
  } finally {
    state.sending = false;
    state.statusText = null;
  }
}

async function novaConversa() {
  await api.clearChat();
  state.messages = [];
  state.error = null;
}

export const chatStore = { state, loadHistory, sendMessage, novaConversa };
