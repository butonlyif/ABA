import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, AlertTriangle, Baby, BarChart3, Bot, ChevronLeft, ChevronRight, ClipboardList, FileText, KeyRound, LogOut, Plus, RefreshCw, Search, ShieldCheck, UserCheck, UserX, Users, X } from "lucide-react";
import "./styles.css";
import "./user-management.css";

const API = import.meta.env.VITE_API_URL || "/api/v1";
type Overview = { users: number; children: number; training_sessions: number; reports: number };
type User = { id: string; username: string; role: string; created_at: string; children_count: number; is_active: boolean };
type UserDetail = User & { training_count: number; reports_count: number; expert_name?: string };
type AuditLog = { id: string; actor: string; action: string; resource_id?: string; details: Record<string, unknown>; created_at: string };
type Operations = {
  queue: { mode: string; queued: number; started: number; failed: number; scheduled: number };
  reports: { pending: number; failed: number; completed: number };
  ai_24h: { calls: number; fallbacks: number; prompt_tokens: number; completion_tokens: number; average_latency_ms: number };
  events: { id: string; level: string; category: string; message: string; details: Record<string, string>; created_at: string }[];
};

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = sessionStorage.getItem("aba_admin_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || (response.status === 403 ? "该账户没有管理员权限" : "请求失败"));
  }
  return response.json();
}

function Login({ done }: { done: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      const data = await call<{ access_token: string }>("/auth/login", {
        method: "POST", body: JSON.stringify({ username, password })
      });
      sessionStorage.setItem("aba_admin_token", data.access_token);
      await call("/admin/overview");
      done();
    } catch (err) {
      sessionStorage.removeItem("aba_admin_token");
      setError((err as Error).message);
    }
  };
  return <main className="login"><form onSubmit={submit}>
    <div className="logo"><ShieldCheck/></div><p>星星家庭</p><h1>系统管理后台</h1>
    <label>管理员账户<input value={username} onChange={e => setUsername(e.target.value)}/></label>
    <label>密码<input type="password" value={password} onChange={e => setPassword(e.target.value)}/></label>
    {error && <span className="error">{error}</span>}<button>安全登录</button>
  </form></main>;
}

