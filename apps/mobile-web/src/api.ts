const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const API_ORIGIN = API_URL.startsWith("http") ? new URL(API_URL).origin : "";

function uuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return "id-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

export type Child = {
  id: string;
  name: string;
  birth_date?: string;
  diagnosis?: string;
  goals?: string;
  is_current: boolean;
  status_snapshot?: {
    domains?: Record<string, number>;
    overall_level?: number;
    trend?: { label: string; delta: number };
    updated_at?: string;
    source?: string;
  };
  last_report_at?: string;
  avatar_url?: string | null;
  avatar_seed?: string | null;
};

export type Task = {
  id: string;
  child_id: string;
  name: string;
  description?: string;
  category: string;
  status: string;
  sort_order?: number;
  is_daily?: boolean;
};

export type Report = {
  id: string;
  child_id: string;
  status: string;
  title: string;
  summary: string;
  content: any;
  trend?: string | null;
  trend_detail?: { avg_before: number; avg_after: number; delta: number } | null;
  file_url?: string | null;
  created_at: string;
};

export type SkillTemplate = {
  name: string;
  category: string;
  description: string;
  level: number;
  group: string;
  flashcard_category?: string | null;
};

export type SkillCatalog = {
  domain: string;
  count: number;
  skills: SkillTemplate[];
};

export type Session = {
  id: string;
  skill_name: string;
  trials: string[];
  percentage: number;
  status: string;
};

export type Expert = {
  id: string; name: string; title: string; specialties: string[]; bio: string;
  credentials: string; avatar_url?: string; accepting_clients: boolean; client_count: number;
};
export type ExpertProfile = {
  display_name: string; title: string; specialties: string[]; bio: string; credentials: string;
  avatar_url?: string; accepting_clients: boolean; max_clients: number;
};
export type ExpertMessage = { id: string; sender: "client" | "expert"; content: string; created_at: string };
export type ExpertClient = { id: string; name: string; unread: number; latest: string };

type Tokens = { access_token: string; refresh_token: string };

