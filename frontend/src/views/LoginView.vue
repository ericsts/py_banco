<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "../api/client";
import { authStore } from "../stores/auth";

const email = ref("");
const password = ref("");
const error = ref<string | null>(null);
const loading = ref(false);
const router = useRouter();

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    const user = await authStore.login(email.value, password.value);
    router.push(user.status === "approved" ? "/arquivos" : "/conta-pendente");
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : "Não foi possível entrar";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-4">
    <div class="w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-6 text-center">Banco <span class="text-slate-500">/ entrar</span></h1>
      <form class="space-y-3" @submit.prevent="submit">
        <input
          v-model="email"
          type="email"
          required
          placeholder="Email"
          class="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
        />
        <input
          v-model="password"
          type="password"
          required
          placeholder="Senha"
          class="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
        />
        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 rounded-md px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {{ loading ? "Entrando…" : "Entrar" }}
        </button>
      </form>
      <p class="text-center text-sm text-slate-500 mt-4">
        Não tem conta?
        <RouterLink to="/cadastro" class="text-indigo-300 hover:underline">Cadastre-se</RouterLink>
      </p>
    </div>
  </div>
</template>
