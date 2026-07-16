<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type AdminUser } from "../api/client";

const users = ref<AdminUser[]>([]);
const loading = ref(true);
const busy = ref<Set<string>>(new Set());

async function load() {
  loading.value = true;
  try {
    users.value = await api.adminListUsers();
  } finally {
    loading.value = false;
  }
}

async function approve(u: AdminUser) {
  busy.value.add(u.id);
  try {
    await api.adminApproveUser(u.id);
    await load();
  } finally {
    busy.value.delete(u.id);
  }
}

async function reject(u: AdminUser) {
  busy.value.add(u.id);
  try {
    await api.adminRejectUser(u.id);
    await load();
  } finally {
    busy.value.delete(u.id);
  }
}

function fmtDate(d: string): string {
  return new Date(d).toLocaleString("pt-PT");
}

const statusLabel: Record<string, string> = { pending: "Pendente", approved: "Aprovado", rejected: "Rejeitado" };
const statusClass: Record<string, string> = {
  pending: "text-amber-400",
  approved: "text-emerald-400",
  rejected: "text-red-400",
};

onMounted(load);
</script>

<template>
  <div>
    <h2 class="text-xl font-semibold mb-6">Usuários</h2>
    <p v-if="loading" class="text-slate-500 text-sm">Carregando…</p>

    <div v-else class="rounded-lg border border-slate-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-900/60 text-slate-500">
          <tr class="text-left">
            <th class="px-4 py-2 font-medium">Email</th>
            <th class="px-4 py-2 font-medium">Papel</th>
            <th class="px-4 py-2 font-medium">Cadastrado em</th>
            <th class="px-4 py-2 font-medium">Status</th>
            <th class="px-4 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-t border-slate-800/60">
            <td class="px-4 py-2 text-slate-200">{{ u.email }}</td>
            <td class="px-4 py-2 text-slate-400 capitalize">{{ u.role }}</td>
            <td class="px-4 py-2 text-slate-400">{{ fmtDate(u.created_at) }}</td>
            <td class="px-4 py-2 font-medium" :class="statusClass[u.status]">{{ statusLabel[u.status] }}</td>
            <td class="px-4 py-2 text-right space-x-2">
              <button
                v-if="u.status !== 'approved'"
                class="text-xs px-3 py-1 rounded-md bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-40"
                :disabled="busy.has(u.id)"
                @click="approve(u)"
              >
                Aprovar
              </button>
              <button
                v-if="u.status !== 'rejected'"
                class="text-xs px-3 py-1 rounded-md bg-red-500/20 text-red-300 hover:bg-red-500/30 disabled:opacity-40"
                :disabled="busy.has(u.id)"
                @click="reject(u)"
              >
                Rejeitar
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