const tokenStore = {
  get access() { return sessionStorage.getItem("aba_access"); },
  get refresh() { return localStorage.getItem("aba_refresh"); },
  set(tokens: Tokens) {
    sessionStorage.setItem("aba_access", tokens.access_token);
    localStorage.setItem("aba_refresh", tokens.refresh_token);
  },
  clear() {
    sessionStorage.removeItem("aba_access");
    localStorage.removeItem("aba_refresh");
  }
};

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (tokenStore.access) headers.set("Authorization", `Bearer ${tokenStore.access}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retry && tokenStore.refresh) {
    const refreshed = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokenStore.refresh })
    });
    if (refreshed.ok) {
      tokenStore.set(await refreshed.json());
      return request<T>(path, init, false);
    }
    tokenStore.clear();
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(error.detail || "请求失败");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  tokenStore,
  register: (username: string, password: string) =>
    request<Tokens>("/auth/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  login: (username: string, password: string) =>
    request<Tokens>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: () => request<{ id: string; username: string; role: string }>("/auth/me"),
  children: () => request<Child[]>("/children"),
  createChild: (body: Partial<Child>) => request<Child>("/children", { method: "POST", body: JSON.stringify(body) }),
  setCurrentChild: (childId: string) => request<Child>(`/children/${childId}/current`, { method: "PATCH" }),
  importRecord: async (childId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_URL}/children/${childId}/upload-record`, {
      method: "POST",
      headers: tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {},
      body: form
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "上传失败" }));
      throw new Error(error.detail || "上传失败");
    }
    return response.json() as Promise<Child>;
  },
  importRecordText: (childId: string, text: string) =>
    request<Child>(`/children/${childId}/import-record`, { method: "POST", body: JSON.stringify({ text }) }),
  uploadChildAvatar: async (childId: string, file: File) => {
    const form = new FormData();
    form.append("avatar", file);
    const response = await fetch(`${API_URL}/children/${childId}/avatar`, {
      method: "POST",
      headers: tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {},
      body: form
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "头像上传失败" }));
      throw new Error(error.detail || "头像上传失败");
    }
    return response.json() as Promise<Child>;
  },
  removeChildAvatar: (childId: string) =>
    request<Child>(`/children/${childId}/avatar`, { method: "DELETE" }),
  regenerateChildAvatar: (childId: string) =>
    request<Child>(`/children/${childId}/avatar/regenerate`, { method: "POST" }),
  tasks: (childId: string) => request<Task[]>(`/tasks?child_id=${childId}`),
  deleteTask: (taskId: string) => request<void>(`/tasks/${taskId}`, { method: "DELETE" }),
  createTask: (body: { child_id: string; name: string; description?: string; category: string; is_daily?: boolean }) =>
    request<Task>("/tasks", { method: "POST", body: JSON.stringify(body) }),
  reorderTasks: (childId: string, order: { id: string; sort_order: number }[]) =>
    request<Task[]>("/tasks/reorder", { method: "PATCH", body: JSON.stringify({ child_id: childId, order }) }),
  skillTemplates: () => request<SkillCatalog[]>("/training/templates"),
  questions: () => request<{ items: { id: string; domain: string; domain_name: string; level: number; text: string }[] }>("/assessments/questions"),
  submitAssessment: (childId: string, answers: Record<string, number>, idempotencyKey: string) =>
    request("/assessments", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ child_id: childId, answers })
    }),
  createSession: (childId: string, task: Task) =>
    request<Session>("/training-sessions", {
      method: "POST",
      headers: { "Idempotency-Key": uuid() },
      body: JSON.stringify({ child_id: childId, task_id: task.id, skill_name: task.name })
    }),
  addTrial: (sessionId: string, result: string) =>
    request<Session>(`/training-sessions/${sessionId}/trials`, { method: "POST", body: JSON.stringify({ result }) }),
  activeSession: (childId: string) =>
    request<Session | null>(`/training-sessions/active?child_id=${childId}`),
  undoTrial: (sessionId: string) =>
    request<Session>(`/training-sessions/${sessionId}/trials/latest`, { method: "DELETE" }),
  finishSession: (sessionId: string) =>
    request<Session>(`/training-sessions/${sessionId}/finish`, { method: "POST" }),
  flashcards: () => request<{ groups: { group: string; categories: { name: string; count: number }[] }[] }>("/flashcards"),
  flashcardImage: async (category: string, index: number) => {
    const response = await fetch(`${API_URL}/flashcards/${encodeURIComponent(category)}/${index}`, {
      headers: tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}
    });
    if (!response.ok) throw new Error("卡片加载失败");
    return URL.createObjectURL(await response.blob());
  },
  progress: (childId: string) => request<any>(`/progress?child_id=${childId}`),
  reports: (childId: string) => request<any[]>(`/reports?child_id=${childId}`),
  generateReport: (childId: string) =>
    request<any>("/reports", { method: "POST", body: JSON.stringify({ child_id: childId }) }),
  downloadReport: async (reportId: string) => {
    const fetchFile = () => fetch(`${API_URL}/reports/${reportId}/file`, {
      headers: tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {}
    });
    let response = await fetchFile();
    if (response.status === 401 && tokenStore.refresh) {
      await request("/auth/me");
      response = await fetchFile();
    }
    if (!response.ok) throw new Error("报告下载失败");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `ABA训练报告-${new Date().toISOString().slice(0, 10)}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  },
  publicChat: (message: string) =>
    request<{ answer: string }>("/chat/public", { method: "POST", body: JSON.stringify({ message }) }),
  chat: (message: string, childId?: string) =>
    request<{ answer: string; sources: { title: string }[] }>("/chat", { method: "POST", body: JSON.stringify({ message, child_id: childId }) }),
  chatStream: async (message: string, childId: string | undefined, onChunk: (text: string) => void) => {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {})
      },
      body: JSON.stringify({ message, child_id: childId })
    });
    if (!response.ok || !response.body) throw new Error("流式回答暂时不可用");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    let answer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      const lines = pending.split("\n");
      pending = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const part = line.slice(6);
        if (part === "[DONE]") continue;
        answer += part;
        onChunk(answer);
      }
    }
    return answer;
  },
  chatMessages: (product: "aba" | "coach") =>
    request<{ id: string; role: string; content: string; sources: { title: string }[] }[]>(`/chat/messages?product=${product}`),
  clearChatMessages: (product: "aba" | "coach") =>
    request<{ deleted: number }>(`/chat/messages?product=${product}`, { method: "DELETE" }),
  exportChat: async (product: "aba" | "coach") => {
    const msgs = await request<{ id: string; role: string; content: string; sources?: { title: string }[] }[]>(`/chat/messages?product=${product}`);
    const lines = msgs.map(m => {
      const role = m.role === "user" ? "你" : "AI";
      let text = `[${role}]\n${m.content}`;
      if (m.sources?.length) text += `\n[参考: ${m.sources.map(s => s.title).join(", ")}]`;
      return text;
    });
    const blob = new Blob([`ABA 智能问答记录\n导出时间: ${new Date().toLocaleString("zh-CN")}\n${"─".repeat(40)}\n\n${lines.join("\n\n")}`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `ABA问答记录_${new Date().toISOString().slice(0,10)}.txt`; a.click();
    URL.revokeObjectURL(url);
  },
  experts: () => request<{ items: Expert[]; selected_expert_id?: string }>("/experts"),
  selectExpert: (expertId: string) =>
    request("/experts/selection", { method: "PUT", body: JSON.stringify({ expert_id: expertId }) }),
  releaseExpert: () => request("/experts/selection", { method: "DELETE" }),
  notifications: () => request<{ expert_unread: number }>("/notifications"),
  askExpert: (content: string) =>
    request<ExpertMessage>("/expert/questions", { method: "POST", body: JSON.stringify({ content }) }),
  expertConversation: () => request<{ items: ExpertMessage[] }>("/expert/conversation"),
  expertClients: () => request<{ items: ExpertClient[] }>("/expert/clients"),
  expertProfile: () => request<ExpertProfile>("/expert/profile"),
  saveExpertProfile: (body: ExpertProfile) =>
    request<ExpertProfile>("/expert/profile", { method: "PUT", body: JSON.stringify(body) }),
  uploadExpertAvatar: async (file: File) => {
    const form = new FormData();
    form.append("avatar", file);
    const response = await fetch(`${API_URL}/expert/profile/avatar`, {
      method: "POST",
      headers: tokenStore.access ? { Authorization: `Bearer ${tokenStore.access}` } : {},
      body: form
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "头像上传失败" }));
      throw new Error(error.detail || "头像上传失败");
    }
    return response.json() as Promise<{ avatar_url: string }>;
  },
  assetUrl: (path?: string) => path ? `${API_ORIGIN}${path}` : "",
  expertClientMessages: (clientId: string) =>
    request<{ items: ExpertMessage[] }>(`/expert/clients/${clientId}/messages`),
  replyToClient: (clientId: string, content: string) =>
    request<ExpertMessage>(`/expert/clients/${clientId}/reply`, { method: "POST", body: JSON.stringify({ content }) }),
  closeExpertConsultation: (clientId: string) =>
    request<{ closed: boolean }>(`/expert/clients/${clientId}/close`, { method: "POST" }),
  coachChat: (message: string) =>
    request<{ answer: string }>("/coach/chat", { method: "POST", body: JSON.stringify({ message }) }),
  coachOverview: () => request<{ mood_today: string | null; journal_count: number; growth_stage: string }>("/coach/overview"),
  moods: () => request<{ id: string; mood: string; intensity: number; note: string | null; entry_date: string }[]>("/coach/moods"),
  saveMood: (payload: { mood: string; intensity: number; note?: string }) => request("/coach/moods", { method: "POST", body: JSON.stringify(payload) }),
  journals: () => request<{ id: string; content: string; created_at: string }[]>("/coach/journals"),
  saveJournal: (content: string) => request("/coach/journals", { method: "POST", body: JSON.stringify({ content, prompt: "今天有没有一个瞬间，你觉得自己其实做得还不错？" }) }),
  coachArticles: (q?: string) => request<{ items: { id: string; title: string; category: string; subcategory: string; level: string; read_time: string; summary: string }[] }>(`/coach/articles${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  coachCategories: () => request<{ items: { id: string; name: string; icon: string; desc: string; color: string; count: number; children: { id: string; name: string; icon: string; desc: string; count: number }[] }[] }>("/coach/categories"),
  coachArticle: (id: string) => request<{ id: string; title: string; category: string; subcategory: string; summary: string; content: string; read_time: string; related: { id: string; title: string; subcategory: string; read_time: string }[] }>(`/coach/articles/${id}`),
  coachWeeklyReport: (week_offset: number = 0) => request<{ week_start: string; week_end: string; mood_count: number; journal_count: number; chat_count: number; content: string; provider: string; fallback: boolean }>(`/coach/weekly-report?week_offset=${week_offset}`, { method: "POST" })
};
