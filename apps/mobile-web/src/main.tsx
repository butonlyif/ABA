import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Baby, BarChart3, BookOpen, Camera, Check, ChevronLeft, ChevronRight, CircleUserRound, Download, Dumbbell, HeartHandshake, Home, Inbox, MessageCircleHeart, PenLine, Play, Plus, RefreshCw, Send, ShieldCheck, Shuffle, Smile, Sparkles, Sprout, Target, UserRoundCheck, WifiOff } from "lucide-react";
import { api, Child, ExpertClient, ExpertProfile, Report, Session, SkillTemplate, Task } from "./api";
import "./styles.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 20_000 } } });
type Tab = "home" | "child" | "training" | "progress" | "me";
type ProductMode = "aba" | "coach";

// ACT 六步法：以一个问题为单位发起的 session
type ActStepKey = "awareness" | "acceptance" | "defusion" | "present" | "values" | "action";
type ActSession = {
  id: string;
  problem: string;
  steps: Record<ActStepKey, { reflection: string; completedAt: string | null }>;
  resolution: { solved: boolean | null; note: string; updatedAt: string | null };
  status: "in_progress" | "completed";
  createdAt: string;
  updatedAt: string;
};

const ACT_STEPS: { key: ActStepKey; name: string; prompt: string; placeholder: string }[] = [
  { key: "awareness", name: "觉察", prompt: "此刻，这件事让你感受到什么？", placeholder: "比如：胸口发紧、想躲起来、脑子停不下来……" },
  { key: "acceptance", name: "接纳", prompt: "允许这种感觉存在。你可以对它说一句什么？", placeholder: "比如：焦虑，我看到你了，你可以待一会儿。" },
  { key: "defusion", name: "解离", prompt: "如果把这个想法当作一段文字，它在说什么？", placeholder: "把它写下来，然后用一句话把它念出来。" },
  { key: "present", name: "当下", prompt: "把注意力带回身体。此刻你的脚、肩、手在哪里？", placeholder: "选一个当下的身体感觉，描述一下。" },
  { key: "values", name: "价值", prompt: "如果问题不再存在，你想成为什么样的家长？", placeholder: "写一句话，作为你行动的方向。" },
  { key: "action", name: "行动", prompt: "今天可以做的一件 2 分钟小事是什么？", placeholder: "具体到可以马上开始，做完回到原问题。" }
];

