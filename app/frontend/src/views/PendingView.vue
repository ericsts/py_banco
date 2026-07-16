<script setup lang="ts">
import { authStore } from "../stores/auth";

async function sair() {
  await authStore.logout();
  window.location.href = "/login";
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 px-4">
    <div class="w-full max-w-sm text-center space-y-4">
      <h1 class="text-xl font-semibold">Banco</h1>
      <p v-if="authStore.state.user?.status === 'rejected'" class="text-red-400 text-sm">
        Seu cadastro não foi aprovado. Fale com o administrador se achar que isso é um engano.
      </p>
      <p v-else class="text-slate-400 text-sm">
        Sua conta ({{ authStore.state.user?.email }}) está aguardando aprovação do administrador. Tente entrar novamente
        mais tarde.
      </p>
      <button class="text-sm text-indigo-300 hover:underline" @click="sair">Sair</button>
    </div>
  </div>
</template>
