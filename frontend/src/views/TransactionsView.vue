<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, type Transaction } from "../api/client";

const items = ref<Transaction[]>([]);
const total = ref(0);
const totalValor = ref(0);
const subtotaisMes = ref<Record<string, number>>({});
const loading = ref(true);
const page = ref(1);
const pageSize = 100;

const meses = ref<string[]>([]);
const grupos = ref<string[]>([]);

const filtroMes = ref("");
const filtroFonte = ref("");
const filtroGrupo = ref("");
const filtroBusca = ref("");
const filtroTipo = ref("debito");

async function loadFiltros() {
  [meses.value, grupos.value] = await Promise.all([api.listMeses(), api.listGrupos()]);
}

async function load() {
  loading.value = true;
  try {
    const res = await api.listTransactions({
      ano_mes: filtroMes.value,
      fonte: filtroFonte.value,
      grupo: filtroGrupo.value,
      tipo: filtroTipo.value,
      q: filtroBusca.value,
      page: page.value,
      page_size: pageSize,
    });
    items.value = res.items;
    total.value = res.total;
    totalValor.value = res.total_valor;
    subtotaisMes.value = res.subtotais_mes;
  } finally {
    loading.value = false;
  }
}

watch([filtroMes, filtroFonte, filtroGrupo, filtroTipo, filtroBusca], () => {
  page.value = 1;
  load();
});
watch(page, load);

onMounted(async () => {
  await loadFiltros();
  await load();
});

function fmtValor(v: number): string {
  return v.toLocaleString("pt-PT", { style: "currency", currency: "EUR" });
}

const totalPages = () => Math.max(1, Math.ceil(total.value / pageSize));

// Os itens já vêm ordenados por data desc, então o mesmo mês fica sempre
// contíguo: insere uma linha de subtotal sempre que o mês muda (ou no fim
// da página). O valor do subtotal é o total real do mês inteiro (todas as
// páginas que casam com os filtros atuais), não só o que está nesta página.
type Row = { kind: "tx"; tx: Transaction } | { kind: "subtotal"; mes: string; valor: number };

const rows = computed<Row[]>(() => {
  const out: Row[] = [];
  items.value.forEach((tx, i) => {
    out.push({ kind: "tx", tx });
    const next = items.value[i + 1];
    if (!next || next.ano_mes !== tx.ano_mes) {
      out.push({ kind: "subtotal", mes: tx.ano_mes, valor: subtotaisMes.value[tx.ano_mes] ?? 0 });
    }
  });
  return out;
});
</script>

<template>
  <div>
    <h2 class="text-xl font-semibold mb-6">Lançamentos</h2>

    <div class="flex flex-wrap gap-3 mb-4">
      <select v-model="filtroMes" class="bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 text-sm">
        <option value="">Todos os meses</option>
        <option v-for="m in meses" :key="m" :value="m">{{ m }}</option>
      </select>
      <select v-model="filtroFonte" class="bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 text-sm">
        <option value="">Cartão + Conta</option>
        <option value="cartao">Cartão</option>
        <option value="conta">Conta</option>
      </select>
      <select v-model="filtroGrupo" class="bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 text-sm max-w-[16rem]">
        <option value="">Todos os grupos</option>
        <option v-for="g in grupos" :key="g" :value="g">{{ g }}</option>
      </select>
      <select v-model="filtroTipo" class="bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 text-sm">
        <option value="debito">Despesas</option>
        <option value="credito">Entradas</option>
        <option value="">Despesas + Entradas</option>
      </select>
      <input
        v-model="filtroBusca"
        placeholder="Buscar na descrição…"
        class="bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 text-sm flex-1 min-w-[12rem]"
      />
    </div>

    <p class="text-slate-500 text-xs mb-2">{{ total }} lançamentos</p>

    <div class="rounded-lg border border-slate-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-900/60 text-slate-500">
          <tr class="text-left">
            <th class="px-4 py-2 font-medium">Data</th>
            <th class="px-4 py-2 font-medium">Fonte</th>
            <th class="px-4 py-2 font-medium">Descrição</th>
            <th class="px-4 py-2 font-medium">Grupo</th>
            <th class="px-4 py-2 font-medium text-right">Valor</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="px-4 py-6 text-center text-slate-500">Carregando…</td>
          </tr>
          <template v-for="row in rows" :key="row.kind === 'tx' ? row.tx.id : `subtotal-${row.mes}`">
            <tr v-if="row.kind === 'tx'" class="border-t border-slate-800/60">
              <td class="px-4 py-2 text-slate-400 whitespace-nowrap">{{ row.tx.data }}</td>
              <td class="px-4 py-2 text-slate-400 capitalize">{{ row.tx.fonte }}</td>
              <td class="px-4 py-2 text-slate-200">{{ row.tx.descricao_original }}</td>
              <td class="px-4 py-2 text-slate-400">{{ row.tx.grupo }}</td>
              <td
                class="px-4 py-2 text-right font-mono"
                :class="row.tx.tipo === 'credito' ? 'text-emerald-400' : 'text-slate-200'"
              >
                {{ row.tx.tipo === "credito" ? "+" : "−" }}{{ fmtValor(row.tx.valor) }}
              </td>
            </tr>
            <tr v-else class="border-t border-slate-700 bg-slate-900/70">
              <td colspan="4" class="px-4 py-2 text-slate-400 font-medium">Subtotal {{ row.mes }}</td>
              <td class="px-4 py-2 text-right font-mono font-medium text-slate-100">{{ fmtValor(row.valor) }}</td>
            </tr>
          </template>
        </tbody>
        <tfoot v-if="!loading">
          <tr class="border-t-2 border-slate-600 bg-slate-900">
            <td colspan="4" class="px-4 py-3 text-slate-200 font-semibold">
              Total geral (todos os lançamentos filtrados, não só esta página)
            </td>
            <td class="px-4 py-3 text-right font-mono font-semibold text-slate-100">{{ fmtValor(totalValor) }}</td>
          </tr>
        </tfoot>
      </table>
    </div>

    <div class="flex items-center justify-between mt-4 text-sm text-slate-400">
      <button
        class="px-3 py-1 rounded-md bg-slate-800 disabled:opacity-30"
        :disabled="page <= 1"
        @click="page--"
      >
        Anterior
      </button>
      <span>Página {{ page }} de {{ totalPages() }}</span>
      <button
        class="px-3 py-1 rounded-md bg-slate-800 disabled:opacity-30"
        :disabled="page >= totalPages()"
        @click="page++"
      >
        Próxima
      </button>
    </div>
  </div>
</template>