function Admin() {
  const [ready, setReady] = useState(Boolean(sessionStorage.getItem("aba_admin_token")));
  const [overview, setOverview] = useState<Overview>();
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "user" | "expert" | "disabled">("all");
  const [page, setPage] = useState<"overview" | "users" | "operations" | "audit">("overview");
  const [selected, setSelected] = useState<UserDetail | null>(null);
  const [notice, setNotice] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({ username: "", password: "", role: "user" });
  const [resetPassword, setResetPassword] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [operations, setOperations] = useState<Operations>();
  useEffect(() => {
    if (ready) call<Overview>("/admin/overview")
      .then(setOverview)
      .catch(() => setReady(false));
  }, [ready]);
  useEffect(() => {
    if (!ready) return;
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ limit: "20", offset: String(pageIndex * 20) });
      if (query.trim()) params.set("q", query.trim());
      if (filter === "user" || filter === "expert") params.set("role", filter);
      if (filter === "disabled") params.set("active", "false");
      call<{ total: number; items: User[] }>(`/admin/users?${params}`)
        .then(result => { setUsers(result.items); setTotal(result.total); })
        .catch(() => setReady(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [ready, query, filter, pageIndex, refreshKey]);
  useEffect(() => {
    if (ready && page === "audit") call<{ items: AuditLog[] }>("/admin/audit-logs").then(result => setAuditLogs(result.items));
  }, [ready, page, refreshKey]);
  useEffect(() => {
    if (ready && page === "operations") call<Operations>("/admin/operations").then(setOperations);
  }, [ready, page, refreshKey]);
  if (!ready) return <Login done={() => setReady(true)}/>;
  const filtered = users;
  const updateRole = async (user: User, role: string) => {
    try {
      await call(`/admin/users/${user.id}/role?role=${role}`, { method: "PATCH" });
      setUsers(items => items.map(item => item.id === user.id ? { ...item, role } : item));
      if (selected?.id === user.id) setSelected({ ...selected, role });
      setNotice("角色已更新");
    } catch (err) { setNotice((err as Error).message); }
  };
  const openUser = async (user: User) => setSelected(await call<UserDetail>(`/admin/users/${user.id}`));
  const updateStatus = async (user: User, active: boolean) => {
    try {
      await call(`/admin/users/${user.id}/status?active=${active}`, { method: "PATCH" });
      setUsers(items => items.map(item => item.id === user.id ? { ...item, is_active: active } : item));
      if (selected?.id === user.id) setSelected({ ...selected, is_active: active });
      setNotice(active ? "账户已恢复" : "账户已停用，刷新令牌已撤销");
    } catch (err) { setNotice((err as Error).message); }
  };
  const createUser = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await call("/admin/users", { method: "POST", body: JSON.stringify(newUser) });
      setShowCreate(false);
      setNewUser({ username: "", password: "", role: "user" });
      setRefreshKey(value => value + 1);
      setNotice("新账户已创建");
    } catch (err) { setNotice((err as Error).message); }
  };
  const changePassword = async () => {
    if (!selected || resetPassword.length < 12) return;
    try {
      await call(`/admin/users/${selected.id}/password`, { method: "PATCH", body: JSON.stringify({ password: resetPassword }) });
      setResetPassword("");
      setNotice("密码已重置，原登录状态已撤销");
    } catch (err) { setNotice((err as Error).message); }
  };
  const actionLabels: Record<string, string> = {
    "admin.user.created": "创建账户", "admin.user.role_changed": "修改角色",
    "admin.user.status_changed": "修改账户状态", "admin.user.password_reset": "重置密码"
  };
  const retryReport = async (reportId: string) => {
    try {
      await call(`/admin/reports/${reportId}/retry`, { method: "POST" });
      setNotice("报告已重新进入任务队列");
      setRefreshKey(value => value + 1);
    } catch (err) { setNotice((err as Error).message); }
  };
  return <main className="admin">
    <aside><div><ShieldCheck/><strong>星星家庭</strong><small>系统管理中心</small></div>
      <nav><button className={page === "overview" ? "active" : ""} onClick={() => setPage("overview")}><BarChart3/>业务总览</button><button className={page === "users" ? "active" : ""} onClick={() => setPage("users")}><Users/>用户管理</button><button className={page === "operations" ? "active" : ""} onClick={() => setPage("operations")}><Activity/>运行监控</button><button className={page === "audit" ? "active" : ""} onClick={() => setPage("audit")}><ClipboardList/>操作审计</button></nav>
      <button className="logout" onClick={() => { sessionStorage.clear(); setReady(false); }}><LogOut/>退出</button>
    </aside>
    <section>
      <header><div><p>管理员工作台</p><h1>{page === "overview" ? "业务总览" : page === "users" ? "用户管理" : page === "operations" ? "运行监控" : "操作审计"}</h1></div><span>专家咨询在手机专家工作台处理</span></header>
      {notice && <div className="notice" onClick={() => setNotice("")}>{notice}</div>}
      {page === "overview" ? <><div className="stats">
        <article><Users/><div><strong>{overview?.users ?? "—"}</strong><span>注册用户</span></div></article>
        <article><Baby/><div><strong>{overview?.children ?? "—"}</strong><span>孩子档案</span></div></article>
        <article><BarChart3/><div><strong>{overview?.training_sessions ?? "—"}</strong><span>训练记录</span></div></article>
        <article><FileText/><div><strong>{overview?.reports ?? "—"}</strong><span>进展报告</span></div></article>
      </div><div className="overview-guide"><Users/><div><h2>账户与权限集中管理</h2><p>前往“用户管理”查看详情、分配角色或停用账户。管理员不处理专家咨询内容。</p></div><button onClick={() => setPage("users")}>进入用户管理 <ChevronRight/></button></div></> : page === "users" ? <div className="panel">
        <div className="panel-head"><div><h2>用户账户</h2><p>查看用户信息，并区分家长、专家和管理员</p></div>
          <div className="panel-tools"><button className="create-button" onClick={() => setShowCreate(true)}><Plus/>新建账户</button><button title="刷新" onClick={() => setRefreshKey(value => value + 1)}><RefreshCw/></button><label><Search/><input placeholder="搜索用户名" value={query} onChange={e => { setQuery(e.target.value); setPageIndex(0); }}/></label></div>
        </div>
        <div className="filters"><button className={filter === "all" ? "active" : ""} onClick={() => { setFilter("all"); setPageIndex(0); }}>全部</button><button className={filter === "user" ? "active" : ""} onClick={() => { setFilter("user"); setPageIndex(0); }}>家长</button><button className={filter === "expert" ? "active" : ""} onClick={() => { setFilter("expert"); setPageIndex(0); }}>专家</button><button className={filter === "disabled" ? "active" : ""} onClick={() => { setFilter("disabled"); setPageIndex(0); }}>已停用</button><span>共 {total} 个账户</span></div>
        <table><thead><tr><th>用户名</th><th>状态</th><th>角色</th><th>孩子档案</th><th>注册日期</th><th></th></tr></thead>
          <tbody>{filtered.map(user => <tr key={user.id}>
            <td><strong>{user.username}</strong><small>{user.id.slice(0, 8)}</small></td>
            <td><span className={`status ${user.is_active ? "active" : "disabled"}`}>{user.is_active ? "正常" : "已停用"}</span></td>
            <td><select value={user.role} onChange={e => updateRole(user, e.target.value)}>
              <option value="user">家长</option><option value="expert">专家</option><option value="admin">管理员</option>
            </select></td>
            <td>{user.children_count}</td><td>{new Date(user.created_at).toLocaleDateString("zh-CN")}</td>
            <td><button className="detail-button" onClick={() => openUser(user)}>详情 <ChevronRight/></button></td>
          </tr>)}</tbody>
        </table>
        <div className="pagination"><button disabled={pageIndex === 0} onClick={() => setPageIndex(value => value - 1)}><ChevronLeft/>上一页</button><span>第 {pageIndex + 1} 页</span><button disabled={(pageIndex + 1) * 20 >= total} onClick={() => setPageIndex(value => value + 1)}>下一页<ChevronRight/></button></div>
      </div> : page === "operations" ? <div className="operations">
        <div className="operations-head"><div><h2>服务运行状态</h2><p>只记录运行指标和错误类型，不记录用户提问正文。</p></div><button onClick={() => setRefreshKey(value => value + 1)}><RefreshCw/>刷新</button></div>
        <div className="ops-grid">
          <article><Activity/><span>报告队列</span><strong>{operations?.queue.queued ?? "—"}</strong><small>{operations?.queue.mode === "redis" ? `处理中 ${operations.queue.started} · 重试等待 ${operations.queue.scheduled}` : "本地开发模式"}</small></article>
          <article><FileText/><span>报告任务</span><strong>{operations?.reports.pending ?? "—"}</strong><small>失败 {operations?.reports.failed ?? 0} · 完成 {operations?.reports.completed ?? 0}</small></article>
          <article><Bot/><span>AI 调用（24小时）</span><strong>{operations?.ai_24h.calls ?? "—"}</strong><small>降级 {operations?.ai_24h.fallbacks ?? 0} · 平均 {operations?.ai_24h.average_latency_ms ?? 0}ms</small></article>
          <article><BarChart3/><span>AI Token（24小时）</span><strong>{((operations?.ai_24h.prompt_tokens ?? 0) + (operations?.ai_24h.completion_tokens ?? 0)).toLocaleString()}</strong><small>输入 {operations?.ai_24h.prompt_tokens ?? 0} · 输出 {operations?.ai_24h.completion_tokens ?? 0}</small></article>
        </div>
        <div className="panel event-panel"><div className="panel-head"><div><h2>最近异常</h2><p>报告失败可由管理员安全重试</p></div></div>
          <div className="event-list">{operations?.events.length ? operations.events.map(item => <article key={item.id}><span><AlertTriangle/></span><div><strong>{item.message}</strong><p>{item.category} · {item.details.error_type || "运行异常"}</p></div><time>{new Date(item.created_at).toLocaleString("zh-CN")}</time>{item.category === "report" && item.details.report_id ? <button onClick={() => retryReport(item.details.report_id)}>重新生成</button> : null}</article>) : <p className="empty-audit">暂无运行异常</p>}</div>
        </div>
      </div> : <div className="panel audit-panel"><div className="panel-head"><div><h2>管理员操作记录</h2><p>用于追踪账户创建、权限、状态和密码变更</p></div><button className="audit-refresh" onClick={() => setRefreshKey(value => value + 1)}><RefreshCw/>刷新</button></div><div className="audit-list">{auditLogs.length ? auditLogs.map(item => <article key={item.id}><span><ClipboardList/></span><div><strong>{actionLabels[item.action] || item.action}</strong><p>{item.actor} · 用户 {item.resource_id?.slice(0, 8) || "—"}</p></div><time>{new Date(item.created_at).toLocaleString("zh-CN")}</time></article>) : <p className="empty-audit">暂无管理员操作记录</p>}</div></div>}
      {selected && <div className="drawer-backdrop" onClick={() => setSelected(null)}><aside className="user-drawer" onClick={e => e.stopPropagation()}>
        <button className="drawer-close" onClick={() => setSelected(null)}><X/></button>
        <div className="drawer-avatar">{selected.username.slice(0, 1)}</div><p className="eyebrow">用户详情</p><h2>{selected.username}</h2>
        <span className={`status ${selected.is_active ? "active" : "disabled"}`}>{selected.is_active ? "账户正常" : "账户已停用"}</span>
        <dl><div><dt>用户 ID</dt><dd>{selected.id}</dd></div><div><dt>注册时间</dt><dd>{new Date(selected.created_at).toLocaleString("zh-CN")}</dd></div><div><dt>孩子档案</dt><dd>{selected.children_count}</dd></div><div><dt>训练记录</dt><dd>{selected.training_count}</dd></div><div><dt>进展报告</dt><dd>{selected.reports_count}</dd></div><div><dt>签约专家</dt><dd>{selected.expert_name || "未选择"}</dd></div></dl>
        <label className="drawer-role">账户角色<select value={selected.role} onChange={e => updateRole(selected, e.target.value)}><option value="user">家长</option><option value="expert">专家</option><option value="admin">管理员</option></select></label>
        <div className="password-reset"><label><KeyRound/>重置密码</label><div><input type="password" placeholder="至少 12 位新密码" value={resetPassword} onChange={e => setResetPassword(e.target.value)}/><button disabled={resetPassword.length < 12} onClick={changePassword}>确认重置</button></div></div>
        <button className={`status-action ${selected.is_active ? "disable" : "enable"}`} onClick={() => updateStatus(selected, !selected.is_active)}>{selected.is_active ? <><UserX/>停用该账户</> : <><UserCheck/>恢复该账户</>}</button>
      </aside></div>}
      {showCreate && <div className="drawer-backdrop" onClick={() => setShowCreate(false)}><form className="create-dialog" onSubmit={createUser} onClick={e => e.stopPropagation()}><button type="button" className="drawer-close" onClick={() => setShowCreate(false)}><X/></button><div className="drawer-avatar"><Plus/></div><p className="eyebrow">账户管理</p><h2>创建新账户</h2><label>用户名<input required minLength={2} value={newUser.username} onChange={e => setNewUser({...newUser, username:e.target.value})}/></label><label>初始密码<input required type="password" minLength={12} placeholder="至少 12 位" value={newUser.password} onChange={e => setNewUser({...newUser, password:e.target.value})}/></label><label>账户角色<select value={newUser.role} onChange={e => setNewUser({...newUser, role:e.target.value})}><option value="user">家长</option><option value="expert">专家</option><option value="admin">管理员</option></select></label><button className="create-submit">创建账户</button></form></div>}
    </section>
  </main>;
}

createRoot(document.getElementById("root")!).render(<Admin/>);
