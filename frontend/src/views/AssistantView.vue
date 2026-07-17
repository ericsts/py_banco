<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { chatStore } from "../stores/chat";

const ANALYZE_PROMPT =
  "Analise meus gastos recentes: quais são minhas maiores categorias de despesa, " +
  "há algum gasto atípico que valha revisar, e alguma recomendação prática?";

const input = ref("");
const scrollAnchor = ref<HTMLElement | null>(null);

const messages = computed(() => chatStore.state.messages);

function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false }) as string);
}

function scrollToBottom() {
  scrollAnchor.value?.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function send() {
  const text = input.value;
  input.value = "";
  await chatStore.sendMessage(text);
}

async function analisar() {
  if (chatStore.state.sending) return;
  await chatStore.sendMessage(ANALYZE_PROMPT);
}

async function novaConversa() {
  if (chatStore.state.sending) return;
  await chatStore.novaConversa();
}

watch(
  () => messages.value.length + messages.value.reduce((acc, m) => acc + m.content.length, 0),
  () => nextTick(scrollToBottom)
);

onMounted(async () => {
  await chatStore.loadHistory();
  await nextTick(scrollToBottom);
});
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-8.5rem)]">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold">Assistente financeiro</h2>
      <button class="text-sm text-slate-400 hover:text-slate-100" @click="novaConversa">Nova conversa</button>
    </div>

    <p v-if="chatStore.state.loading" class="text-slate-500 text-sm">Carregando…</p>

    <template v-else>
      <div class="flex-1 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/40 p-4 space-y-3 mb-3">
        <div v-if="messages.length === 0" class="text-slate-500 text-sm text-center py-8">
          Pergunte algo sobre seus gastos, ou use o botão abaixo para uma análise geral.
        </div>

        <div v-for="m in messages" :key="m.id" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
          <div
            class="max-w-[80%] rounded-lg px-4 py-2 text-sm"
            :class="
              m.role === 'user'
                ? 'bg-indigo-500/20 text-indigo-100'
                : 'bg-slate-900/60 border border-slate-800 text-slate-200'
            "
          >
            <div v-if="m.role === 'assistant'" class="prose-chat" v-html="renderMarkdown(m.content)"></div>
            <span v-else class="whitespace-pre-wrap">{{ m.content }}</span>
          </div>
        </div>

        <p v-if="chatStore.state.statusText" class="text-slate-500 text-xs italic pl-1">
          {{ chatStore.state.statusText }}
        </p>

        <div ref="scrollAnchor"></div>
      </div>

      <p v-if="chatStore.state.error" class="text-red-400 text-sm mb-2">{{ chatStore.state.error }}</p>

      <div class="mb-3">
        <button
          class="text-sm bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-md px-3 py-1.5 text-slate-300 disabled:opacity-50"
          :disabled="chatStore.state.sending"
          @click="analisar"
        >
          Analisar meus gastos
        </button>
      </div>

      <form class="flex gap-2" @submit.prevent="send">
        <textarea
          v-model="input"
          rows="1"
          placeholder="Pergunte sobre seus gastos…"
          class="flex-1 resize-none bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
          :disabled="chatStore.state.sending"
          @keydown.enter.exact.prevent="send"
        ></textarea>
        <button
          type="submit"
          :disabled="chatStore.state.sending || !input.trim()"
          class="bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          {{ chatStore.state.sending ? "Enviando…" : "Enviar" }}
        </button>
      </form>
    </template>
  </div>
</template>

<style scoped>
.prose-chat :deep(p) {
  margin-bottom: 0.5rem;
}
.prose-chat :deep(ul),
.prose-chat :deep(ol) {
  margin: 0.25rem 0 0.5rem 1.25rem;
  list-style-position: outside;
}
.prose-chat :deep(ul) {
  list-style-type: disc;
}
.prose-chat :deep(ol) {
  list-style-type: decimal;
}
.prose-chat :deep(strong) {
  font-weight: 600;
  color: rgb(241 245 249);
}
.prose-chat :deep(code) {
  background: rgb(30 41 59);
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
  font-size: 0.85em;
}
.prose-chat :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.9em;
}
.prose-chat :deep(th),
.prose-chat :deep(td) {
  border: 1px solid rgb(30 41 59);
  padding: 0.25rem 0.5rem;
  text-align: left;
}
.prose-chat :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
