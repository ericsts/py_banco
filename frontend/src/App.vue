<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { authStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();

const links = computed(() => {
  const base = [
    { to: "/arquivos", label: "Arquivos" },
    { to: "/lancamentos", label: "Lançamentos" },
    { to: "/resumo", label: "Resumo" },
    { to: "/assistente", label: "Assistente" },
  ];
  if (authStore.state.user?.role === "admin") {
    base.push({ to: "/admin/usuarios", label: "Usuários" }, { to: "/admin/quarentena", label: "Quarentena" });
  }
  return base;
});

const showChrome = computed(() => !route.meta.public && route.name !== "conta-pendente");

async function sair() {
  await authStore.logout();
  router.push("/login");
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header v-if="showChrome" class="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-10">
      <div class="max-w-6xl mx-auto px-6 py-4 flex items-center gap-8">
        <h1 class="text-lg font-semibold tracking-tight">Banco <span class="text-slate-500">/ gestão de extratos</span></h1>
        <nav class="flex gap-1">
          <RouterLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
            :class="route.path === link.to ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'"
          >
            {{ link.label }}
          </RouterLink>
        </nav>
        <div class="ml-auto flex items-center gap-3 text-sm text-slate-400">
          <span>{{ authStore.state.user?.email }}</span>
          <button class="hover:text-slate-100" @click="sair">Sair</button>
        </div>
      </div>
    </header>
    <main :class="showChrome ? 'max-w-6xl mx-auto px-6 py-8' : ''">
      <RouterView />
    </main>
  </div>
</template>
