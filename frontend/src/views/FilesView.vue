<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, ApiError, type FileEntry } from "../api/client";
import { authStore } from "../stores/auth";

const files = ref<FileEntry[]>([]);
const loading = ref(true);
const importing = ref<Set<string>>(new Set());
const uploading = ref(false);
const errorMsg = ref<string | null>(null);
const verTodos = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const isAdmin = () => authStore.state.user?.role === "admin";

async function load() {
  loading.value = true;
  errorMsg.value = null;
  try {
    files.value = await api.listFiles(verTodos.value);
  } catch (e) {
    errorMsg.value = "Não foi possível carregar a lista de arquivos.";
  } finally {
    loading.value = false;
  }
}

async function onFilesSelected(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const selected = input.files;
  if (!selected || selected.length === 0) return;
  uploading.value = true;
  errorMsg.value = null;
  try {
    for (const file of Array.from(selected)) {
      await api.uploadFile(file);
    }
    await load();
  } catch (e) {
    errorMsg.value = e instanceof ApiError ? e.detail : "Falha no upload";
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

async function doImport(f: FileEntry) {
  importing.value.add(f.id);
  try {
    await api.importFile(f.id);
  } catch (e) {
    /* refletido pelo status ao recarregar */
  } finally {
    importing.value.delete(f.id);
    await load();
  }
}

async function doPurge(f: FileEntry) {
  await api.purgeFile(f.id);
  await load();
}

function formatSize(bytes: number): string {
  return `${(bytes / 1024).toFixed(0)} KB`;
}

function docTypeLabel(t: string): string {
  return { cartao: "Cartão", conta: "Conta", unsupported: "Não reconhecido" }[t] ?? t;
}

function fmtDate(d: string | null): string {
  return d ? new Date(d).toLocaleString("pt-PT") : "—";
}

onMounted(load);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">Arquivos</h2>
      <div class="flex items-center gap-3">
        <label v-if="isAdmin()" class="text-sm text-slate-400 flex items-center gap-1.5">
          <input type="checkbox" v-model="verTodos" @change="load" />
          Ver de todos os usuários
        </label>
        <button
          class="text-sm px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200"
          @click="load"
        >
          Atualizar
        </button>
        <button
          class="text-sm px-3 py-1.5 rounded-md bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-50"
          :disabled="uploading"
          @click="fileInput?.click()"
        >
          {{ uploading ? "Enviando…" : "Enviar extrato" }}
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="application/pdf,.pdf,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          multiple
          class="hidden"
          @change="onFilesSelected"
        />
      </div>
    </div>

    <p class="text-slate-500 text-xs mb-3">
      Aceita PDF ou XLSX. Arquivos enviados ficam disponíveis por 7 dias (o histórico de lançamentos importados
      permanece depois disso).
    </p>

    <p v-if="errorMsg" class="text-red-400 text-sm mb-4">{{ errorMsg }}</p>
    <p v-else-if="loading" class="text-slate-500 text-sm">Carregando…</p>
    <p v-else-if="files.length === 0" class="text-slate-500 text-sm">Nenhum arquivo enviado ainda.</p>

    <div v-else class="rounded-lg border border-slate-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-900/60 text-slate-500">
          <tr class="text-left">
            <th class="px-4 py-2 font-medium">Arquivo</th>
            <th v-if="verTodos" class="px-4 py-2 font-medium">Usuário</th>
            <th class="px-4 py-2 font-medium">Tipo</th>
            <th class="px-4 py-2 font-medium">Tamanho</th>
            <th class="px-4 py-2 font-medium">Enviado em</th>
            <th class="px-4 py-2 font-medium">Status</th>
            <th class="px-4 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id" class="border-t border-slate-800/60">
            <td class="px-4 py-2 font-mono text-xs text-slate-300">{{ f.filename }}</td>
            <td v-if="verTodos" class="px-4 py-2 text-slate-400">{{ f.owner_email }}</td>
            <td class="px-4 py-2 text-slate-400">{{ docTypeLabel(f.doc_type) }}</td>
            <td class="px-4 py-2 text-slate-500">{{ formatSize(f.size_bytes) }}</td>
            <td class="px-4 py-2 text-slate-500">{{ fmtDate(f.uploaded_at) }}</td>
            <td class="px-4 py-2">
              <span v-if="f.status === 'imported'" class="inline-flex items-center gap-1.5 text-emerald-400">
                ✅ Importado
                <span class="text-slate-500">({{ f.transaction_count }} lançamentos)</span>
              </span>
              <span v-else-if="f.status === 'error'" class="inline-flex items-center gap-1.5 text-red-400" :title="f.last_error ?? ''">
                ⚠️ Erro na importação
              </span>
              <span v-else-if="f.status === 'unsupported'" class="text-amber-400">
                🔍 Não reconhecido (em quarentena)
              </span>
              <span v-else class="text-slate-500"> ⚪ Não importado </span>
              <span v-if="!f.pdf_disponivel" class="block text-[11px] text-slate-600">Arquivo removido (retenção)</span>
            </td>
            <td class="px-4 py-2 text-right space-x-2 whitespace-nowrap">
              <button
                v-if="f.status !== 'unsupported' && f.pdf_disponivel"
                class="text-xs px-3 py-1 rounded-md bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-40"
                :disabled="importing.has(f.id)"
                @click="doImport(f)"
              >
                {{ importing.has(f.id) ? "Importando…" : f.status === "imported" ? "Reimportar" : "Importar" }}
              </button>
              <button
                v-if="f.pdf_disponivel"
                class="text-xs px-3 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"
                @click="doPurge(f)"
              >
                Remover arquivo
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
