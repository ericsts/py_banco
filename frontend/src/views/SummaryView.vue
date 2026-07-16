<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, type SummaryRow } from "../api/client";
import MonthlyBarChart from "../components/MonthlyBarChart.vue";

const rows = ref<SummaryRow[]>([]);
const loading = ref(true);
const tipo = ref<"debito" | "credito">("debito");

const meses = computed(() => {
  const set = new Set<string>();
  rows.value.forEach((r) => Object.keys(r.valores).forEach((m) => set.add(m)));
  return [...set].sort();
});

const monthlyTotals = computed(() =>
  meses.value.map((mes) => ({
    mes,
    valor: rows.value.reduce((acc, r) => acc + (r.valores[mes] ?? 0), 0),
  }))
);

const grandTotal = computed(() => rows.value.reduce((acc, r) => acc + r.total, 0));

async function load() {
  loading.value = true;
  try {
    rows.value = await api.summary("grupo", tipo.value);
  } finally {
    loading.value = false;
  }
}

function fmt(v: number): string {
  return v.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

watch(tipo, load);
onMounted(load);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-semibold">Resumo por grupo × mês</h2>
      <div class="inline-flex rounded-md border border-slate-800 overflow-hidden text-sm">
        <button
          class="px-3 py-1.5"
          :class="tipo === 'debito' ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-400 hover:bg-slate-800'"
          @click="tipo = 'debito'"
        >
          Despesas
        </button>
        <button
          class="px-3 py-1.5"
          :class="tipo === 'credito' ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-400 hover:bg-slate-800'"
          @click="tipo = 'credito'"
        >
          Entradas
        </button>
      </div>
    </div>

    <p v-if="loading" class="text-slate-500 text-sm">Carregando…</p>

    <template v-else>
      <div class="rounded-lg border border-slate-800 bg-slate-900/40 p-4 mb-6">
        <div class="flex items-baseline justify-between mb-3">
          <h3 class="text-sm font-medium text-slate-400">
            Total de {{ tipo === "debito" ? "despesas" : "entradas" }} por mês
          </h3>
          <span class="text-lg font-semibold text-slate-100">{{ fmt(grandTotal) }}</span>
        </div>
        <MonthlyBarChart :data="monthlyTotals" />
      </div>

      <div class="rounded-lg border border-slate-800 overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-900/60 text-slate-500">
            <tr class="text-left">
              <th class="px-4 py-2 font-medium sticky left-0 bg-slate-900/60">Grupo</th>
              <th v-for="m in meses" :key="m" class="px-3 py-2 font-medium text-right whitespace-nowrap">{{ m }}</th>
              <th class="px-4 py-2 font-medium text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.chave" class="border-t border-slate-800/60">
              <td class="px-4 py-2 text-slate-200 sticky left-0 bg-slate-950">{{ r.chave }}</td>
              <td v-for="m in meses" :key="m" class="px-3 py-2 text-right font-mono text-slate-400">
                {{ r.valores[m] ? fmt(r.valores[m]) : "—" }}
              </td>
              <td class="px-4 py-2 text-right font-mono font-medium text-slate-100">{{ fmt(r.total) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="border-t border-slate-700 bg-slate-900/60 font-medium">
              <td class="px-4 py-2 sticky left-0 bg-slate-900/60">TOTAL</td>
              <td v-for="m in meses" :key="m" class="px-3 py-2 text-right font-mono">
                {{ fmt(monthlyTotals.find((x) => x.mes === m)?.valor ?? 0) }}
              </td>
              <td class="px-4 py-2 text-right font-mono">{{ fmt(grandTotal) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </template>
  </div>
</template>
