import { reactive } from "vue";
import { api, type CurrentUser } from "../api/client";

const state = reactive<{ user: CurrentUser | null; loaded: boolean }>({
  user: null,
  loaded: false,
});

async function fetchMe(): Promise<CurrentUser | null> {
  try {
    state.user = await api.me();
  } catch {
    state.user = null;
  } finally {
    state.loaded = true;
  }
  return state.user;
}

async function login(email: string, password: string): Promise<CurrentUser> {
  const user = await api.login(email, password);
  state.user = user;
  state.loaded = true;
  return user;
}

async function logout() {
  await api.logout().catch(() => {});
  state.user = null;
}

export const authStore = { state, fetchMe, login, logout };