function newActSession(problem: string): ActSession {
  const now = new Date().toISOString();
  return {
    id: (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`),
    problem,
    steps: ACT_STEPS.reduce((acc, step) => {
      acc[step.key] = { reflection: "", completedAt: null };
      return acc;
    }, {} as ActSession["steps"]),
    resolution: { solved: null, note: "", updatedAt: null },
    status: "in_progress",
    createdAt: now,
    updatedAt: now
  };
}

// ─── 情绪多维记录 ───
type MoodDetail = {
  emotions: string[];
  intensity: number;
  triggers: string[];
  body: string[];
  coping: string;
};
const MOOD_FAMILIES: { group: string; items: { key: string; label: string }[] }[] = [
  { group: "稳定", items: [{ key: "calm", label: "平静" }, { key: "relaxed", label: "放松" }, { key: "grateful", label: "感激" }, { key: "warm", label: "温暖" }] },
  { group: "正向活力", items: [{ key: "joy", label: "愉悦" }, { key: "excited", label: "兴奋" }, { key: "hopeful", label: "有希望" }, { key: "proud", label: "自豪" }] },
  { group: "警觉与不安", items: [{ key: "anxious", label: "焦虑" }, { key: "tense", label: "紧绷" }, { key: "restless", label: "烦躁" }, { key: "overwhelmed", label: "不堪重负" }] },
  { group: "低落与疲惫", items: [{ key: "sad", label: "低落" }, { key: "exhausted", label: "疲惫" }, { key: "empty", label: "空虚" }, { key: "lonely", label: "孤独" }] },
  { group: "压力与愤怒", items: [{ key: "angry", label: "愤怒" }, { key: "frustrated", label: "挫败" }, { key: "ashamed", label: "羞耻" }, { key: "guilty", label: "内疚" }] },
  { group: "迷茫", items: [{ key: "confused", label: "困惑" }, { key: "doubtful", label: "怀疑" }, { key: "numb", label: "麻木" }, { key: "helpless", label: "无助" }] }
];
const TRIGGER_OPTIONS = ["孩子行为", "家庭琐事", "工作", "夫妻关系", "家人期待", "训练过程", "社交场合", "睡眠不足", "自我要求", "经济压力", "健康担忧", "时间不够"];
const BODY_OPTIONS = ["肩膀紧", "心跳快", "胸口闷", "胃部不适", "手心出汗", "手抖", "呼吸急促", "呼吸平稳", "肌肉放松", "全身乏力", "头痛", "面部发烫"];
const INTENSITY_LABELS = ["几乎没感觉", "轻微", "中等", "较强", "非常强烈"];

function flattenMoods() {
  const map: Record<string, string> = {};
  for (const f of MOOD_FAMILIES) for (const i of f.items) map[i.key] = i.label;
  return map;
}
const MOOD_LABEL_MAP = flattenMoods();

function parseMoodDetail(note: string | null | undefined): MoodDetail | null {
  if (!note) return null;
  try {
    const obj = JSON.parse(note);
    if (obj && Array.isArray(obj.emotions)) return obj as MoodDetail;
  } catch { /* ignore legacy */ }
  return null;
}

function Auth({ mode, setMode, onDone }: { mode: ProductMode; setMode: (mode: ProductMode) => void; onDone: () => void }) {
  const [signup, setSignup] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      const tokens = await (signup ? api.register(username, password) : api.login(username, password));
      api.tokenStore.set(tokens);
      onDone();
    } catch (err) { setError((err as Error).message); }
  };
  return <main className="auth">
    <div className="brand-mark"><Sparkles size={30}/></div>
    <p className="eyebrow">星星家庭</p>
    <h1 style={{fontSize: '2em', marginBottom: '4px'}}>你好，我是<strong style={{color: 'var(--purple)'}}>皮特</strong></h1>
    <p className="muted" style={{fontSize: '0.9em'}}>皮特 - ABA 智能助手 · 让每一次陪伴都看得见成长</p>
    <form className="auth-card" onSubmit={submit}>
      <p className="entry-label">选择要进入的空间</p>
      <div className="entry-grid">
        <button type="button" className={`entry-option aba-entry ${mode === "aba" ? "selected" : ""}`} onClick={() => setMode("aba")}>
          <span className="entry-icon"><Target /></span>
          <span><strong style={{fontSize: '1.1em'}}>皮特</strong><small>ABA 智能助手 · 孩子档案 · 评估 · 训练</small></span>
          <Check className="entry-check" />
        </button>
        <button type="button" className={`entry-option coach-entry ${mode === "coach" ? "selected" : ""}`} onClick={() => setMode("coach")}>
          <span className="entry-icon"><HeartHandshake /></span>
          <span><strong>家长陪伴</strong><small>情绪支持 · 成长练习 · 日记</small></span>
          <Check className="entry-check" />
        </button>
      </div>
      <div className="segment">
        <button type="button" className={!signup ? "active" : ""} onClick={() => setSignup(false)}>登录</button>
        <button type="button" className={signup ? "active" : ""} onClick={() => setSignup(true)}>注册</button>
      </div>
      <label>用户名<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
      <label>密码<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete={signup ? "new-password" : "current-password"} /></label>
      {error && <p className="error">{error}</p>}
      <button className={`primary ${mode === "coach" ? "coach-primary" : ""}`} disabled={username.length < 2 || (signup ? password.length < 8 : password.length < 4)}>
        {signup ? "创建家庭账户" : mode === "coach" ? "进入家长陪伴" : "开始和皮特对话"}
      </button>
      <small>注册即表示同意儿童数据保护与隐私说明</small>
    </form>
  </main>;
}

function EmptyChild({ done }: { done: () => void }) {
  const [name, setName] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const query = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () => {
      const child = await api.createChild({ name, diagnosis });
      // 创建后立刻生成卡通头像
      try { await api.regenerateChildAvatar(child.id); } catch (_) { /* 兜底失败不影响主流程 */ }
      return child;
    },
    onSuccess: () => { query.invalidateQueries({ queryKey: ["children"] }); done(); }
  });
  return <section className="empty-state">
    <div className="round-icon"><Baby /></div>
    <h2>先建立孩子档案</h2>
    <p>只需基础信息，之后可以随时完善。</p>
    <input placeholder="孩子的小名" value={name} onChange={e => setName(e.target.value)} />
    <input placeholder="诊断信息（可选）" value={diagnosis} onChange={e => setDiagnosis(e.target.value)} />
    <button className="primary" onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}><Plus size={18}/> 创建档案</button>
    <small className="muted">创建后系统会自动生成一张卡通头像</small>
  </section>;
}

function ChildAvatar({ child, size = 80, badge = false }: { child: Child; size?: number; badge?: boolean }) {
  const url = child.avatar_url ? api.assetUrl(child.avatar_url) : "";
  // 加上 cache-busting（每次 avatar_url 变化或 uploaded 时间戳变化时重置）
  const bust = React.useMemo(() => `${Date.now().toString(36)}`, [child.avatar_url]);
  const src = url ? `${url}${url.includes("?") ? "&" : "?"}v=${bust}` : "";
  const [errored, setErrored] = useState(false);
  // avatar_url 缺失（移除后）时直接走卡通
  const showImage = Boolean(src) && !errored;
  // 没有 src 或加载失败时显示 fallback（首字母），加载中或加载完成均显示 <img>，
  // 由浏览器原生加载（opacity 始终 1，避免 transition 卡在中间态看不见图）
  return <div className="child-avatar" style={{ width: size, height: size }}>
    {showImage && <img src={src} alt={child.name} onError={() => setErrored(true)} />}
    {!showImage && <span className="child-avatar-fallback">{child.name.slice(0, 1)}</span>}
    {badge && <span className="child-avatar-badge" title="系统自动生成卡通头像">✨</span>}
  </div>;
}

function AvatarUploader({ child }: { child: Child }) {
  const query = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadChildAvatar(child.id, file),
    onSuccess: () => { setError(null); query.invalidateQueries({ queryKey: ["children"] }); },
    onError: (e: Error) => { setError(`上传失败：${e.message}`); }
  });
  const regenerate = useMutation({
    mutationFn: () => api.regenerateChildAvatar(child.id),
    onSuccess: () => { setError(null); query.invalidateQueries({ queryKey: ["children"] }); },
    onError: (e: Error) => { setError(`生成失败：${e.message}`); }
  });
  return <>
    <div className="avatar-uploader">
      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: "none" }} onChange={e => {
        const f = e.target.files?.[0];
        if (f) upload.mutate(f);
        e.target.value = "";
      }} />
      <button className="avatar-mini-btn" onClick={() => fileRef.current?.click()} disabled={upload.isPending} title="上传头像">
        <Camera size={12} />
      </button>
      <button className="avatar-mini-btn" onClick={() => regenerate.mutate()} disabled={regenerate.isPending} title="重新生成卡通">
        <RefreshCw size={12} />
      </button>
    </div>
    {error && <div className="avatar-error" role="alert" onClick={() => setError(null)}>{error}</div>}
  </>;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 9) return "早上好";
  if (h < 12) return "上午好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
}

function HomePage({ child, go }: { child: Child; go: (tab: Tab) => void }) {
  const [helpMode, setHelpMode] = useState<"ai" | "expert">("ai");
  const [message, setMessage] = useState("");
  const { data: history = [], refetch: refetchHistory } = useQuery({ queryKey: ["chat", "aba"], queryFn: () => api.chatMessages("aba") });
  const chat = useMutation({ mutationFn: async () => {
    try { return await api.chatStream(message, child.id, () => refetchHistory()); }
    catch { const r = await api.chat(message, child.id); return r.answer; }
  }, onSuccess: () => {
    setMessage("");
    queryClient.invalidateQueries({ queryKey: ["chat", "aba"] });
  } });
  const clearChat = useMutation({ mutationFn: () => api.clearChatMessages("aba"), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chat", "aba"] }) });
  const { data: expertData } = useQuery({ queryKey: ["experts"], queryFn: api.experts });
  const { data: expertThread } = useQuery({ queryKey: ["expert-conversation"], queryFn: api.expertConversation, enabled: helpMode === "expert" });
  const { data: notificationData } = useQuery({ queryKey: ["notifications"], queryFn: api.notifications, refetchInterval: 10_000 });
  useEffect(() => {
    if (helpMode === "expert" && expertThread) queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [helpMode, expertThread]);
  const selectExpert = useMutation({ mutationFn: api.selectExpert, onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["experts"] });
    queryClient.invalidateQueries({ queryKey: ["expert-conversation"] });
  }});
  const askExpert = useMutation({ mutationFn: () => api.askExpert(message), onSuccess: () => {
    setMessage("");
    queryClient.invalidateQueries({ queryKey: ["expert-conversation"] });
  }});
  const releaseExpert = useMutation({ mutationFn: api.releaseExpert, onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["experts"] });
    queryClient.invalidateQueries({ queryKey: ["expert-conversation"] });
  }});
  return <>
    {/* 紧凑顶栏：问候 + 标题 + 清空 */}
    <header className="home-header">
      <div>
        <p className="eyebrow">{getGreeting()}，家长</p>
        <h1>有什么我可以帮你的？</h1>
      </div>
      {history.length > 0 && <div style={{display:"flex",gap:10,alignItems:"center"}}><button className="text-button" onClick={() => api.exportChat("aba")}><Download size={14}/> 导出</button><button className="text-button clear-chat-btn" onClick={() => clearChat.mutate()} disabled={clearChat.isPending}>清空</button></div>}
    </header>

    {/* 问答主区域 — 占据大部分空间 */}
    <section className="home-chat">
      <div className="help-switch">
        <button className={helpMode === "ai" ? "active" : ""} onClick={() => setHelpMode("ai")}><Sparkles/>问 AI</button>
        <button className={helpMode === "expert" ? "active" : ""} onClick={() => setHelpMode("expert")}><UserRoundCheck/>问专家{Boolean(notificationData?.expert_unread) && <b>{notificationData!.expert_unread}</b>}</button>
      </div>
      {helpMode === "ai" ? <>
        <div className="chat-thread-header">
          <div className="section-title"><span><Sparkles size={18}/> 皮特在这里</span><small>MiniMax 驱动</small></div>
        </div>
        <div className="chat-thread home-thread">
          {history.length === 0 && <div className="bubble">你好，我是<strong>皮特</strong>！我可以和你一起分析孩子的行为，也能给出适合家庭练习的具体步骤。</div>}
          {history.map(item => <div className={`chat-bubble ${item.role}`} key={item.id}>
            <p>{item.content}</p>
            {item.role === "assistant" && item.sources?.length > 0 && <div className="chat-sources">{item.sources.map(s => <span key={s.title}>{s.title}</span>)}</div>}
          </div>)}
          {chat.isPending && <div className="chat-bubble assistant"><p>正在查找知识库并整理回答…</p></div>}
        </div>
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="描述一个具体场景…" onKeyDown={e => { if (e.key === "Enter" && message.trim()) chat.mutate(); }} /><button onClick={() => chat.mutate()} disabled={!message.trim() || chat.isPending}>发送</button></div>
      </> : <>
        <div className="section-title"><span><UserRoundCheck size={18}/> 专家支持</span><small>人工回复</small></div>
        {!expertData?.selected_expert_id && <div className="expert-picker">
          <p>选择一位专家，后续问题会由他持续跟进。</p>
          {expertData?.items.map(expert => <button key={expert.id} onClick={() => selectExpert.mutate(expert.id)}>
            <span className="expert-avatar">{expert.avatar_url ? <img src={api.assetUrl(expert.avatar_url)} alt={expert.name}/> : expert.name.slice(0, 1)}</span><span><strong>{expert.name}</strong><small>{expert.title}{expert.specialties.length ? ` · ${expert.specialties.join("、")}` : ""}</small><em>{expert.bio || (expert.accepting_clients ? "正在接收新客户" : "暂停接收新客户")}</em></span><ChevronRight/>
          </button>)}
          {!expertData?.items.length && <p className="muted">暂时没有可选专家，请稍后再试。</p>}
        </div>}
        {expertData?.selected_expert_id && <div className="expert-thread">
          <div className="selected-expert-bar"><span>当前专家：{expertData.items.find(item => item.id === expertData.selected_expert_id)?.name || "已选择"}</span><button onClick={() => releaseExpert.mutate()}>更换专家</button></div>
          {expertThread?.items.length ? expertThread.items.map(item => <div className={`expert-bubble ${item.sender}`} key={item.id}>{item.content}<small>{item.sender === "client" ? "我" : "专家"}</small></div>) : <div className="bubble">你好，把你的具体问题发给我，我会在工作台中回复你。</div>}
          <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="向专家描述你的问题…" /><button onClick={() => askExpert.mutate()} disabled={!message.trim() || askExpert.isPending}>发送</button></div>
        </div>}
      </>}
    </section>

    {/* 底部快捷入口（紧凑） */}
    <nav className="home-nav">
      <button onClick={() => go("child")}><Target/><span>孩子<small>评估与状态</small></span></button>
      <button onClick={() => go("training")}><Dumbbell/><span>训练<small>今日任务</small></span></button>
      <button onClick={() => go("progress")}><BarChart3/><span>进展<small>成长趋势</small></span></button>
    </nav>
  </>;
}

function ChildStatusCard({ snapshot, lastReportAt }: { snapshot: NonNullable<Child["status_snapshot"]> | null | undefined; lastReportAt?: string }) {
  if (!snapshot || !snapshot.domains || Object.keys(snapshot.domains).length === 0) {
    return (
      <section className="child-status status-empty">
        <p className="eyebrow">能力状态</p>
        <p className="muted small" style={{margin:"4px 0 0"}}>尚未评估或导入病例。<a onClick={() => { const el = document.querySelector(".record-import"); el?.scrollIntoView({ behavior: "smooth" }); }} style={{color:"var(--purple)",cursor:"pointer",fontWeight:600}}>导入病例</a> 或完成下方评估。</p>
      </section>
    );
  }
  const domains = snapshot.domains || {};
  const entries = Object.entries(domains).sort((a, b) => b[1] - a[1]);
  const trend = snapshot.trend;
  const trendLabel = trend?.label === "progress" ? "进步中" : trend?.label === "regression" ? "需关注" : "稳定";
  const trendClass = trend?.label === "progress" ? "trend-up" : trend?.label === "regression" ? "trend-down" : "trend-stable";
  const updated = snapshot.updated_at ? new Date(snapshot.updated_at).toLocaleDateString("zh-CN") : "";
  return (
    <section className="child-status">
      <div className="status-header">
        <p className="eyebrow">目前状态</p>
        {trend && <span className={`trend-badge ${trendClass}`}>
          {trendLabel}{trend.delta !== 0 ? ` ${trend.delta > 0 ? "+" : ""}${trend.delta}%` : ""}
        </span>}
      </div>
      <div className="status-domains">
        {entries.map(([domain, score]) => (
          <div className="domain-row" key={domain}>
            <span className="domain-name">{domain}</span>
            <div className="domain-bar"><span style={{ width: `${score}%` }} /></div>
            <span className="domain-score">{Math.round(score)}</span>
          </div>
        ))}
      </div>
      <p className="status-meta">更新于 {updated}{snapshot.source === "assessment" ? " · 评估" : snapshot.source === "report" ? " · 周报" : ""}</p>
    </section>
  );
}

function RecordImport({ childId }: { childId: string }) {
  const [mode, setMode] = useState<null | "file" | "text">(null);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const import_file = useMutation({
    mutationFn: (file: File) => api.importRecord(childId, file),
    onSuccess: () => { setMsg("病例导入成功，AI 已分析并更新状态"); setMode(null); queryClient.invalidateQueries({ queryKey: ["children"] }); },
    onError: (e: Error) => setMsg(`导入失败：${e.message}`),
  });
  const import_text = useMutation({
    mutationFn: () => api.importRecordText(childId, text),
    onSuccess: () => { setMsg("病例分析完成，状态已更新"); setText(""); setMode(null); queryClient.invalidateQueries({ queryKey: ["children"] }); },
    onError: (e: Error) => setMsg(`分析失败：${e.message}`),
  });
  return (
    <section className="record-import">
      <div className="record-head">
        <p className="eyebrow">导入病例</p>
        {!mode && <button className="text-button" onClick={() => setMode("file")}>上传文件</button>}
        {!mode && <button className="text-button" onClick={() => setMode("text")}>粘贴文本</button>}
      </div>
      {!mode && <p className="muted small">上传孩子的诊断报告、评估记录或病历（PDF/Word/TXT），AI 会自动分析并生成能力状态。</p>}
      {mode === "file" && <>
        <input ref={fileInput} type="file" accept=".pdf,.doc,.docx,.txt,.md" style={{ display: "none" }} onChange={e => { const f = e.target.files?.[0]; if (f) import_file.mutate(f); }} />
        <button className="secondary" onClick={() => fileInput.current?.click()} disabled={import_file.isPending}>
          {import_file.isPending ? "正在分析…" : "选择病例文件"}
        </button>
        <button className="text-button" onClick={() => setMode(null)}>取消</button>
      </>}
      {mode === "text" && <>
        <textarea className="record-textarea" placeholder="粘贴病例内容、诊断报告或评估描述…" value={text} onChange={e => setText(e.target.value)} rows={4} />
        <div style={{ display: "flex", gap: 8 }}>
          <button className="primary" disabled={!text.trim() || import_text.isPending} onClick={() => import_text.mutate()}>
            {import_text.isPending ? "AI 分析中…" : "分析并更新状态"}
          </button>
          <button className="text-button" onClick={() => setMode(null)}>取消</button>
        </div>
      </>}
      {msg && <p className={`record-msg ${msg.includes("失败") ? "error" : ""}`}>{msg}</p>}
    </section>
  );
}

function ChildPage({ child }: { child: Child }) {
  const { data: allChildren = [] } = useQuery({ queryKey: ["children"], queryFn: api.children });
  const [showAdd, setShowAdd] = useState(false);
  const [newChildName, setNewChildName] = useState("");
  const switchChild = useMutation({ mutationFn: api.setCurrentChild, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["children"] }) });
  const addChild = useMutation({ mutationFn: () => api.createChild({ name: newChildName }), onSuccess: data => {
    setNewChildName("");
    setShowAdd(false);
    switchChild.mutate(data.id);
    queryClient.invalidateQueries({ queryKey: ["children"] });
  }});
  const { data, isLoading: questionsLoading, error: questionsError } = useQuery({ queryKey: ["questions"], queryFn: api.questions });
  const [answers, setAnswers] = useState<Record<string, number>>(() => JSON.parse(localStorage.getItem(`assessment_${child.id}`) || "{}"));
  const [assessmentKey] = useState(() => {
    const storageKey = `assessment_key_${child.id}`;
    const existing = localStorage.getItem(storageKey);
    if (existing) return existing;
    const created = (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function")
      ? crypto.randomUUID()
      : "id-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(storageKey, created);
    return created;
  });
  // 恢复到第一个未作答的题目（评估进度持久化）
  const [questionIndex, setQuestionIndex] = useState(() => {
    const saved = JSON.parse(localStorage.getItem(`assessment_${child.id}`) || "{}");
    const savedPos = parseInt(localStorage.getItem(`assessment_pos_${child.id}`) || "0", 10);
    return Number.isNaN(savedPos) ? 0 : savedPos;
  });
  useEffect(() => { localStorage.setItem(`assessment_pos_${child.id}`, String(questionIndex)); }, [questionIndex, child.id]);
  const submit = useMutation({
    mutationFn: () => api.submitAssessment(child.id, answers, assessmentKey),
    onSuccess: () => {
      localStorage.removeItem(`assessment_${child.id}`);
      localStorage.removeItem(`assessment_key_${child.id}`);
      localStorage.removeItem(`assessment_pos_${child.id}`);
      setQuestionIndex(0);
      queryClient.invalidateQueries({ queryKey: ["tasks", child.id] });
      queryClient.invalidateQueries({ queryKey: ["children"] });
    }
  });
  useEffect(() => localStorage.setItem(`assessment_${child.id}`, JSON.stringify(answers)), [answers, child.id]);
  return <>
    <section className="profile-card">
      <div className="profile-card-avatar-wrap">
        <ChildAvatar child={child} size={72} />
        <AvatarUploader child={child} />
      </div>
      <div style={{flex:1, minWidth: 0}}><p className="eyebrow">当前孩子</p><h2>{child.name}</h2><p>{child.diagnosis || "尚未填写诊断信息"}</p></div>
      <button className="add-child-btn" onClick={() => setShowAdd(!showAdd)} title="添加孩子"><Plus size={16}/></button>
    </section>
    {showAdd && <div className="inline-add"><input placeholder="孩子的小名" value={newChildName} onChange={e => setNewChildName(e.target.value)}/><button onClick={() => addChild.mutate()} disabled={!newChildName.trim()}>保存</button></div>}
    {/* 多孩子切换：紧凑横向 pills */}
    {allChildren.length > 1 && <div className="child-pills">{allChildren.map(item => <button className={item.id === child.id ? "active" : ""} onClick={() => switchChild.mutate(item.id)} key={item.id}>
      <ChildAvatar child={item} size={20} />
      <span>{item.name}</span>
    </button>)}</div>}
    <ChildStatusCard snapshot={child.status_snapshot} lastReportAt={child.last_report_at} />
    <RecordImport childId={child.id} />
    <div className="page-heading"><p className="eyebrow">能力评估</p><h1>找到此刻最合适的起点</h1><p>根据孩子近两周的真实表现作答。不确定时选择"有时"。</p></div>
    {questionsLoading && <p>正在加载评估题目…</p>}
    {questionsError && <p className="error">评估题目加载失败：{String(questionsError)}</p>}
    {data && <section className="assessment-focus">
      <div className="assessment-progress"><span style={{width: `${(Object.keys(answers).length / data.items.length) * 100}%`}} /></div>
      <p className="assessment-count">已完成 {Object.keys(answers).length}/{data.items.length}</p>
      {data.items[questionIndex] && <article className="question">
        <small>{data.items[questionIndex].domain_name} · Level {data.items[questionIndex].level}</small>
        <strong>{data.items[questionIndex].text}</strong>
        <div className="answer-row">{["还不会", "有时", "经常"].map((label, value) =>
          <button key={label} className={answers[data.items[questionIndex].id] === value ? "selected" : ""} onClick={() => {
            setAnswers({ ...answers, [data.items[questionIndex].id]: value });
            if (questionIndex < data.items.length - 1) setQuestionIndex(questionIndex + 1);
          }}>{label}</button>)}</div>
      </article>}
      <div className="assessment-nav"><button disabled={questionIndex === 0} onClick={() => setQuestionIndex(questionIndex - 1)}>上一题</button><span>{questionIndex + 1}/{data.items.length}</span><button disabled={questionIndex === data.items.length - 1} onClick={() => setQuestionIndex(questionIndex + 1)}>下一题</button></div>
      <button className="primary" disabled={Object.keys(answers).length !== data.items.length || submit.isPending} onClick={() => submit.mutate()}>
        {submit.isSuccess ? <><Check/> 已生成训练任务</> : "提交完整评估并生成任务"}
      </button>
    </section>}
  </>;
}

function TrainingPage({ child }: { child: Child }) {
  const [view, setView] = useState<"tasks" | "flashcards">("tasks");
  const [manageMode, setManageMode] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [addingTask, setAddingTask] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newCat, setNewCat] = useState("基础能力");
  const [newDaily, setNewDaily] = useState(false);
  const [tplDomain, setTplDomain] = useState("全部");
  const [tplQuery, setTplQuery] = useState("");
  const [tplOpenDomain, setTplOpenDomain] = useState<string | null>(null);
  const { data: tasks = [], isLoading } = useQuery({ queryKey: ["tasks", child.id], queryFn: () => api.tasks(child.id) });
  const { data: skillCatalog = [] } = useQuery({ queryKey: ["skill-templates"], queryFn: api.skillTemplates });
  const [session, setSession] = useState<Session | null>(null);
  const { data: activeSession } = useQuery({ queryKey: ["active-session", child.id], queryFn: () => api.activeSession(child.id) });
  useEffect(() => { if (activeSession) setSession(activeSession); }, [activeSession]);
  const start = useMutation({ mutationFn: (task: Task) => api.createSession(child.id, task), onSuccess: data => { setSession(data); queryClient.invalidateQueries({ queryKey: ["active-session", child.id] }); } });
  const trial = useMutation({ mutationFn: (result: string) => api.addTrial(session!.id, result), onSuccess: setSession });
  const undo = useMutation({ mutationFn: () => api.undoTrial(session!.id), onSuccess: setSession });
  const finish = useMutation({ mutationFn: () => api.finishSession(session!.id), onSuccess: data => { setSession(data); queryClient.invalidateQueries({ queryKey: ["tasks", child.id] }); queryClient.invalidateQueries({ queryKey: ["active-session", child.id] }); } });
  const delTask = useMutation({ mutationFn: (taskId: string) => api.deleteTask(taskId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks", child.id] }) });
  const addTask = useMutation({
    mutationFn: () => api.createTask({ child_id: child.id, name: newName, description: newDesc || undefined, category: newCat, is_daily: newDaily }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tasks", child.id] }); setAddingTask(false); setNewName(""); setNewDesc(""); setNewDaily(false); }
  });
  const addFromTemplate = (tpl: SkillTemplate) => {
    api.createTask({ child_id: child.id, name: tpl.name, description: tpl.description, category: tpl.category }).then(() =>
      queryClient.invalidateQueries({ queryKey: ["tasks", child.id] })
    );
  };

  // 过滤：去掉报告项 + 按完成状态分组
  const realTasks = useMemo(() => tasks.filter(t => !t.name.includes("报告")), [tasks]);
  const activeTasks = useMemo(() => realTasks.filter(t => t.status !== "completed"), [realTasks]);
  const completedTasks = useMemo(() => realTasks.filter(t => t.status === "completed"), [realTasks]);

  // 按分类分组（保持 sort_order）
  const grouped = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const t of activeTasks) {
      const cat = t.category || "其他";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(t);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0], "zh"));
  }, [activeTasks]);

  // 排序操作
  const moveTask = (taskId: string, direction: -1 | 1) => {
    const idx = realTasks.findIndex(t => t.id === taskId);
    if ((direction === -1 && idx === 0) || (direction === 1 && idx === realTasks.length - 1)) return;
    const newOrder = [...realTasks];
    [newOrder[idx], newOrder[idx + direction]] = [newOrder[idx + direction], newOrder[idx]];
    api.reorderTasks(child.id, newOrder.map((t, i) => ({ id: t.id, sort_order: i }))).then(() =>
      queryClient.invalidateQueries({ queryKey: ["tasks", child.id] })
    );
  };

  if (session && session.status === "active") return <section className="training-live">
    <button className="back-link" onClick={() => setSession(null)}><ChevronLeft/> 返回任务列表</button>
    <p className="eyebrow">正在训练</p><h1>{session.skill_name}</h1>
    <div className="task-detail-desc">{(realTasks.find(t => t.name === session.skill_name) as Task)?.description || "每次呈现刺激后，记录孩子最少辅助下的反应。"}</div>
    <TrainingFlashcard skillName={session.skill_name}/>
    <div className="score-ring"><strong>{session.percentage}%</strong><small>独立正确</small></div>
    <div className="trial-log">{session.trials.map((value, index) => <span className={`trial ${value}`} key={index}>{value}</span>)}</div>
    <div className="trial-buttons">
      <button disabled={trial.isPending} onClick={() => trial.mutate("I")}>I<small>独立</small></button>
      <button disabled={trial.isPending} onClick={() => trial.mutate("V")}>V<small>语言</small></button>
      <button disabled={trial.isPending} onClick={() => trial.mutate("M")}>M<small>示范</small></button>
      <button disabled={trial.isPending} onClick={() => trial.mutate("P")}>P<small>身体</small></button>
      <button disabled={trial.isPending} onClick={() => trial.mutate("E")}>E<small>错误</small></button>
    </div>
    <button className="undo-trial" disabled={!session.trials.length || undo.isPending} onClick={() => undo.mutate()}>撤销上一条记录</button>
    <button className="primary" disabled={!session.trials.length} onClick={() => finish.mutate()}>结束并保存训练</button>
  </section>;
  return <>
    <div className="page-heading"><p className="eyebrow">训练中心</p><h1>今天，专注一件小事</h1><p>短时、高频、在成功时结束。</p></div>
    <div className="training-tabs">
      <button className={view === "tasks" ? "active" : ""} onClick={() => setView("tasks")}>当前任务 ({activeTasks.length})</button>
      <button className={view === "flashcards" ? "active" : ""} onClick={() => setView("flashcards")}>图片卡</button>
      <button className={manageMode ? "active manage-btn" : "manage-btn"} onClick={() => setManageMode(!manageMode)} title="管理任务"><PenLine size={14}/></button>
    </div>
    {view === "flashcards" ? <FlashcardCenter/> : isLoading ? <p>正在加载任务…</p> : activeTasks.length === 0 && completedTasks.length === 0 ?
      <section className="empty-state"><Target/><h2>还没有训练任务</h2><p>先去"孩子"页完成能力评估。</p></section> :
      <section className="task-list">
        {/* 添加新任务 */}
        {manageMode && addingTask && <article className="task-card add-task-form">
          <div style={{width:"100%"}}>
            <p className="tpl-hint">从训练库选择，或自定义输入</p>
            {/* 模板搜索 + 筛选 */}
            <input autoFocus placeholder="搜索训练（如：模仿、情绪、等待）" value={tplQuery} onChange={e => setTplQuery(e.target.value)} className="add-task-input"/>
            {tplQuery && (() => {
              const q = tplQuery.toLowerCase();
              const results = skillCatalog.flatMap(g => g.skills).filter(s =>
                s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
              ).slice(0, 8);
              return results.length ? <div className="tpl-search-results">
                {results.map(s => <button key={s.name} className="tpl-search-item" onClick={() => { addFromTemplate(s); setTplQuery(""); }}>
                  <span className="tpl-name">{s.name}</span>
                  <span className="tpl-cat">{s.category}</span>
                </button>)}
              </div> : <p className="muted small">未找到匹配的训练，请在下方自定义</p>;
            })()}
            {/* 按领域分组浏览 */}
            <select value={tplDomain} onChange={e => { setTplDomain(e.target.value); setTplOpenDomain(null); }} className="add-task-select">
              <option value="全部">全部领域</option>
              {skillCatalog.map(g => <option key={g.domain} value={g.domain}>{g.domain}（{g.count}）</option>)}
            </select>
            {skillCatalog.filter(g => tplDomain === "全部" || g.domain === tplDomain).map(group => (
              <div key={group.domain} className="tpl-group">
                <button className="tpl-group-head" onClick={() => setTplOpenDomain(tplOpenDomain === group.domain ? null : group.domain)}>
                  <span>{group.domain}</span><small>{group.count} 项 {tplOpenDomain === group.domain ? "▾" : "▸"}</small>
                </button>
                {tplOpenDomain === group.domain && <div className="tpl-list">
                  {group.skills.map(s => <button key={s.name} className="tpl-item" onClick={() => addFromTemplate(s)}>
                    <span className="tpl-name">{s.name}<span className="tpl-level">Lv{s.level}</span></span>
                    <span className="tpl-desc">{s.description}</span>
                    <span className="tpl-add-btn">+ 添加</span>
                  </button>)}
                </div>}
              </div>
            ))}
            <div className="tpl-divider"><span>自定义训练</span></div>
            <input placeholder="自定义训练名称" value={newName} onChange={e => setNewName(e.target.value)} className="add-task-input"/>
            <textarea placeholder="具体说明（可选）" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={2} className="add-task-input"/>
            <select value={newCat} onChange={e => setNewCat(e.target.value)} className="add-task-select">
              {skillCatalog.map(g => <option key={g.domain} value={g.domain}>{g.domain}</option>)}
              <option value="其他">其他</option>
            </select>
            <label className="daily-toggle"><input type="checkbox" checked={newDaily} onChange={e => setNewDaily(e.target.checked)}/> 每日任务（完成后保留）</label>
            <div style={{display:"flex",gap:"8px"}}>
              <button className="primary add-task-submit" disabled={!newName.trim() || addTask.isPending} onClick={() => addTask.mutate()}>添加</button>
              <button onClick={() => {setAddingTask(false);setNewName("");setNewDesc("")}}>取消</button>
            </div>
          </div>
        </article>}
        {grouped.map(([category, items]) => {
          const collapsed = collapsedGroups[category];
          return <div key={category} className={`task-group${collapsed ? " collapsed" : ""}`}>
            <h3 className="task-group-title" onClick={() => setCollapsedGroups(s => ({ ...s, [category]: !s[category] }))}>
              {category}<span>{items.length} 项 {collapsed ? "▸" : "▾"}</span>
            </h3>
            {!collapsed && items.map((task, i) => {
            const isExpanded = expandedId === task.id;
            const globalIdx = realTasks.indexOf(task);
            return <article key={task.id} className={`task-card compact expandable ${task.status}${isExpanded?" open":""}`}>
              <div className="task-row" onClick={() => setExpandedId(isExpanded ? null : task.id)}>
                {manageMode && <div className="task-sort-btns">
                  <button disabled={globalIdx===0} onClick={(e)=>{e.stopPropagation();moveTask(task.id,-1)}} title="上移">▲</button>
                  <button disabled={globalIdx>=realTasks.length-1} onClick={(e)=>{e.stopPropagation();moveTask(task.id,1)}} title="下移">▼</button>
                </div>}
                <span className="task-name">{task.name}{task.is_daily && <em className="daily-tag">每日</em>}</span>
                {!manageMode && <button onClick={(e)=>{e.stopPropagation();start.mutate(task)}} aria-label={`开始${task.name}`}><Play size={16}/></button>}
                {manageMode && <button className="task-del-btn" onClick={(e)=>{e.stopPropagation();delTask.mutate(task.id)}} title="删除">×</button>}
              </div>
              {isExpanded && <div className="task-expand-body">
                <p className="task-desc-text">{task.description || "暂无详细说明"}</p>
                <div className="task-expand-actions">
                  <span className="task-cat-tag">{task.category}</span>
                  {!manageMode && <button className="primary small" onClick={()=>{setExpandedId(null);start.mutate(task)}}>开始训练</button>}
                </div>
              </div>}
            </article>;
          })}
        </div>;
        })}
        {/* 管理模式底部按钮 */}
        {manageMode && <div className="task-manage-footer">
          <button className="primary" onClick={()=>setAddingTask(true)}><Plus size={14}/> 添加新训练</button>
        </div>}
      </section>}
    {session?.status === "completed" && <div className="success-banner"><Check/> 本次训练已保存，独立正确率 {session.percentage}%</div>}
  </>;
}

function TrainingFlashcard({ skillName }: { skillName: string }) {
  const { data: catalog } = useQuery({ queryKey: ["flashcards"], queryFn: api.flashcards });
  const [index, setIndex] = useState(0);
  const allCategories = useMemo(() => catalog?.groups.flatMap(g => g.categories) ?? [], [catalog]);
  const matched = useMemo(() => {
    const lower = skillName.toLowerCase();
    const exact = allCategories.find(c => lower.includes(c.name.toLowerCase()) || c.name.toLowerCase().includes(lower));
    if (exact) return exact;
    const keywordMap: Record<string, string[]> = {
      "情绪": ["情绪", "情感"], "颜色": ["颜色"], "动物": ["动物"], "水果": ["水果"],
      "蔬菜": ["蔬菜"], "职业": ["职业", "服务人员"], "天气": ["天气"], "形状": ["形状"],
      "身体": ["身体部位"], "食物": ["食物", "饮料"], "衣物": ["衣物"], "数字": ["数字"],
      "字母": ["字母"], "分类": ["分类"], "配对": ["配对"], "社交": ["社交"],
    };
    for (const [keyword, patterns] of Object.entries(keywordMap)) {
      if (lower.includes(keyword)) {
        const found = allCategories.find(c => {
          const cn = c.name.toLowerCase();
          return patterns.some(p => cn.includes(p));
        });
        if (found) return found;
      }
    }
    return undefined;
  }, [allCategories, skillName]);
  const { data: image, isLoading } = useQuery({
    queryKey: ["flashcard-image", matched?.name, index],
    queryFn: () => api.flashcardImage(matched!.name, index),
    enabled: Boolean(matched)
  });
  useEffect(() => () => { if (image) URL.revokeObjectURL(image); }, [image]);
  if (!matched) return null;
  const goRandom = () => setIndex(Math.floor(Math.random() * matched.count));
  if (!matched) return null;
  return <div className="training-flashcard">
    <div className="flashcard-frame">
      <span className="flashcard-label">{matched.name}</span>
      <div className="flashcard-stage">
        {isLoading ? <div className="flashcard-loading"><Sparkles size={24}/> 加载中…</div> : image ? <img src={image} alt={`${matched.name} ${index + 1}`}/> : null}
      </div>
      <div className="flashcard-nav">
        <button disabled={index === 0} onClick={() => setIndex(index - 1)}><ChevronLeft size={16}/></button>
        <button className="flashcard-random" onClick={goRandom} title="随机"><Shuffle size={16}/></button>
        <span className="flashcard-counter">{index + 1} / {matched.count}</span>
        <button disabled={index >= matched.count - 1} onClick={() => setIndex(index + 1)}><ChevronRight size={16}/></button>
      </div>
    </div>
  </div>;
}

function FlashcardCenter() {
  const { data, isLoading } = useQuery({ queryKey: ["flashcards"], queryFn: api.flashcards });
  const [category, setCategory] = useState<{ name: string; count: number } | null>(null);
  const [index, setIndex] = useState(0);
  const { data: image, isLoading: imageLoading } = useQuery({
    queryKey: ["flashcard-image", category?.name, index],
    queryFn: () => api.flashcardImage(category!.name, index),
    enabled: Boolean(category)
  });
  useEffect(() => () => { if (image) URL.revokeObjectURL(image); }, [image]);
  if (category) return <section className="flashcard-viewer">
    <button className="back-link" onClick={() => { setCategory(null); setIndex(0); }}><ChevronLeft/> 返回类别</button>
    <div className="flashcard-stage">{imageLoading ? <p>正在渲染卡片…</p> : image ? <img src={image} alt={`${category.name} ${index + 1}`}/> : null}</div>
    <strong>{category.name}</strong><small>{index + 1} / {category.count}</small>
    <div className="flashcard-controls"><button disabled={index === 0} onClick={() => setIndex(index - 1)}>上一张</button><button disabled={index >= category.count - 1} onClick={() => setIndex(index + 1)}>下一张</button></div>
  </section>;
  if (isLoading) return <p>正在加载图片卡目录…</p>;
  return <section className="flashcard-catalog">{data?.groups.map(group => <div key={group.group}><h3>{group.group}</h3><div>{group.categories.map(item =>
    <button key={item.name} onClick={() => setCategory(item)}><span>{item.name}</span><small>{item.count} 张</small><ChevronRight/></button>)}</div></div>)}</section>;
}

function ReportTrendBadge({ trend, delta }: { trend?: string | null; delta?: number }) {
  const label = trend === "progress" ? "进步" : trend === "regression" ? "回退" : "稳定";
  const cls = trend === "progress" ? "trend-up" : trend === "regression" ? "trend-down" : "trend-stable";
  return <span className={`report-status trend-badge ${cls}`}>{label}{typeof delta === "number" && delta !== 0 ? ` ${delta > 0 ? "+" : ""}${delta}%` : ""}</span>;
}

function ProgressPage({ child }: { child: Child }) {
  const { data, refetch } = useQuery({ queryKey: ["progress", child.id], queryFn: () => api.progress(child.id) });
  const { data: reports = [] } = useQuery({ queryKey: ["reports", child.id], queryFn: () => api.reports(child.id), refetchInterval: query => {
    const rows = query.state.data as any[] | undefined;
    return rows?.some(item => item.status === "pending") ? 1500 : false;
  }});
  const generate = useMutation({ mutationFn: () => api.generateReport(child.id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", child.id] }) });
  return <>
    <div className="page-heading"><p className="eyebrow">成长进展</p><h1>每一点积累，都有意义</h1></div>
    <div className="stats">
      <article><strong>{data?.training_days || 0}</strong><span>训练天数</span></article>
      <article><strong>{data?.completed_sessions || 0}</strong><span>完成训练</span></article>
      <article><strong>{data?.average_percentage || 0}%</strong><span>平均独立率</span></article>
    </div>
    <section className="card"><div className="section-title"><span>最近训练</span><button className="text-button" onClick={() => refetch()}>刷新</button></div>
      {!data?.timeline?.length ? <p className="muted">完成第一次训练后，这里会出现趋势。</p> : data.timeline.map((item: Session) =>
        <div className="timeline" key={item.id}><span><Check/></span><div><strong>{item.skill_name}</strong><small>{item.percentage}% 独立正确</small></div></div>)}
    </section>
    <section className="card report-card"><div><p className="eyebrow">AI 训练报告</p><h2>把数据变成下一步建议</h2><p>基于真实训练记录生成结构化总结。</p></div>
      <button className="secondary" onClick={() => generate.mutate()} disabled={generate.isPending}>生成本周报告</button>
      {reports.map((report: Report) => <div className={`report-item ${report.status}`} key={report.id}>
        <div className="report-head"><strong>{report.title}</strong>
          {report.status === "pending" ? <span className="report-status">生成中…</span>
            : report.status === "failed" ? <span className="report-status">失败</span>
            : <ReportTrendBadge trend={report.trend} delta={report.trend_detail?.delta} />}
        </div>
        <p>{report.summary}</p>
        {report.content?.next_steps?.length ? <ul>{report.content.next_steps.map((step: string) => <li key={step}>{step}</li>)}</ul> : null}
        {report.file_url ? <button className="text-button" onClick={() => api.downloadReport(report.id)}>下载 PDF 报告</button> : null}
      </div>)}
    </section>
  </>;
}

function ActStepForm({ step, onSave, onToJournal }: { step: { key: ActStepKey; name: string; prompt: string; placeholder: string }; session: ActSession; onSave: (reflection: string) => void; onToJournal: () => void }) {
  const [text, setText] = useState("");
  return <div className="act-step-form">
    <p className="eyebrow">第 {ACT_STEPS.findIndex(s => s.key === step.key) + 1} 步 / 共 {ACT_STEPS.length} 步</p>
    <h3>{step.name}</h3>
    <p className="act-prompt">{step.prompt}</p>
    <textarea value={text} onChange={e => setText(e.target.value)} placeholder={step.placeholder} rows={4}/>
    <div className="growth-detail-actions">
      <button className="primary" disabled={!text.trim()} onClick={() => onSave(text.trim())}>完成本步</button>
      <button className="text-button" onClick={onToJournal}>写进日记</button>
    </div>
  </div>;
}

function ActResolutionForm({ onSave, onRestart, onToJournal }: { session: ActSession; onSave: (solved: boolean, note: string) => void; onRestart: () => void; onToJournal: () => void }) {
  const [solved, setSolved] = useState<boolean | null>(null);
  const [note, setNote] = useState("");
  return <div className="act-resolution-form">
    <h3 className="coach-section-head">回到原问题</h3>
    <p>六步都走完了。回到刚才那个问题——现在它怎么样了？</p>
    <div className="act-solved-picker">
      <button className={solved === true ? "selected" : ""} onClick={() => setSolved(true)}>缓解了</button>
      <button className={solved === false ? "selected" : ""} onClick={() => setSolved(false)}>还在</button>
    </div>
    <textarea value={note} onChange={e => setNote(e.target.value)} placeholder="写一句此刻的状态，或者接下来想做的事。" rows={3}/>
    <div className="growth-detail-actions">
      <button className="primary" disabled={solved === null} onClick={() => onSave(solved!, note.trim())}>保存这次记录</button>
      <button className="text-button" onClick={onRestart}>再来一次六步</button>
      <button className="text-button" onClick={onToJournal}>写进日记</button>
    </div>
  </div>;
}

function ActResolutionView({ session, onRestart }: { session: ActSession; onRestart: () => void }) {
  return <div className="act-resolution-view">
    <h3 className="coach-section-head">这次的结果</h3>
    <p>
      {session.resolution.solved === true ? "原问题已经缓解。" :
       session.resolution.solved === false ? "原问题还在，可以再走一次。" :
       "已完成六步。"}
    </p>
    {session.resolution.note && <blockquote className="act-resolution-note">{session.resolution.note}</blockquote>}
    <div className="growth-detail-actions">
      <button className="primary" onClick={onRestart}>再走一次六步</button>
    </div>
  </div>;
}

function CoachApp({ username, switchToAba, logout }: { username: string; switchToAba: () => void; logout: () => void }) {
  type CoachTab = "chat" | "emotion" | "growth" | "journal" | "knowledge";
  const [tab, setTab] = useState<CoachTab>("chat");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    "你好，这里是一个可以自由表达的空间。你可以聊任何事，我会认真回应你。"
  ]);
  const [mood, setMood] = useState("平静");
  // 情绪多维记录（今日）
  const [moodDetail, setMoodDetail] = useState<MoodDetail>({ emotions: ["calm"], intensity: 3, triggers: [], body: [], coping: "" });
  const [journal, setJournal] = useState("");
  const [articleId, setArticleId] = useState<string | null>(null);
  // ACT 六步法：以「一个问题」为单位发起一个 session，可随时再来一次
  // session = { id, problem, steps: [{ key, reflection, completedAt }], resolution, createdAt, updatedAt, status }
  const ACT_SESSIONS_KEY = "coach_act_sessions";
  const [actSessions, setActSessions] = useState<ActSession[]>(() => {
    try {
      const raw = localStorage.getItem(ACT_SESSIONS_KEY);
      if (raw) return JSON.parse(raw);
    } catch { /* ignore */ }
    return [];
  });
  useEffect(() => {
    try { localStorage.setItem(ACT_SESSIONS_KEY, JSON.stringify(actSessions)); } catch { /* ignore */ }
  }, [actSessions]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [newProblem, setNewProblem] = useState("");
  // 知识库分类筛选
  const [activeCategory, setActiveCategory] = useState<string>("全部");
  const { data: coachOverview } = useQuery({ queryKey: ["coach-overview"], queryFn: api.coachOverview });
  const { data: coachHistory = [] } = useQuery({ queryKey: ["chat", "coach"], queryFn: () => api.chatMessages("coach") });
  const { data: savedMoods = [] } = useQuery({ queryKey: ["coach-moods"], queryFn: api.moods });
  const { data: savedJournals = [] } = useQuery({ queryKey: ["coach-journals"], queryFn: api.journals });
  const { data: articleCatalog } = useQuery({ queryKey: ["coach-articles"], queryFn: api.coachArticles });
  const { data: selectedArticle } = useQuery({ queryKey: ["coach-article", articleId], queryFn: () => api.coachArticle(articleId!), enabled: Boolean(articleId) });
  useEffect(() => {
    if (coachHistory.length) setMessages(coachHistory.map(item => item.content));
  }, [coachHistory]);
  const coachChatMutation = useMutation({ mutationFn: (text: string) => api.coachChat(text), onSuccess: () => {
    setMessage("");
    queryClient.invalidateQueries({ queryKey: ["chat", "coach"] });
  }});
  const moodMutation = useMutation({
    mutationFn: () => {
      const primaryLabel = MOOD_LABEL_MAP[moodDetail.emotions[0]] || moodDetail.emotions[0] || mood;
      const note = JSON.stringify({ ...moodDetail, savedAt: new Date().toISOString() });
      return api.saveMood({ mood: primaryLabel, intensity: moodDetail.intensity, note });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coach-moods"] });
      queryClient.invalidateQueries({ queryKey: ["coach-overview"] });
    }
  });
  const journalMutation = useMutation({ mutationFn: () => api.saveJournal(journal), onSuccess: () => {
    setJournal("");
    queryClient.invalidateQueries({ queryKey: ["coach-journals"] });
    queryClient.invalidateQueries({ queryKey: ["coach-overview"] });
  }});
  const send = () => {
    if (!message.trim()) return;
    coachChatMutation.mutate(message);
  };
  const GROWTH_STAGES: { id: number; name: string; copy: string; practice: string }[] = [];
  void GROWTH_STAGES;
  const CATEGORY_LABELS: Record<string, string> = {
    "methodology": "方法与认知",
    "emotion": "情绪",
    "self": "自我关怀",
    "relationship": "关系",
    "career": "工作与生活平衡",
    "health": "健康与睡眠",
    "habits": "习惯养成",
    "parenting": "养育压力",
    "mindfulness": "正念",
  };
  const headers: Record<CoachTab, [string, string]> = {
    chat: ["陪伴", `${username}，想聊点什么都可以`],
    emotion: ["情绪", "记录今天的状态，看见自己的节奏"],
    growth: ["ACT", "带着一个问题，按自己的节奏走完六步"],
    journal: ["日记", "留一句话给今天的自己"],
    knowledge: ["知识库", "为家长准备的成长内容"]
  };

  // ─── ACT session helpers ───
  const sortedSessions = useMemo(
    () => [...actSessions].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [actSessions]
  );
  const activeSession = useMemo(
    () => actSessions.find(s => s.id === activeSessionId) || null,
    [actSessions, activeSessionId]
  );

  const updateSession = (id: string, updater: (s: ActSession) => ActSession) => {
    setActSessions(prev => prev.map(s => (s.id === id ? { ...updater(s), updatedAt: new Date().toISOString() } : s)));
  };

  const startNewSession = () => {
    const problem = newProblem.trim();
    if (!problem) return;
    const session = newActSession(problem);
    setActSessions(prev => [session, ...prev]);
    setActiveSessionId(session.id);
    setNewProblem("");
  };

  const restartSession = (id: string) => {
    setActSessions(prev => prev.map(s => (s.id === id ? newActSession(s.problem) : s)));
    setActiveSessionId(id);
  };

  const goToJournalFromAct = () => {
    setActiveSessionId(null);
    setTab("journal");
  };

  const renderActSessionDetail = (session: ActSession) => {
    const completedCount = ACT_STEPS.filter(step => session.steps[step.key].completedAt).length;
    const currentIndex = ACT_STEPS.findIndex(step => !session.steps[step.key].completedAt);
    const allDone = currentIndex === -1;
    const currentStep = allDone ? null : ACT_STEPS[currentIndex];
    return <>
      <button className="back-link" onClick={() => setActiveSessionId(null)}><ChevronLeft/> 返回</button>
      <div className="act-progress">
        <p className="eyebrow">{session.status === "completed" ? "已完成" : `进行中 ${completedCount}/${ACT_STEPS.length}`}</p>
        <div className="act-progress-bar"><span style={{ width: `${(completedCount / ACT_STEPS.length) * 100}%` }} /></div>
        <h2 className="act-problem">{session.problem}</h2>
      </div>
      {!allDone && currentStep && <ActStepForm
        session={session}
        step={currentStep}
        onSave={(reflection) => updateSession(session.id, s => ({
          ...s,
          steps: { ...s.steps, [currentStep.key]: { reflection, completedAt: new Date().toISOString() } }
        }))}
        onToJournal={goToJournalFromAct}
      />}
      {allDone && !session.resolution.updatedAt && <ActResolutionForm
        session={session}
        onSave={(solved, note) => updateSession(session.id, s => ({
          ...s,
          resolution: { solved, note, updatedAt: new Date().toISOString() },
          status: "completed"
        }))}
        onRestart={() => restartSession(session.id)}
        onToJournal={goToJournalFromAct}
      />}
      {session.resolution.updatedAt && <ActResolutionView session={session} onRestart={() => restartSession(session.id)} />}
      <details className="act-step-list">
        <summary>查看所有步骤的记录</summary>
        <ol>{ACT_STEPS.map(step => (
          <li key={step.key}>
            <strong>{step.name}</strong>
            {session.steps[step.key].completedAt
              ? <p>{session.steps[step.key].reflection || "（未填写）"}</p>
              : <p className="muted small">未完成</p>}
          </li>
        ))}</ol>
      </details>
    </>;
  };
  const page = {
    chat: <>
      <div className="mood-picker">{["平静", "焦虑", "疲惫", "悲伤"].map(item => <button className={mood === item ? "selected" : ""} onClick={() => setMood(item)} key={item}>{item}</button>)}</div>
      <section className="card coach-chat">
        <div className="section-title"><span><MessageCircleHeart size={19}/> 陪伴对话</span><small>由 MiniMax-M3 驱动 · ACT 成长支持</small></div>
        {messages.map((item, index) => <div className={coachHistory[index]?.role === "user" ? "coach-bubble user-message" : "coach-bubble"} key={index}>{item}</div>)}
        {coachChatMutation.isPending && <div className="coach-bubble">我在听，也在认真想怎么回应你…</div>}
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="写一句你现在想说的" /><button onClick={send} disabled={!message.trim() || coachChatMutation.isPending}>发送</button></div>
      </section>
      <section className="coach-tip"><strong>今天可以这样试一次</strong><p>把想做的事缩小到 2 分钟，先开始，再看接下来要不要继续。</p><button onClick={() => setTab("journal")}>写进今日反思</button></section>
    </>,
    emotion: (() => {
      // 解析最近 30 条记录的 detail，按情绪计数
      const recentDetails = savedMoods.map(item => parseMoodDetail(item.note)).filter(Boolean) as MoodDetail[];
      const todayDetail = recentDetails[0] || null;
      const last7 = recentDetails.slice(0, 7);
      const avgIntensity = last7.length ? (last7.reduce((s, d) => s + d.intensity, 0) / last7.length).toFixed(1) : "—";
      const emotionCounts: Record<string, number> = {};
      last7.forEach(d => d.emotions.forEach(k => { emotionCounts[k] = (emotionCounts[k] || 0) + 1; }));
      const topEmotions = Object.entries(emotionCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);

      const toggleIn = <T,>(arr: T[], v: T) => arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v];
      const toggleEmotion = (key: string) => {
        setMoodDetail(prev => {
          const next = toggleIn(prev.emotions, key);
          return { ...prev, emotions: next.length ? next : ["calm"] };
        });
      };
      const toggleTrigger = (label: string) => setMoodDetail(prev => ({ ...prev, triggers: toggleIn(prev.triggers, label) }));
      const toggleBody = (label: string) => setMoodDetail(prev => ({ ...prev, body: toggleIn(prev.body, label) }));

      const canSave = moodDetail.emotions.length > 0;
      const primaryLabel = moodDetail.emotions.map(k => MOOD_LABEL_MAP[k] || k).join(" · ");

      return <>
        <section className="card emotion-panel">
          <div className="emotion-stats">
            <div><span>本周强度</span><strong>{avgIntensity}</strong><small>/5</small></div>
            <div><span>已记录</span><strong>{savedMoods.length}</strong><small>天</small></div>
            <div><span>常见情绪</span><strong className="emotion-top">{topEmotions.map(([k]) => MOOD_LABEL_MAP[k] || k).join(" · ") || "—"}</strong></div>
          </div>
          <div className="emotion-trend" aria-label="近 7 天强度趋势">
            {Array.from({ length: 7 }).map((_, i) => {
              const d = last7[i];
              const v = d ? d.intensity : 0;
              return <div key={i} className={`emotion-bar ${v ? `lvl-${v}` : "empty"}`} title={d ? `${v}/5` : "未记录"}><span style={{ height: `${(v / 5) * 100}%` }} /></div>;
            })}
          </div>
        </section>

        <section className="card emotion-form">
          <h3 className="coach-section-head">今天的情绪</h3>

          <div className="form-row">
            <label className="form-label">情绪（可多选）</label>
            <div className="mood-families">
              {MOOD_FAMILIES.map(family => (
                <div className="mood-family" key={family.group}>
                  <span className="mood-family-title">{family.group}</span>
                  <div className="mood-chips">
                    {family.items.map(item => <button key={item.key} className={moodDetail.emotions.includes(item.key) ? "selected" : ""} onClick={() => toggleEmotion(item.key)}>{item.label}</button>)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="form-row">
            <label className="form-label">强度 · {INTENSITY_LABELS[moodDetail.intensity - 1]}</label>
            <div className="intensity-bar">
              {[1, 2, 3, 4, 5].map(n => <button key={n} className={moodDetail.intensity === n ? "selected" : ""} onClick={() => setMoodDetail(prev => ({ ...prev, intensity: n }))}>{n}</button>)}
            </div>
          </div>

          <div className="form-row">
            <label className="form-label">触发场景（可多选）</label>
            <div className="tag-cloud">
              {TRIGGER_OPTIONS.map(opt => <button key={opt} className={moodDetail.triggers.includes(opt) ? "selected" : ""} onClick={() => toggleTrigger(opt)}>{opt}</button>)}
            </div>
          </div>

          <div className="form-row">
            <label className="form-label">身体感受（可多选）</label>
            <div className="tag-cloud">
              {BODY_OPTIONS.map(opt => <button key={opt} className={moodDetail.body.includes(opt) ? "selected" : ""} onClick={() => toggleBody(opt)}>{opt}</button>)}
            </div>
          </div>

          <div className="form-row">
            <label className="form-label">应对方式（可选）</label>
            <textarea value={moodDetail.coping} onChange={e => setMoodDetail(prev => ({ ...prev, coping: e.target.value }))} placeholder="做了什么 / 想做什么 / 没做什么但注意到…" rows={2}/>
          </div>

          <button className="coach-main-button" disabled={!canSave || moodMutation.isPending} onClick={() => moodMutation.mutate()}>
            {moodMutation.isSuccess ? "今天的情绪已保存" : `保存今天的记录：${primaryLabel}`}
          </button>
        </section>

        <h3 className="coach-section-head">最近记录（{savedMoods.length}）</h3>
        <div className="emotion-history">
          {savedMoods.length === 0 ? <p className="muted small">还没有记录。今天第一次记录后会出现这里。</p> :
            savedMoods.slice(0, 14).map(item => {
              const detail = parseMoodDetail(item.note);
              const date = new Date(item.entry_date);
              return <article key={item.id} className="emotion-history-item">
                <time>{date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</time>
                <div>
                  <strong>{detail ? detail.emotions.map(k => MOOD_LABEL_MAP[k] || k).join(" · ") : item.mood}</strong>
                  <span className="emotion-intensity-badge">强度 {item.intensity}/5</span>
                  {detail && detail.triggers.length > 0 && <p className="emotion-history-tags"><small>场景：</small>{detail.triggers.join("、")}</p>}
                  {detail && detail.body.length > 0 && <p className="emotion-history-tags"><small>身体：</small>{detail.body.join("、")}</p>}
                  {detail && detail.coping && <p className="emotion-history-coping">{detail.coping}</p>}
                </div>
              </article>;
            })}
        </div>
      </>;
    })(),
    growth: activeSession ? <section className="card act-session">{renderActSessionDetail(activeSession)}</section> : <>
      <section className="card act-intake">
        <h3 className="coach-section-head">现在困扰你的是什么？</h3>
        <p className="muted small">用一句话写下你今天最想处理的问题。ACT 会按 6 步陪你走一遍——觉察 → 接纳 → 解离 → 当下 → 价值 → 行动。</p>
        <textarea value={newProblem} onChange={e => setNewProblem(e.target.value)} placeholder="比如：晚上孩子又哭闹，我忍不住对他吼了。" rows={3}/>
        <button className="primary" disabled={!newProblem.trim()} onClick={startNewSession}>开始六步</button>
      </section>
      <h3 className="coach-section-head">过往问题（{sortedSessions.length}）</h3>
      {sortedSessions.length === 0 ? <p className="muted small">发起第一个问题后，会按时间倒序保存在这里。</p> :
        <div className="act-history">{sortedSessions.map(session => {
          const completedCount = ACT_STEPS.filter(step => session.steps[step.key].completedAt).length;
          return <button key={session.id} className={`act-history-item ${session.status}`} onClick={() => setActiveSessionId(session.id)}>
            <div className="act-history-head">
              <strong>{session.problem}</strong>
              <small>{new Date(session.updatedAt).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</small>
            </div>
            <p className="muted small">
              {session.status === "completed"
                ? (session.resolution.solved === true ? "已解决" : session.resolution.solved === false ? "未解决" : "已完成六步")
                : `进行中 ${completedCount}/${ACT_STEPS.length}`}
            </p>
          </button>;
        })}</div>}
    </>,
    journal: <>
      <section className="card journal-card"><p>今天有没有一个你想记录下来的瞬间？</p><p>如果有朋友处在你今天的位置，你会对他说什么？</p><textarea value={journal} onChange={e => setJournal(e.target.value)} placeholder="想到什么写什么，不必完整"/><button className="coach-main-button" disabled={!journal.trim() || journalMutation.isPending} onClick={() => journalMutation.mutate()}>保存今日反思</button></section>
      <h3 className="coach-section-head">过往记录</h3>
      <div className="journal-history">{savedJournals.length ? savedJournals.map(item => <article key={item.id}><time>{new Date(item.created_at).toLocaleDateString("zh-CN", {month: "short", day: "numeric"})}</time><div><strong>{item.content.slice(0, 18)}</strong><p>{item.content}</p></div></article>) : <p className="muted">保存第一篇反思后会显示在这里。</p>}</div>
    </>,
    knowledge: articleId ? <section className="article-detail"><button className="back-link" onClick={() => setArticleId(null)}><ChevronLeft/> 返回知识库</button>{selectedArticle ? <><p className="eyebrow">{CATEGORY_LABELS[selectedArticle.category] || selectedArticle.category} · {selectedArticle.read_time}</p><h2>{selectedArticle.title}</h2><p className="article-summary">{selectedArticle.summary}</p><div className="article-content">{selectedArticle.content}</div></> : <p>正在加载文章…</p>}</section> : (() => {
      const availableCategories = Array.from(new Set((articleCatalog?.items || []).map(item => item.category)));
      const orderedKnown = ["parenting", "self", "emotion", "relationship", "mindfulness", "methodology", "health", "habits", "career"];
      const visibleCats = orderedKnown.filter(c => availableCategories.includes(c));
      const categoryKeys = ["全部", ...visibleCats];
      const filteredItems = (articleCatalog?.items || []).filter(item =>
        activeCategory === "全部" || item.category === activeCategory
      );
      return <>
        <div className="knowledge-chips">{categoryKeys.map(cat => <button key={cat} className={cat === activeCategory ? "selected" : ""} onClick={() => setActiveCategory(cat)}>{cat === "全部" ? "全部" : CATEGORY_LABELS[cat] || cat}</button>)}</div>
        {filteredItems.length === 0 ? <p className="muted">该分类下还没有内容。</p> : <div className="knowledge-list">{filteredItems.map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{CATEGORY_LABELS[item.category] || item.category}{item.subcategory ? ` · ${item.subcategory}` : ""} · {item.read_time}</small><strong>{item.title}</strong><p>{item.summary}</p><ChevronRight/></button>)}</div>}
      </>;
    })()
  }[tab];
  const navItems = [
    ["chat", "陪伴", MessageCircleHeart], ["emotion", "情绪", Smile], ["growth", "成长", Sprout],
    ["journal", "日记", PenLine], ["knowledge", "知识库", BookOpen]
  ] as const;
  return <main className="coach-shell">
    <header className="coach-hero compact">
      <button onClick={switchToAba}><ChevronLeft /> 皮特 - ABA 智能助手</button>
      <p className="eyebrow">家长陪伴 · {headers[tab][0]}</p>
      <h1>{headers[tab][1]}</h1>
      <p>一个安全、温和、不评判的空间</p>
    </header>
    <section className="coach-content">{page}{tab === "knowledge" && <button className="coach-logout" onClick={logout}>退出登录</button>}</section>
    <nav className="coach-nav">{navItems.map(([id, label, Icon]) => <button className={tab === id ? "active" : ""} onClick={() => setTab(id)} key={id}><Icon/><span>{label}</span></button>)}</nav>
  </main>;
}

function ExpertApp({ username, logout }: { username: string; logout: () => void }) {
  const [workspace, setWorkspace] = useState<"inbox" | "profile">("inbox");
  const [selected, setSelected] = useState<ExpertClient | null>(null);
  const [reply, setReply] = useState("");
  const { data: savedProfile } = useQuery({ queryKey: ["expert-profile"], queryFn: api.expertProfile });
  const [profile, setProfile] = useState<ExpertProfile | null>(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  useEffect(() => { if (savedProfile) setProfile(savedProfile); }, [savedProfile]);
  useEffect(() => { if (savedProfile?.avatar_url) setAvatarPreview(api.assetUrl(savedProfile.avatar_url)); }, [savedProfile]);
  const { data: clientData } = useQuery({
    queryKey: ["expert-clients"],
    queryFn: api.expertClients,
    refetchInterval: 10_000
  });
  const { data: messages } = useQuery({
    queryKey: ["expert-client-messages", selected?.id],
    queryFn: () => api.expertClientMessages(selected!.id),
    enabled: Boolean(selected),
    refetchInterval: 8_000
  });
  const sendReply = useMutation({
    mutationFn: () => api.replyToClient(selected!.id, reply),
    onSuccess: () => {
      setReply("");
      queryClient.invalidateQueries({ queryKey: ["expert-client-messages", selected?.id] });
      queryClient.invalidateQueries({ queryKey: ["expert-clients"] });
    }
  });
  const saveProfile = useMutation({
    mutationFn: () => api.saveExpertProfile(profile!),
    onSuccess: data => { setProfile(data); queryClient.invalidateQueries({ queryKey: ["expert-profile"] }); }
  });
  const uploadAvatar = useMutation({
    mutationFn: api.uploadExpertAvatar,
    onSuccess: data => {
      if (profile) setProfile({...profile, avatar_url: data.avatar_url});
      setAvatarPreview(`${api.assetUrl(data.avatar_url)}?v=${Date.now()}`);
      queryClient.invalidateQueries({ queryKey: ["expert-profile"] });
    }
  });
  const closeConsultation = useMutation({
    mutationFn: () => api.closeExpertConsultation(selected!.id),
    onSuccess: () => {
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["expert-clients"] });
    }
  });
  return <main className="expert-shell">
    <header className="expert-hero">
      {selected && <button onClick={() => setSelected(null)}><ChevronLeft/> 返回客户列表</button>}
      <p className="eyebrow">{workspace === "profile" ? "专家资料" : "专家工作台"}</p>
      <h1>{selected ? selected.name : workspace === "profile" ? "完善你的专业名片" : `你好，${savedProfile?.display_name || username}`}</h1>
      <p>{selected ? "查看问题并给出专业、清晰的回复" : workspace === "profile" ? "家长选择专家时会看到这些信息" : "集中处理家长咨询，不混入系统管理功能"}</p>
    </header>
    <section className="expert-content">
      {!selected && <div className="expert-workspace-tabs"><button className={workspace === "inbox" ? "active" : ""} onClick={() => setWorkspace("inbox")}>客户咨询</button><button className={workspace === "profile" ? "active" : ""} onClick={() => setWorkspace("profile")}>我的资料</button></div>}
      {!selected && workspace === "profile" && profile ? <form className="expert-profile-form" onSubmit={event => { event.preventDefault(); saveProfile.mutate(); }}>
        <div className="avatar-upload">
          <span>{avatarPreview ? <img src={avatarPreview} alt="专家头像"/> : profile.display_name.slice(0, 1)}</span>
          <label><strong>{uploadAvatar.isPending ? "正在处理照片…" : "上传专家照片"}</strong><small>支持 JPG、PNG、WebP，最大 5MB</small><input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => { const file = e.target.files?.[0]; if (file) uploadAvatar.mutate(file); }}/></label>
        </div>
        {uploadAvatar.isError && <p className="error">{(uploadAvatar.error as Error).message}</p>}
        <label>展示姓名<input value={profile.display_name} onChange={e => setProfile({...profile, display_name:e.target.value})}/></label>
        <label>专业头衔<input value={profile.title} onChange={e => setProfile({...profile, title:e.target.value})}/></label>
        <label>擅长领域<input value={profile.specialties.join("、")} onChange={e => setProfile({...profile, specialties:e.target.value.split(/[、,，]/).map(v => v.trim()).filter(Boolean)})} placeholder="语言发展、情绪行为、生活技能"/></label>
        <label>个人简介<textarea value={profile.bio} onChange={e => setProfile({...profile, bio:e.target.value})} placeholder="介绍你的服务方式和经验"/></label>
        <label>资质与经历<textarea value={profile.credentials} onChange={e => setProfile({...profile, credentials:e.target.value})} placeholder="填写可核验的培训、认证或从业经历"/></label>
        <label>最多服务客户数<input type="number" min={1} max={200} value={profile.max_clients} onChange={e => setProfile({...profile, max_clients:Number(e.target.value)})}/></label>
        <label className="accepting-toggle"><input type="checkbox" checked={profile.accepting_clients} onChange={e => setProfile({...profile, accepting_clients:e.target.checked})}/><span><strong>接收新客户</strong><small>关闭后不会出现在新家长的可选列表中</small></span></label>
        <button className="save-profile" disabled={saveProfile.isPending}>{saveProfile.isSuccess ? "资料已保存" : "保存专家资料"}</button>
      </form> : !selected ? <>
        <div className="expert-summary"><Inbox/><div><strong>{clientData?.items.length || 0}</strong><span>位签约客户</span></div><div><strong>{clientData?.items.reduce((sum, item) => sum + item.unread, 0) || 0}</strong><span>条待回复</span></div></div>
        <h2>客户咨询</h2>
        <div className="client-list">{clientData?.items.map(client => <button key={client.id} onClick={() => setSelected(client)}>
          <span className="expert-avatar">{client.name.slice(0, 1)}</span>
          <span><strong>{client.name}</strong><small>{client.latest || "尚未发送问题"}</small></span>
          {client.unread > 0 ? <b>{client.unread}</b> : <ChevronRight/>}
        </button>)}</div>
        {!clientData?.items.length && <div className="empty-inbox"><Inbox/><strong>还没有客户咨询</strong><p>家长选择你并发送问题后，会出现在这里。</p></div>}
        <button className="expert-logout" onClick={logout}>退出登录</button>
      </> : <>
        <div className="expert-conversation">{messages?.items.map(item => <div className={`expert-bubble ${item.sender}`} key={item.id}>{item.content}<small>{item.sender === "expert" ? "我" : selected.name}</small></div>)}</div>
        <div className="expert-reply"><textarea value={reply} onChange={e => setReply(e.target.value)} placeholder="输入给家长的回复…"/><button onClick={() => sendReply.mutate()} disabled={!reply.trim() || sendReply.isPending}><Send/>发送回复</button></div>
        <button className="close-consultation" onClick={() => closeConsultation.mutate()} disabled={closeConsultation.isPending}>结束本次咨询关系</button>
      </>}
    </section>
  </main>;
}

function NetworkStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const connected = () => setOnline(true);
    const disconnected = () => setOnline(false);
    window.addEventListener("online", connected);
    window.addEventListener("offline", disconnected);
    return () => {
      window.removeEventListener("online", connected);
      window.removeEventListener("offline", disconnected);
    };
  }, []);
  return online ? null : <div className="network-status"><WifiOff/>当前网络不可用，评估草稿仍会保存在本机</div>;
}

function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(api.tokenStore.access || api.tokenStore.refresh));
  const [mode, setMode] = useState<ProductMode>(() => (localStorage.getItem("aba_product_mode") as ProductMode) || "aba");
  const [tab, setTab] = useState<Tab>("home");
  const { data: user, isError } = useQuery({ queryKey: ["me"], queryFn: api.me, enabled: authenticated });
  const { data: children = [] } = useQuery({ queryKey: ["children"], queryFn: api.children, enabled: Boolean(user && user.role !== "expert") });
  const child = useMemo(() => children.find(item => item.is_current) || children[0], [children]);
  const chooseMode = (next: ProductMode) => {
    setMode(next);
    localStorage.setItem("aba_product_mode", next);
  };
  const logout = () => { api.tokenStore.clear(); setAuthenticated(false); };
  if (!authenticated || isError) return <Auth mode={mode} setMode={chooseMode} onDone={() => { setAuthenticated(true); queryClient.invalidateQueries(); }} />;
  if (!user) return <main className="loading"><Sparkles/> 正在准备你的家庭空间…</main>;
  if (user.role === "expert") return <ExpertApp username={user.username} logout={logout}/>;
  if (user.role === "admin") return <main className="auth"><div className="brand-mark"><ShieldCheck/></div><p className="eyebrow">管理员账户</p><h1>请进入系统管理后台</h1><p className="muted">管理员与家长、专家工作空间已完全分开。</p><button className="primary" onClick={() => location.href = "/admin/"}>打开管理后台</button><button className="danger" onClick={logout}>退出登录</button></main>;
  if (mode === "coach") return <CoachApp username={user.username} switchToAba={() => chooseMode("aba")} logout={logout} />;
  if (!child) return <main className="shell"><EmptyChild done={() => setTab("home")} /></main>;
  const content = {
    home: <HomePage child={child} go={setTab}/>,
    child: <ChildPage child={child}/>,
    training: <TrainingPage child={child}/>,
    progress: <ProgressPage child={child}/>,
    me: <section className="me-page"><div className="avatar large">{user.username.slice(0, 1)}</div><h1>{user.username}</h1><p>星星家庭成员</p><button className="card product-switch-card" onClick={() => chooseMode("coach")}><MessageCircleHeart/><span>进入家长陪伴<small>情绪支持、成长练习与反思日记</small></span><ChevronRight/></button><button className="danger" onClick={logout}>退出登录</button></section>
  }[tab];
  const nav = [
    ["home", "首页", Home], ["child", "孩子", Baby], ["training", "训练", Target],
    ["progress", "进展", BarChart3], ["me", "我的", CircleUserRound]
  ] as const;
  return <main className="shell"><div className="content">{content}</div><nav>{nav.map(([id, label, Icon]) =>
    <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon/><span>{label}</span></button>)}</nav></main>;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><QueryClientProvider client={queryClient}><NetworkStatus/><App/></QueryClientProvider></React.StrictMode>
);
