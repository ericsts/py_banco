<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type QuarantineEntry } from "../api/client";

const items = ref<QuarantineEntry[]>([]);
const loading = ref(true);
const reprocessing = ref(false);
const preview = ref<{ filename: string; texto: string } | null>(null);
const previewLoading = ref<string | null>(null);
const reprocessResult = ref<string | null>(null);

async function load() {
  loading.value = true;
  try {
    items.value = await api.adminListQuarantine();
  } finally {
    loading.value = false;
  }
}

async function verTexto(item: QuarantineEntry) {
  previewLoading.value = item.id;
  preview.value = null;
  try {
    preview.value = await api.adminPreviewQuarantine(item.id);
  } finally {
    previewLoading.value = null;
  }
}

async function reprocessar() {
  reprocessing.value = true;
  reprocessResult.value = null;
  try {
    const r = await api.adminReprocessQuarantine();
    reprocessResult.value = `${r.resolvidos} de ${r.analisados} passaram a ser reconhecidos.`;
    await load();
  } finally {
    reprocessing.value = false;
  }
}

function fmtDate(d: string | null): string {
  return d ? new Date(d).toLocaleString("pt-PT") : "—";
}

onMounted(load);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">Quarentena (formatos não reconhecidos)</h2>
      <button
        class="text-sm px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-50"
        :disabled="reprocessing"
        @click="reprocessar"
      >
        {{ reprocessing ? "Reprocessando…" : "Reprocessar quarentena" }}
      </button>
    </div>

    <p v-if="reprocessResult" class="text-emerald-400 text-sm mb-4">{{ reprocessResult }}</p>
    <p v-if="loading" class="text-slate-500 text-sm">Carregando…</p>
    <p v-else-if="items.length === 0" class="text-slate-500 text-sm">Nada em quarentena no momento.</p>

    <div v-else class="rounded-lg border border-slate-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-900/60 text-slate-500">
          <tr class="text-left">
            <th class="px-4 py-2 font-medium">Arquivo</th>
            <th class="px-4 py-2 font-medium">Usuário</th>
            <th class="px-4 py-2 font-medium">Enviado em</th>
            <th class="px-4 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id" class="border-t border-slate-800/60">
            <td class="px-4 py-2 font-mono text-xs text-slate-300">{{ item.filename }}</td>
            <td class="px-4 py-2 text-slate-400">{{ item.owner_email }}</td>
            <td class="px-4 py-2 text-slate-400">{{ fmtDate(item.uploaded_at) }}</td>
            <td class="px-4 py-2 text-right">
              <button
                v-if="item.pdf_disponivel"
                class="text-xs px-3 py-1 rounded-md bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-40"
                :disabled="previewLoading === item.id"
                @click="verTexto(item)"
              >
                Ver texto extraído
              </button>
              <span v-else class="text-xs text-slate-600">Arquivo removido</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="preview" class="mt-6 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
      <h3 class="text-sm font-medium text-slate-300 mb-2">{{ preview.filename }}</h3>
      <pre class="text-xs text-slate-400 whitespace-pre-wrap max-h-96 overflow-y-auto">{{ preview.texto }}</pre>
    </div>
  </div>
</template>
