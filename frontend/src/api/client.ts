export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export interface FileEntry {
  id: string;
  filename: string;
  doc_type: "cartao" | "conta" | "unsupported";
  size_bytes: number;
  uploaded_at: string | null;
  status: "not_imported" | "imported" | "error" | "unsupported";
  transaction_count: number | null;
  last_status: string | null;
  last_error: string | null;
  pdf_disponivel: boolean;
  owner_email: string | null;
}

export interface ImportResult {
  id: string;
  status: string;
  transaction_count: number;
  error: string | null;
}

export interface Transaction {
  id: string;
  data: string;
  fonte: "cartao" | "conta";
  tipo: "debito" | "credito";
  descricao_original: string;
  grupo: string;
  valor: number;
  ano_mes: string;
  excluido: boolean;
  excluido_motivo: string | null;
  source_file_nome: string;
}

export interface TransactionPage {
  total: number;
  total_valor: number;
  subtotais_mes: Record<string, number>;
  items: Transaction[];
}

export interface SummaryRow {
  chave: string;
  valores: Record<string, number>;
  total: number;
}

export interface CurrentUser {
  id: string;
  email: string;
  role: "admin" | "user";
  status: "pending" | "approved" | "rejected";
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export interface QuarantineEntry {
  id: string;
  filename: string;
  owner_email: string;
  uploaded_at: string | null;
  size_bytes: number;
  pdf_disponivel: boolean;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: "include", ...init });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return req<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const api = {
  // auth
  register: (email: string, password: string) => postJson<CurrentUser>("/api/auth/register", { email, password }),
  login: (email: string, password: string) => postJson<CurrentUser>("/api/auth/login", { email, password }),
  logout: () => req("/api/auth/logout", { method: "POST" }),
  me: () => req<CurrentUser>("/api/auth/me"),

  // files
  listFiles: (todos = false) => req<FileEntry[]>(`/api/files${todos ? "?todos=true" : ""}`),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return req<FileEntry>("/api/files/upload", { method: "POST", body: form });
  },
  importFile: (id: string) => postJson<ImportResult>(`/api/files/${id}/import`, {}),
  purgeFile: (id: string) => postJson<FileEntry>(`/api/files/${id}/purge`, {}),

  // transactions
  listTransactions: (params: Record<string, string | number | boolean | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return req<TransactionPage>(`/api/transactions?${qs.toString()}`);
  },
  listGrupos: () => req<string[]>("/api/transactions/grupos"),
  listMeses: () => req<string[]>("/api/transactions/meses"),
  summary: (por: "grupo" | "fonte", tipo: "debito" | "credito" = "debito") =>
    req<SummaryRow[]>(`/api/summary?por=${por}&tipo=${tipo}`),

  // admin
  adminListUsers: (statusFiltro?: string) =>
    req<AdminUser[]>(`/api/admin/users${statusFiltro ? `?status_filtro=${statusFiltro}` : ""}`),
  adminApproveUser: (id: string) => postJson<AdminUser>(`/api/admin/users/${id}/approve`, {}),
  adminRejectUser: (id: string) => postJson<AdminUser>(`/api/admin/users/${id}/reject`, {}),
  adminListQuarantine: () => req<QuarantineEntry[]>("/api/admin/quarentena"),
  adminPreviewQuarantine: (id: string) => req<{ filename: string; texto: string }>(`/api/admin/quarentena/${id}/preview`),
  adminReprocessQuarantine: () => postJson<{ analisados: number; resolvidos: number }>("/api/admin/quarentena/reprocessar", {}),
};
