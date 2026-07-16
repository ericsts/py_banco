<script setup lang="ts">
import { ref } from "vue";
import { api, ApiError } from "../api/client";

const email = ref("");
const password = ref("");
const error = ref<string | null>(null);
const loading = ref(false);
const done = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await api.register(email.value, password.value);
    done.value = true;
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail : "Não foi possível cadastrar";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-4">
    <div class="w-full max-w-sm">
      <h1 class="text-xl font-semibold mb-6 text-center">Banco <span class="text-slate-500">/ cadastro</span></h1>

      <div v-if="done" class="text-center space-y-3">
        <p class="text-emerald-400 text-sm">Cadastro enviado! Sua conta está aguardando aprovação do administrador.</p>
        <RouterLink to="/login" class="text-indigo-300 hover:underline text-sm">Voltar para o login</RouterLink>
      </div>

      <form v-else class="space-y-3" @submit.prevent="submit">
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
          minlength="8"
          placeholder="Senha (mín. 8 caracteres)"
          class="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
        />
        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>
        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 rounded-md px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          {{ loading ? "Enviando…" : "Cadastrar" }}
        </button>
      </form>
      <p v-if="!done" class="text-center text-sm text-slate-500 mt-4">
        Já tem conta?
        <RouterLink to="/login" class="text-indigo-300 hover:underline">Entrar</RouterLink>
      </p>
    </div>
  </div>
</template>
