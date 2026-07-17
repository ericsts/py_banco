import { createRouter, createWebHistory } from "vue-router";
import LoginView from "./views/LoginView.vue";
import RegisterView from "./views/RegisterView.vue";
import PendingView from "./views/PendingView.vue";
import FilesView from "./views/FilesView.vue";
import TransactionsView from "./views/TransactionsView.vue";
import SummaryView from "./views/SummaryView.vue";
import AssistantView from "./views/AssistantView.vue";
import AdminUsersView from "./views/AdminUsersView.vue";
import AdminQuarantineView from "./views/AdminQuarantineView.vue";
import { authStore } from "./stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/arquivos" },
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/cadastro", name: "cadastro", component: RegisterView, meta: { public: true } },
    { path: "/conta-pendente", name: "conta-pendente", component: PendingView, meta: { requiresAuth: true } },
    { path: "/arquivos", name: "arquivos", component: FilesView, meta: { requiresApproved: true } },
    { path: "/lancamentos", name: "lancamentos", component: TransactionsView, meta: { requiresApproved: true } },
    { path: "/resumo", name: "resumo", component: SummaryView, meta: { requiresApproved: true } },
    { path: "/assistente", name: "assistente", component: AssistantView, meta: { requiresApproved: true } },
    { path: "/admin/usuarios", name: "admin-usuarios", component: AdminUsersView, meta: { requiresAdmin: true } },
    { path: "/admin/quarentena", name: "admin-quarentena", component: AdminQuarantineView, meta: { requiresAdmin: true } },
  ],
});

router.beforeEach(async (to) => {
  if (to.meta.public) return true;

  if (!authStore.state.loaded) {
    await authStore.fetchMe();
  }
  const user = authStore.state.user;

  if (!user) return { name: "login" };

  if (to.meta.requiresAdmin) {
    if (user.status !== "approved") return { name: "conta-pendente" };
    if (user.role !== "admin") return { name: "arquivos" };
    return true;
  }

  if (to.meta.requiresApproved && user.status !== "approved") {
    return { name: "conta-pendente" };
  }

  if (to.name === "conta-pendente" && user.status === "approved") {
    return { name: "arquivos" };
  }

  return true;
});

export default router;
