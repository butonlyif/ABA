import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Baby, BarChart3, BookOpen, Camera, Check, ChevronLeft, ChevronRight, CircleUserRound, Download, Dumbbell, Home, Inbox, MessageCircleHeart, PenLine, Play, Plus, RefreshCw, Send, ShieldCheck, Shuffle, Smile, Sprout, Target, UserRoundCheck, WifiOff } from "lucide-react";
import { api, Child, ExpertClient, ExpertProfile, Report, Session, SkillTemplate, Task, TrialResult } from "./api";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 2 * 60_000,
      refetchOnWindowFocus: false,
    },
  },
});
function invalidateChildren(client = queryClient) {
  client.invalidateQueries({ queryKey: ["children"] });
  client.invalidateQueries({ queryKey: ["bootstrap"] });
}
type Tab = "home" | "child" | "training" | "progress" | "me";
type ProductMode = "aba" | "coach";

function formatChatTimestamp(value: string | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ACT 六步法：以一个问题为单位发起的 session
type ActStepKey = "awareness" | "acceptance" | "defusion" | "present" | "values" | "action";
type ActMode = "quick" | "full";
type ActActionStatus = "planned" | "tried" | "completed" | "blocked";
type ActSession = {
  id: string;
  problem: string;
  mode: ActMode;
  steps: Record<ActStepKey, { reflection: string; completedAt: string | null }>;
  resolution: { solved: boolean | null; note: string; updatedAt: string | null };
  actionPlan: {
    value: string;
    action: string;
    fallback: string;
    when: string;
    status: ActActionStatus;
    obstacle: string;
    updatedAt: string | null;
  } | null;
  status: "in_progress" | "completed";
  createdAt: string;
  updatedAt: string;
};

const ACT_STEPS: { key: ActStepKey; name: string; prompt: string; placeholder: string; starters: string[] }[] = [
  { key: "awareness", name: "先看看发生了什么", prompt: "不用分析原因。你可以写发生的事、脑中的念头、身体感觉，或者只是“说不清但很难受”。", placeholder: "想到什么就写什么，不需要完整。", starters: ["发生的事是……", "我脑子里一直在想……", "身体最明显的是……", "我说不清，只觉得……"] },
  { key: "acceptance", name: "先不急着赶走它", prompt: "此刻最想摆脱或躲开的是什么？不要求喜欢它，只试着让它暂时存在一小会儿。", placeholder: "例如：我不喜欢这种感觉，但现在先不和它较劲。", starters: ["我最想躲开的是……", "我可以先允许……", "现在还做不到接纳，但我注意到……"] },
  { key: "defusion", name: "听见脑中的声音", prompt: "这件事出现时，脑中反复播放的是什么？可以是一句话、一个画面、一种担心，也可以是想立刻做某事的冲动。", placeholder: "例如：我注意到，我脑子里又出现了“我肯定做不好”的声音。", starters: ["脑中反复的一句话是……", "我总看到一个画面……", "我担心的是……", "我很想立刻……"] },
  { key: "present", name: "回到眼前这一刻", prompt: "不用强迫自己平静。看看现在能注意到什么：眼前的东西、听到的声音、身体接触到的地方，选一个即可。", placeholder: "例如：我能感觉到后背靠着椅子，听见空调的声音。", starters: ["我现在看见……", "我现在听见……", "身体接触到……", "我注意到呼吸……"] },
  { key: "values", name: "选择想靠近的方向", prompt: "在这件事里，你希望自己更靠近怎样的状态或做法？不需要成为某种完美的人。", placeholder: "例如：更诚实一点、更照顾自己一点、说话慢一点。", starters: ["我想更靠近……", "对我重要的是……", "哪怕很难，我仍想……"] },
  { key: "action", name: "带走一个很小的动作", prompt: "现在的条件下，哪件事能在两分钟内开始？不是解决整个问题，只是让自己向想要的方向移动一点。", placeholder: "例如：喝一杯水、发一条消息、写下明天要说的第一句话。", starters: ["我现在可以先……", "如果只做两分钟，我会……", "条件不够时，我可以改成……"] }
];

function actStepGuidance(step: typeof ACT_STEPS[number], session: ActSession) {
  const problem = session.problem.length > 42 ? `${session.problem.slice(0, 42)}…` : session.problem;
  const awareness = session.steps.awareness.reflection;
  const defusion = session.steps.defusion.reflection;
  const values = session.steps.values.reflection;
  const context = awareness || problem;
  const guidance: Partial<Record<ActStepKey, { prompt: string; starters: string[]; placeholder: string }>> = {
    awareness: {
      prompt: `先只看「${problem}」发生时的真实反应，不分析谁对谁错。事情、念头、身体感觉，写一个就够。`,
      starters: [`当「${problem}」出现时，我先注意到……`, "我脑子里马上想到……", "身体最明显的是……"],
      placeholder: `围绕“${problem}”，写下最先出现的反应。`,
    },
    acceptance: {
      prompt: `刚才你写到「${context.slice(0, 48)}${context.length > 48 ? "…" : ""}」。这一步不是认同它，只是暂时不花力气赶走它。`,
      starters: ["我最想马上摆脱的是……", "我可以让这种感觉先待一会儿……", "现在还做不到接纳，但我愿意先注意到……"],
      placeholder: "写下你最想躲开的感受，以及愿意给它留下多大一点空间。",
    },
    defusion: {
      prompt: `回到「${problem}」：脑中最容易让你被带着走的那句话、画面或冲动是什么？把它当成脑中出现的信息，而不是已经确定的事实。`,
      starters: ["关于这件事，我脑中反复说……", "我注意到自己正在担心……", "我又出现了想立刻……的冲动"],
      placeholder: "例如：我注意到，我脑中正在说“这一定会变糟”。",
    },
    present: {
      prompt: `即使「${problem}」还没有解决，也先把注意力放回此刻十秒。选一个眼前真实存在的声音、触感或物体。`,
      starters: ["此刻我能看见……", "此刻我能听见……", "身体接触到……"],
      placeholder: "只记录一个此刻能看到、听到或触到的东西。",
    },
    values: {
      prompt: `面对「${problem}」，先不问怎样才算完美。你希望自己的下一步更靠近哪种方向？`,
      starters: ["在这件事里，我想更靠近……", "即使脑中还有这些声音，我仍看重……", defusion ? "不跟着这个念头走时，我更愿意……" : "对我真正重要的是……"],
      placeholder: "例如：照顾自己、诚实表达、保持边界、耐心一点。",
    },
    action: {
      prompt: `你想靠近的是「${(values || "对自己重要的方向").slice(0, 40)}」。针对「${problem}」，现在能开始的最小动作是什么？只要两分钟内可以启动。`,
      starters: ["我现在先做……", "如果只做两分钟，我会……", "条件不够时，我把它缩小为……"],
      placeholder: "写一个具体动作：什么时候、做什么，尽量不依赖别人先改变。",
    },
  };
  return guidance[step.key] || step;
}

function newActSession(problem: string, mode: ActMode = "full"): ActSession {
  const now = new Date().toISOString();
  return {
    id: (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`),
    problem,
    mode,
    steps: ACT_STEPS.reduce((acc, step) => {
      acc[step.key] = { reflection: "", completedAt: null };
      return acc;
    }, {} as ActSession["steps"]),
    resolution: { solved: null, note: "", updatedAt: null },
    actionPlan: null,
    status: "in_progress",
    createdAt: now,
    updatedAt: now
  };
}

// ─── OSKAR session（解决方案聚焦 · 交互式自助）───
type OskarStepKey = "outcome" | "scale" | "knowhow" | "action" | "review";
type OskarSession = {
  id: string;
  topic: string;
  steps: Record<OskarStepKey, { reflection: string; completedAt: string | null }>;
  smallAction: { description: string; when: string; status: "planned" | "tried" | "done"; note: string; updatedAt: string | null } | null;
  status: "in_progress" | "completed";
  createdAt: string;
  updatedAt: string;
};

const OSKAR_STEPS: { key: OskarStepKey; name: string; shortLabel: string; prompt: string; placeholder: string; starters: string[] }[] = [
  {
    key: "outcome",
    name: "O · 你想要的是什么？",
    shortLabel: "成果",
    prompt: `假如一夜之间事情好转了一点，明天早上你会先注意到什么不同？不用想\u201C全部解决\u201D，只要一个具体的、你能看得见的信号。`,
    placeholder: "例如：我会发现自己早上没有先看手机，而是直接去厨房。",
    starters: ["我会注意到自己……", "别人会看到我……", "最明显的不同是……"],
  },
  {
    key: "scale",
    name: "S · 0-10 你现在在几？",
    shortLabel: "量尺",
    prompt: `如果 0 是\u201C完全没开始\u201D，10 是\u201C已经到了你刚才描述的画面\u201D——你现在大概在几？为什么是这个数，而不是更低？`,
    placeholder: "例如：大概 4 分。因为上周有两天我已经做到了。",
    starters: ["我现在大概在……", "之所以不是更低，是因为……", "让我到这个分的是……"],
  },
  {
    key: "knowhow",
    name: "K · 你手里已有的筹码",
    shortLabel: "资源",
    prompt: "这个想要的状态，什么时候已经发生过，哪怕只有一点点？你当时做了什么让它发生的？",
    placeholder: "例如：上周末孩子发脾气时，我先喝了口水再回应——那一次没吵起来。",
    starters: ["有一次……", "我之前试过……", "帮我做到的是……", "我其实擅长……"],
  },
  {
    key: "action",
    name: "A · 选一小步",
    shortLabel: "行动",
    prompt: "不要求大计划。如果只上升一分，你接下来可以做的一个最小动作是什么？两分钟内能开始的，由你来选。",
    placeholder: "例如：今晚花 2 分钟把明天要穿的衣服准备好。",
    starters: ["我接下来可以先……", "上升一分的话……", "两分钟内能做的……"],
  },
  {
    key: "review",
    name: "R · 什么变好了？",
    shortLabel: "回顾",
    prompt: "过几天回来看看：什么变好了？你做了什么带来了这个改变？（即使很小的变化也值得记下）",
    placeholder: "例如：试了三天，有两天做到了。变好的是我没那么急了。",
    starters: ["变好的是……", "我注意到……", "我做了……", "下次可以……"],
  },
];

function newOskarSession(topic: string): OskarSession {
  const now = new Date().toISOString();
  return {
    id: (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`),
    topic,
    steps: OSKAR_STEPS.reduce((acc, step) => {
      acc[step.key] = { reflection: "", completedAt: null };
      return acc;
    }, {} as OskarSession["steps"]),
    smallAction: null,
    status: "in_progress",
    createdAt: now,
    updatedAt: now,
  };
}

function OskarStepForm({ step, session, index, total, onSave, onToJournal }: { step: typeof OSKAR_STEPS[number]; session: OskarSession; index: number; total: number; onSave: (reflection: string) => void; onToJournal: () => void }) {
  const [text, setText] = useState("");
  return <div className="act-step-form">
    <p className="eyebrow">第 {index + 1} 步 / 共 {total} 步 · OSKAR</p>
    <h3>{step.name}</h3>
    <div className="act-context-prompt"><small>结合你刚才提到的事</small><p>{step.prompt}</p></div>
    <div className="act-starter-section">
      <span>不知道怎么开头？可以点一句再修改</span>
      <div className="act-starters">
        {step.starters.map(starter => <button onClick={() => setText(starter)} key={starter}>{starter}</button>)}
      </div>
    </div>
    <label className="act-answer-label">你的记录<textarea value={text} onChange={e => setText(e.target.value)} placeholder={step.placeholder} rows={4}/></label>
    <div className="growth-detail-actions">
      <button className="primary" disabled={!text.trim()} onClick={() => onSave(text.trim())}>完成本步</button>
      <button className="text-button" onClick={onToJournal}>写进日记</button>
    </div>
  </div>;
}

function OskarSmallActionForm({ session, onSave }: { session: OskarSession; onSave: (action: NonNullable<OskarSession["smallAction"]>) => void }) {
  const [desc, setDesc] = useState(session.steps.action.reflection || "");
  const [when, setWhen] = useState("");
  return <div className="act-action-form">
    <h3 className="coach-section-head">确认你的一小步</h3>
    <p className="muted small">不需要完美计划。选择一个在现实条件下仍能开始的动作。</p>
    <label>你的一小步是<textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="例如：今晚花2分钟把明天要穿的衣服准备好" rows={2}/></label>
    <label>准备什么时候做<input value={when} onChange={e => setWhen(e.target.value)} placeholder="例如：今晚睡前 / 明天早上"/></label>
    <button className="primary" disabled={!desc.trim()} onClick={() => onSave({ description: desc.trim(), when: when.trim(), status: "planned", note: "", updatedAt: new Date().toISOString() })}>保存行动卡</button>
  </div>;
}

function OskarActionCard({ session, onStatus, onRestart }: { session: OskarSession; onStatus: (status: "tried" | "done", note?: string) => void; onRestart: () => void }) {
  const plan = session.smallAction!;
  return <div className="act-action-card">
    <div className="act-action-head"><span>{plan.status === "done" ? "已完成" : plan.status === "tried" ? "已尝试" : "准备尝试"}</span><strong>一小步</strong></div>
    <p><small>最小行动</small>{plan.description}</p>
    {plan.when && <p><small>使用场景</small>{plan.when}</p>}
    {plan.note && <p><small>结果</small>{plan.note}</p>}
    <div className="act-status-actions">
      <button onClick={() => onStatus("done")}>做到了</button>
      <button onClick={() => onStatus("tried")}>尝试了</button>
    </div>
    <button className="text-button" onClick={onRestart}>针对同一话题再走一次</button>
  </div>;
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
  { group: "稳定", items: [{ key: "calm", label: "平静" }, { key: "relaxed", label: "放松" }, { key: "secure", label: "安心" }, { key: "content", label: "满足" }, { key: "grateful", label: "感激" }, { key: "warm", label: "温暖" }] },
  { group: "正向活力", items: [{ key: "joy", label: "愉悦" }, { key: "light", label: "轻松" }, { key: "excited", label: "兴奋" }, { key: "hopeful", label: "有希望" }, { key: "supported", label: "被支持" }, { key: "proud", label: "自豪" }] },
  { group: "警觉与不安", items: [{ key: "anxious", label: "焦虑" }, { key: "worried", label: "担心" }, { key: "afraid", label: "害怕" }, { key: "tense", label: "紧绷" }, { key: "restless", label: "烦躁" }, { key: "overwhelmed", label: "不堪重负" }] },
  { group: "低落与疲惫", items: [{ key: "sad", label: "低落" }, { key: "aggrieved", label: "委屈" }, { key: "lost", label: "失落" }, { key: "exhausted", label: "疲惫" }, { key: "empty", label: "空虚" }, { key: "lonely", label: "孤独" }] },
  { group: "压力与愤怒", items: [{ key: "angry", label: "愤怒" }, { key: "frustrated", label: "挫败" }, { key: "repressed", label: "压抑" }, { key: "resigned", label: "无奈" }, { key: "ashamed", label: "羞耻" }, { key: "guilty", label: "内疚" }] },
  { group: "迷茫", items: [{ key: "confused", label: "困惑" }, { key: "uncertain", label: "不确定" }, { key: "out_of_control", label: "失控" }, { key: "doubtful", label: "怀疑" }, { key: "numb", label: "麻木" }, { key: "helpless", label: "无助" }] }
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
const moodLabel = (key: string) => key.startsWith("custom:") ? key.slice(7) : MOOD_LABEL_MAP[key] || key;

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
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    const cleanUsername = username.trim();
    if (cleanUsername.length < 2) {
      setError("用户名至少需要 2 个字符");
      return;
    }
    if (signup && password.length < 8) {
      setError("密码至少需要 8 位");
      return;
    }
    if (!signup && password.length < 4) {
      setError("请输入完整密码");
      return;
    }
    setSubmitting(true);
    try {
      const tokens = await (signup ? api.register(cleanUsername, password) : api.login(cleanUsername, password));
      api.tokenStore.set(tokens);
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };
  return <main className="auth">
    <header className={`auth-intro ${mode}`}>
      <p className="eyebrow">星星家庭</p>
      <h1>{mode === "aba" ? "把每天的练习，慢慢变成看得见的进步" : "把心里的事说出来，给自己留一点空间"}</h1>
      <p>{mode === "aba" ? "记录训练、观察变化，并知道下一步做什么。" : "聊一聊、记一记，需要时再回来看看自己的变化。"}</p>
      <img
        src={mode === "aba" ? "/brand/aba-family-training.webp" : "/brand/coach-reflection.webp"}
        alt=""
        width="960"
        height="640"
      />
    </header>
    <form className="auth-card" onSubmit={submit}>
      <p className="entry-label">选择要进入的空间</p>
      <div className="entry-grid">
        <button type="button" className={`entry-option aba-entry ${mode === "aba" ? "selected" : ""}`} onClick={() => setMode("aba")}>
          <span><strong>ABA 家庭训练</strong><small>孩子档案 · 评估 · 训练 · 进展</small></span>
          <Check className="entry-check" />
        </button>
        <button type="button" className={`entry-option coach-entry ${mode === "coach" ? "selected" : ""}`} onClick={() => setMode("coach")}>
          <span><strong>家长陪伴</strong><small>交谈 · 情绪记录 · 成长练习</small></span>
          <Check className="entry-check" />
        </button>
      </div>
      <div className="segment">
        <button type="button" className={!signup ? "active" : ""} onClick={() => setSignup(false)}>登录</button>
        <button type="button" className={signup ? "active" : ""} onClick={() => setSignup(true)}>注册</button>
      </div>
      <label>用户名<input value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
      <label>密码<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete={signup ? "new-password" : "current-password"} /></label>
      {signup && <small className="muted">用户名至少 2 个字符，密码至少 8 位。</small>}
      {error && <p className="error">{error}</p>}
      <button className={`primary ${mode === "coach" ? "coach-primary" : ""}`} disabled={submitting}>
        {submitting ? "正在处理…" : signup ? "创建家庭账户" : mode === "coach" ? "进入家长陪伴" : "开始和皮特对话"}
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
    onSuccess: () => { invalidateChildren(query); done(); }
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
  const [src, setSrc] = useState("");
  const [errored, setErrored] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setSrc("");
    setErrored(false);
    api.childAvatar(child.id).then(url => {
      objectUrl = url;
      if (active) setSrc(url);
      else URL.revokeObjectURL(url);
    }).catch(() => active && setErrored(true));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [child.id, child.avatar_url, child.avatar_seed]);
  const showImage = Boolean(src) && !errored;
  return <div className="child-avatar" style={{ width: size, height: size }}>
    {showImage && <img src={src} alt={child.name} onError={() => setErrored(true)} />}
    {!showImage && <span className="child-avatar-fallback">{child.name.slice(0, 1)}</span>}
    {badge && <span className="child-avatar-badge" title="系统生成头像"><Check size={11}/></span>}
  </div>;
}

function AvatarUploader({ child }: { child: Child }) {
  const query = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.uploadChildAvatar(child.id, file),
    onSuccess: () => { setError(null); invalidateChildren(query); },
    onError: (e: Error) => { setError(`上传失败：${e.message}`); }
  });
  const regenerate = useMutation({
    mutationFn: () => api.regenerateChildAvatar(child.id),
    onSuccess: () => { setError(null); invalidateChildren(query); },
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
  const [pendingUserMessage, setPendingUserMessage] = useState("");
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [chatSendError, setChatSendError] = useState("");
  const abaThreadRef = useRef<HTMLDivElement>(null);
  const { data: history = [] } = useQuery({ queryKey: ["chat", "aba"], queryFn: () => api.chatMessages("aba") });
  const chat = useMutation({
    mutationFn: async (text: string) => {
      try { return await api.chatStream(text, child.id, setStreamedAnswer); }
      catch {
        const response = await api.chat(text, child.id);
        setStreamedAnswer(response.answer);
        return response.answer;
      }
    },
    onMutate: (text) => {
      setPendingUserMessage(text);
      setStreamedAnswer("");
      setChatSendError("");
      setMessage("");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["chat", "aba"] });
      setPendingUserMessage("");
      setStreamedAnswer("");
    },
    onError: (_error, text) => {
      setMessage(text);
      setChatSendError("没有发送成功，输入框已保留，可重新发送。");
    },
  });
  useEffect(() => {
    const thread = abaThreadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [history.length, pendingUserMessage, streamedAnswer, chatSendError]);
  const sendAbaMessage = () => {
    const text = message.trim();
    if (text && !chat.isPending) chat.mutate(text);
  };
  const clearChat = useMutation({ mutationFn: () => api.clearChatMessages("aba"), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chat", "aba"] }) });
  const { data: expertData } = useQuery({ queryKey: ["experts"], queryFn: api.experts });
  const { data: expertThread } = useQuery({ queryKey: ["expert-conversation"], queryFn: api.expertConversation, enabled: helpMode === "expert" });
  const { data: notificationData } = useQuery({ queryKey: ["notifications"], queryFn: api.notifications, refetchInterval: 10_000 });
  const { data: progressData } = useQuery({ queryKey: ["progress", child.id], queryFn: () => api.progress(child.id) });
  const daysSinceTraining = progressData?.last_training_at
    ? Math.floor((Date.now() - new Date(progressData.last_training_at).getTime()) / 86400000)
    : null;
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
    {(daysSinceTraining === null || daysSinceTraining >= 2) && <button className="training-reminder" onClick={() => go("training")}>
      <Target/><span><strong>{daysSinceTraining === null ? "可以开始第一次家庭训练" : `已经 ${daysSinceTraining} 天没有完整训练`}</strong><small>选择一个当前任务，完成5–10个回合即可计入趋势</small></span><ChevronRight/>
    </button>}

    {/* 问答主区域 — 占据大部分空间 */}
    <section className="home-chat">
      <div className="help-switch">
        <button className={helpMode === "ai" ? "active" : ""} onClick={() => setHelpMode("ai")}><MessageCircleHeart/>问皮特</button>
        <button className={helpMode === "expert" ? "active" : ""} onClick={() => setHelpMode("expert")}><UserRoundCheck/>问专家{Boolean(notificationData?.expert_unread) && <b>{notificationData!.expert_unread}</b>}</button>
      </div>
      {helpMode === "ai" ? <>
        <div className="chat-thread-header">
          <div className="section-title"><span>家庭训练问答</span><small>根据孩子的实际情况回答</small></div>
        </div>
        <div className="chat-thread home-thread" ref={abaThreadRef}>
          {history.length === 0 && !pendingUserMessage && <div className="editorial-empty aba-empty">
            <img src="/brand/aba-family-training.webp" alt="" width="960" height="640" loading="lazy"/>
            <div><strong>从一个具体场景开始</strong><p>说说刚才发生了什么、孩子怎么回应。你会得到可以在家尝试的步骤。</p></div>
          </div>}
          {history.map(item => <div className={`chat-bubble ${item.role}`} key={item.id}>
            <p>{item.content}</p>
            {item.role === "assistant" && item.sources?.length > 0 && <div className="chat-sources">{item.sources.map(s => <span key={s.title}>{s.title}</span>)}</div>}
            <time className="chat-message-time">{formatChatTimestamp(item.created_at)}</time>
          </div>)}
          {pendingUserMessage && <div className="chat-bubble user pending-message"><p>{pendingUserMessage}</p>{chatSendError && <small className="chat-send-error">{chatSendError}</small>}<time className="chat-message-time">刚刚</time></div>}
          {chat.isPending && <div className="chat-bubble assistant pending-reply">
            {streamedAnswer ? <p>{streamedAnswer}</p> : <span className="typing-dots" aria-label="正在回复"><i/><i/><i/></span>}
          </div>}
        </div>
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="描述一个具体场景…" onKeyDown={e => { if (e.key === "Enter") sendAbaMessage(); }} /><button onClick={sendAbaMessage} disabled={!message.trim() || chat.isPending}>发送</button></div>
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
  const { data: recordFiles = [] } = useQuery({
    queryKey: ["record-files", childId],
    queryFn: () => api.recordFiles(childId),
  });
  const import_file = useMutation({
    mutationFn: (file: File) => api.importRecord(childId, file),
    onSuccess: () => {
      setMsg("原始文件已保存，能力状态已更新");
      setMode(null);
      invalidateChildren();
      queryClient.invalidateQueries({ queryKey: ["record-files", childId] });
    },
    onError: (e: Error) => setMsg(`导入失败：${e.message}`),
  });
  const import_text = useMutation({
    mutationFn: () => api.importRecordText(childId, text),
    onSuccess: () => { setMsg("病例分析完成，状态已更新"); setText(""); setMode(null); invalidateChildren(); },
    onError: (e: Error) => setMsg(`分析失败：${e.message}`),
  });
  const remove_file = useMutation({
    mutationFn: (fileId: string) => api.deleteRecordFile(childId, fileId),
    onSuccess: () => {
      setMsg("原始文件已删除，已整理的能力状态保留");
      queryClient.invalidateQueries({ queryKey: ["record-files", childId] });
    },
    onError: (e: Error) => setMsg(`删除失败：${e.message}`),
  });
  return (
    <section className="record-import">
      <div className="record-head">
        <p className="eyebrow">导入病例</p>
        {!mode && <button className="text-button" onClick={() => setMode("file")}>上传文件</button>}
        {!mode && <button className="text-button" onClick={() => setMode("text")}>粘贴文本</button>}
      </div>
      {!mode && <p className="muted small">上传诊断报告、评估记录或病历（PDF/Word/TXT），系统会整理其中的能力信息并更新状态。</p>}
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
            {import_text.isPending ? "正在整理…" : "分析并更新状态"}
          </button>
          <button className="text-button" onClick={() => setMode(null)}>取消</button>
        </div>
      </>}
      {recordFiles.length > 0 && <div className="record-file-list">
        <p className="record-file-title">已保存的原始文件</p>
        {recordFiles.map(file => <div className="record-file-row" key={file.id}>
          <button className="record-file-name" onClick={() => api.downloadRecordFile(childId, file.id, file.original_name)}>
            <span>{file.original_name}</span>
            <small>{new Date(file.created_at).toLocaleDateString("zh-CN")} · {(file.size_bytes / 1024).toFixed(file.size_bytes < 1024 * 100 ? 1 : 0)} KB</small>
          </button>
          <button className="record-file-delete" disabled={remove_file.isPending} onClick={() => {
            if (window.confirm("只删除这个原始文件。已经整理出的孩子能力状态会继续保留，确定删除吗？")) {
              remove_file.mutate(file.id);
            }
          }}>删除</button>
        </div>)}
      </div>}
      {msg && <p className={`record-msg ${msg.includes("失败") ? "error" : ""}`}>{msg}</p>}
    </section>
  );
}

function ChildPage({ child }: { child: Child }) {
  const { data: allChildren = [] } = useQuery({ queryKey: ["children"], queryFn: api.children });
  const [showAdd, setShowAdd] = useState(false);
  const [newChildName, setNewChildName] = useState("");
  const switchChild = useMutation({ mutationFn: api.setCurrentChild, onSuccess: () => invalidateChildren() });
  const addChild = useMutation({ mutationFn: () => api.createChild({ name: newChildName }), onSuccess: data => {
    setNewChildName("");
    setShowAdd(false);
    switchChild.mutate(data.id);
    invalidateChildren();
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
      invalidateChildren();
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
    <div className="page-heading"><p className="eyebrow">能力评估</p><h1>完成评估，确定下一批训练任务</h1><p>根据孩子近两周的真实表现作答。不确定时选择“有时”，系统会保留当前进度。</p></div>
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
  const minimumTrials = 5;
  const trialOptions: { result: TrialResult; label: string }[] = [
    { result: "I", label: "独立" },
    { result: "V", label: "语言提示" },
    { result: "M", label: "示范" },
    { result: "P", label: "身体辅助" },
    { result: "E", label: "未完成" },
  ];
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
  const trial = useMutation({ mutationFn: (result: TrialResult) => api.addTrial(session!.id, result), onSuccess: setSession });
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

  if (session && session.status === "active") return <section className="training-live">
    <button className="back-link" onClick={() => setSession(null)}><ChevronLeft/> 返回任务列表</button>
    <p className="eyebrow">正在训练</p><h1>{session.skill_name}</h1>
    <div className="task-detail-desc">{(realTasks.find(t => t.name === session.skill_name) as Task)?.description || "每次呈现刺激后，记录孩子最少辅助下的反应。"}</div>
    <TrainingFlashcard skillName={session.skill_name}/>
    <div className="score-ring"><strong>{session.percentage}%</strong><small>独立正确</small></div>
    <div className={`training-dose ${session.trials.length >= minimumTrials ? "ready" : ""}`}>
      <strong>{Math.min(session.trials.length, minimumTrials)} / {minimumTrials}</strong>
      <span>{session.trials.length >= minimumTrials ? "已达到完整训练标准，可以结束或继续到10个回合" : `再记录 ${minimumTrials - session.trials.length} 个回合即可计入趋势`}</span>
    </div>
    <div className="trial-log" aria-label="本次训练记录">{session.trials.map((value, index) => {
      const option = trialOptions.find(item => item.result === value);
      return <span className={`trial ${value}`} title={option?.label} aria-label={`第${index + 1}次：${option?.label || value}`} key={index}>{value}</span>;
    })}</div>
    <div className="trial-buttons">
      {trialOptions.map(option =>
        <button className={`result-${option.result}`} disabled={trial.isPending} onClick={() => trial.mutate(option.result)} aria-label={option.label} key={option.result}>
          {option.result}<small>{option.label}</small>
        </button>
      )}
    </div>
    <button className="undo-trial" disabled={!session.trials.length || undo.isPending} onClick={() => undo.mutate()}>撤销上一条记录</button>
    <button className="primary" disabled={session.trials.length < minimumTrials || finish.isPending} onClick={() => finish.mutate()}>
      {session.trials.length < minimumTrials ? `至少完成 ${minimumTrials} 个回合` : "结束并保存训练"}
    </button>
  </section>;
  return <>
    <div className="page-heading"><p className="eyebrow">训练中心</p><h1>选择一项任务，完成 5–10 个回合</h1><p>达到 5 个回合后计入趋势；孩子疲惫或明显抗拒时可以提前停下。</p></div>
    <div className="training-tabs">
      <button className={view === "tasks" ? "active" : ""} onClick={() => setView("tasks")}>当前任务 ({activeTasks.length})</button>
      <button className={view === "flashcards" ? "active" : ""} onClick={() => setView("flashcards")}>图片卡</button>
    </div>
    {view === "tasks" && (activeTasks.length > 0 || completedTasks.length > 0) && <div className="task-list-toolbar">
      <span>{manageMode ? "编辑任务清单" : "任务清单"}</span>
      <button className={manageMode ? "task-edit-button active" : "task-edit-button"} onClick={() => setManageMode(!manageMode)} aria-pressed={manageMode}>
        {manageMode ? <><Check size={14}/> 完成</> : <><PenLine size={14}/> 编辑任务</>}
      </button>
    </div>}
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
            {!collapsed && items.map(task => {
            const isExpanded = expandedId === task.id;
            return <article key={task.id} className={`task-card compact expandable ${task.status}${isExpanded?" open":""}`}>
              <div className="task-row" onClick={() => setExpandedId(isExpanded ? null : task.id)}>
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
        {isLoading ? <div className="flashcard-loading"><RefreshCw size={24}/> 正在加载图片…</div> : image ? <img src={image} alt={`${matched.name} ${index + 1}`}/> : null}
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

function ReportsCenter({ child }: { child: Child }) {
  const { data: reports = [] } = useQuery({ queryKey: ["reports", child.id], queryFn: () => api.reports(child.id), refetchInterval: query => {
    const rows = query.state.data as any[] | undefined;
    return rows?.some(item => item.status === "pending") ? 1500 : false;
  }});
  const generate = useMutation({ mutationFn: () => api.generateReport(child.id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", child.id] }) });
  return <section className="card report-card">
    <div><p className="eyebrow">训练报告</p><h2>阶段总结与建议</h2><p>需要时生成，不占用日常进度页面。</p></div>
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
  </section>;
}

function ProgressPage({ child }: { child: Child }) {
  const { data, refetch } = useQuery({ queryKey: ["progress", child.id], queryFn: () => api.progress(child.id) });
  const trendLabel = { progress: "进步", stable: "稳定", regression: "可能回退", insufficient: "数据不足" } as const;
  const chartPoints = data?.weekly.map((week, index) => ({
    ...week,
    x: 24 + index * 92,
    y: week.independent_rate === null ? null : 128 - week.independent_rate,
  })) || [];
  const linePoints = chartPoints.filter(point => point.y !== null).map(point => `${point.x},${point.y}`).join(" ");
  const populatedWeeks = data?.weekly.filter(week => week.trials > 0) || [];
  const supportInsight = (() => {
    if (populatedWeeks.length < 2) {
      return { status: "insufficient", title: "再完成一周即可比较提示变化", message: "当前先展示已记录的五级结果分布，不对单周数据下趋势结论。" };
    }
    const previous = populatedWeeks[populatedWeeks.length - 2];
    const latest = populatedWeeks[populatedWeeks.length - 1];
    const rate = (week: typeof latest, results: ("I" | "V" | "M" | "P" | "E")[]) =>
      Math.round(results.reduce((sum, result) => sum + week.results[result], 0) / week.trials * 100);
    const independentDelta = rate(latest, ["I"]) - rate(previous, ["I"]);
    const highSupportDelta = rate(latest, ["M", "P"]) - rate(previous, ["M", "P"]);
    const incompleteDelta = rate(latest, ["E"]) - rate(previous, ["E"]);
    let status = "mixed";
    let title = "提示结构发生变化";
    if (independentDelta >= 5 && highSupportDelta <= -5) {
      status = "progress";
      title = "提示依赖正在下降";
    } else if (independentDelta <= -5 && highSupportDelta >= 5) {
      status = "regression";
      title = "提示依赖可能上升";
    } else if (Math.abs(independentDelta) < 5 && Math.abs(highSupportDelta) < 5) {
      status = "stable";
      title = "提示结构基本稳定";
    }
    const signed = (value: number) => `${value > 0 ? "+" : ""}${value}`;
    return {
      status,
      title,
      message: `独立完成 ${signed(independentDelta)}，示范/身体辅助 ${signed(highSupportDelta)}，未完成 ${signed(incompleteDelta)} 个百分点（${latest.trials} vs ${previous.trials} 个回合）。`,
    };
  })();
  return <>
    <div className="page-heading"><p className="eyebrow">成长进展</p><h1>先看结论，再看变化来自哪里</h1></div>
    <section className={`progress-conclusion ${data?.trend.status || "insufficient"}`}>
      <div><span>{data ? trendLabel[data.trend.status] : "正在分析"}</span><h2>{data?.trend.title || "正在读取训练记录"}</h2></div>
      <p>{data?.trend.message || "请稍候。"}</p>
      {data?.trend.delta !== null && data?.trend.delta !== undefined && <strong>{data.trend.delta > 0 ? "+" : ""}{data.trend.delta}<small>个百分点</small></strong>}
    </section>
    <section className="progress-rule">
      <strong>怎样形成有效趋势？</strong>
      <span>同一技能每次记录至少5个回合，建议完成5–10个；累计6次完整训练后，开始比较前后趋势。</span>
    </section>
    <div className="stats progress-stats">
      <article><strong>{data?.training_days || 0}</strong><span>训练天数</span></article>
      <article><strong>{data?.completed_sessions || 0}</strong><span>完整训练</span></article>
      <article><strong>{data?.average_percentage || 0}%</strong><span>总体独立率</span></article>
    </div>
    <section className="card progress-chart-card">
      <div className="section-title"><span>近4周独立完成率</span><button className="text-button" onClick={() => refetch()}>刷新</button></div>
      {!chartPoints.some(point => point.y !== null) ? <div className="progress-empty"><BarChart3/><p>完成训练后，这里会形成每周趋势。</p></div> :
        <svg className="progress-line-chart" viewBox="0 0 324 168" role="img" aria-label="近4周独立完成率趋势">
          {[28, 78, 128].map((y, index) => <g key={y}><line x1="24" y1={y} x2="300" y2={y}/><text x="2" y={y + 4}>{100 - index * 50}</text></g>)}
          {linePoints && <polyline points={linePoints}/>}
          {chartPoints.map(point => <g className={point.y === null ? "empty" : ""} key={point.week_start}>
            {point.y !== null && <><circle cx={point.x} cy={point.y} r="5"/><text className="value" x={point.x} y={point.y - 10}>{point.independent_rate}%</text></>}
            <text className="label" x={point.x} y="153">{point.label}</text>
            <text className="sessions" x={point.x} y="166">{point.sessions ? `${point.sessions}次` : "无训练"}</text>
          </g>)}
        </svg>}
    </section>
    <section className="card support-chart-card">
      <div className="section-title"><span>提示结构变化</span><small>最近4周</small></div>
      <div className="support-legend">
        {[["I", "独立"], ["V", "语言"], ["M", "示范"], ["P", "身体"], ["E", "未完成"]].map(([result, label]) =>
          <span className={`result-${result}`} key={result}><i/>{label}</span>)}
      </div>
      <div className="support-bars">{data?.weekly.map(week => <div className="support-week" key={week.week_start}>
        <span>{week.label}</span>
        {week.trials ? <div className="support-stack" aria-label={`${week.label}，共${week.trials}个回合`}>
          {(["I", "V", "M", "P", "E"] as const).map(result => {
            const width = week.results[result] / week.trials * 100;
            return width > 0 ? <i className={`result-${result}`} style={{ width: `${width}%` }} title={`${result} ${Math.round(width)}%`} key={result}/> : null;
          })}
        </div> : <div className="support-stack empty"><em>无训练</em></div>}
        <small>{week.trials ? `${week.trials}回合` : "—"}</small>
      </div>)}</div>
      <div className={`support-insight ${supportInsight.status}`}>
        <strong>{supportInsight.title}</strong><span>{supportInsight.message}</span>
      </div>
    </section>
    <section className="card skill-change-card">
      <div className="section-title"><span>技能变化</span><small>近28天 vs 前28天</small></div>
      {!data?.skills.length ? <p className="muted">有更多训练后，会按技能显示进步或回退。</p> :
        <div className="skill-change-list">{data.skills.map(skill => <div className="skill-change-row" key={skill.skill_name}>
          <div><strong>{skill.skill_name}</strong><small>近28天 {skill.current_sessions} 次训练</small></div>
          <span className="skill-rate">{skill.current_rate === null ? "—" : `${skill.current_rate}%`}</span>
          <span className={`skill-status ${skill.status}`}>
            {skill.status === "insufficient" ? "数据不足" : `${trendLabel[skill.status]}${skill.delta !== null && skill.delta !== 0 ? ` ${skill.delta > 0 ? "+" : ""}${skill.delta}` : ""}`}
          </span>
        </div>)}</div>}
    </section>
  </>;
}

function MePage({ username, child, switchToCoach, logout }: { username: string; child: Child; switchToCoach: () => void; logout: () => void }) {
  return <section className="me-page">
    <div className="me-profile"><div className="avatar large">{username.slice(0, 1)}</div><div><p className="eyebrow">我的家庭空间</p><h1>{username}</h1><span>{child.name}的家长</span></div></div>
    <section className="me-guide">
      <div><Target/><span><strong>每次训练</strong><small>同一技能5–10个回合</small></span></div>
      <div><BarChart3/><span><strong>趋势判断</strong><small>累计6次完整训练</small></span></div>
    </section>
    <button className="card product-switch-card" onClick={switchToCoach}><MessageCircleHeart/><span>进入家长陪伴<small>情绪支持、成长练习与反思日记</small></span><ChevronRight/></button>
    <ReportsCenter child={child}/>
    <button className="danger" onClick={logout}>退出登录</button>
  </section>;
}

const ACT_BLOCKERS = [
  ["没时间", "把这一步缩小为一句话，先保留方向。"],
  ["情绪太强", "先停30秒，感受双脚与呼吸，不要求自己马上平静。"],
  ["对方不在", "先写下最想表达的一句话，作为准备动作。"],
  ["不知道怎么做", "先选择一个自己能控制、两分钟内能开始的动作。"],
  ["当前不安全", "先停止练习，离开危险情境并联系可信任的人或现实支持。"],
] as const;

function ActStepForm({ step, session, index, total, onSave, onBlocked, onToJournal }: { step: { key: ActStepKey; name: string; prompt: string; placeholder: string; starters: string[] }; session: ActSession; index: number; total: number; onSave: (reflection: string) => void; onBlocked: (reason: string, fallback: string) => void; onToJournal: () => void }) {
  const [text, setText] = useState("");
  const [showBlockers, setShowBlockers] = useState(false);
  const guidance = actStepGuidance(step, session);
  return <div className="act-step-form">
    <p className="eyebrow">第 {index + 1} 步 / 共 {total} 步</p>
    <h3>{step.name}</h3>
    <div className="act-context-prompt"><small>结合你刚才提出的事</small><p>{guidance.prompt}</p></div>
    <div className="act-starter-section">
      <span>不知道怎么开头？可以点一句再修改</span>
      <div className="act-starters">
        {guidance.starters.map(starter => <button onClick={() => setText(starter)} key={starter}>{starter}</button>)}
      </div>
    </div>
    <label className="act-answer-label">你的记录<textarea value={text} onChange={e => setText(e.target.value)} placeholder={guidance.placeholder} rows={4}/></label>
    <div className="growth-detail-actions">
      <button className="primary" disabled={!text.trim()} onClick={() => onSave(text.trim())}>完成本步</button>
      <button className="text-button" onClick={() => setShowBlockers(!showBlockers)}>现在做不到</button>
      <button className="text-button" onClick={onToJournal}>写进日记</button>
    </div>
    {showBlockers && <div className="act-blockers">
      <strong>是什么让这一步暂时做不到？</strong>
      {ACT_BLOCKERS.map(([reason, fallback]) => <button onClick={() => onBlocked(reason, fallback)} key={reason}><span>{reason}</span><small>{fallback}</small></button>)}
    </div>}
  </div>;
}

function ActActionPlanForm({ session, onSave }: { session: ActSession; onSave: (plan: NonNullable<ActSession["actionPlan"]>) => void }) {
  const [value, setValue] = useState(session.steps.values.reflection);
  const [action, setAction] = useState(session.steps.action.reflection);
  const [fallback, setFallback] = useState("");
  const [when, setWhen] = useState("");
  return <div className="act-action-form">
    <h3 className="coach-section-head">形成最小行动卡</h3>
    <p className="muted small">问题不需要先消失。选择一个在现实条件下仍能开始的动作。</p>
    <label>我想靠近的方向<input value={value} onChange={e => setValue(e.target.value)} placeholder="例如：耐心、稳定、诚实"/></label>
    <label>两分钟内能开始的行动<textarea value={action} onChange={e => setAction(e.target.value)} placeholder="例如：孩子哭闹时，先停10秒再回应" rows={2}/></label>
    <label>如果条件不满足，就缩小为<textarea value={fallback} onChange={e => setFallback(e.target.value)} placeholder="例如：只把声音降低，不要求自己马上平静" rows={2}/></label>
    <label>准备在什么时候尝试<input value={when} onChange={e => setWhen(e.target.value)} placeholder="例如：今晚睡前 / 下次出现哭闹时"/></label>
    <button className="primary" disabled={!value.trim() || !action.trim() || !fallback.trim()} onClick={() => onSave({
      value: value.trim(), action: action.trim(), fallback: fallback.trim(), when: when.trim(),
      status: "planned", obstacle: "", updatedAt: new Date().toISOString(),
    })}>保存行动卡</button>
  </div>;
}

function ActActionCard({ session, onStatus, onRestart }: { session: ActSession; onStatus: (status: ActActionStatus, obstacle?: string) => void; onRestart: () => void }) {
  const plan = session.actionPlan!;
  return <div className="act-action-card">
    <div className="act-action-head"><span>{plan.status === "completed" ? "已完成" : plan.status === "tried" ? "已尝试" : plan.status === "blocked" ? "条件未满足" : "准备尝试"}</span><strong>{plan.value}</strong></div>
    <p><small>最小行动</small>{plan.action}</p>
    <p><small>条件不满足时</small>{plan.fallback}</p>
    {plan.when && <p><small>使用场景</small>{plan.when}</p>}
    {plan.obstacle && <p><small>遇到的障碍</small>{plan.obstacle}</p>}
    <div className="act-status-actions">
      <button onClick={() => onStatus("completed")}>做到了</button>
      <button onClick={() => onStatus("tried")}>尝试了</button>
      <button onClick={() => onStatus("blocked", "原计划条件未满足，下一次先使用缩小行动。")}>条件未满足</button>
    </div>
    <button className="text-button" onClick={onRestart}>针对同一问题再走一次</button>
  </div>;
}

function ActResultForm({ session, onSave }: { session: ActSession; onSave: (solved: boolean, note: string) => void }) {
  const [solved, setSolved] = useState<boolean | null>(session.resolution.solved);
  const [note, setNote] = useState(session.resolution.note);
  return <div className="act-result-form">
    <p className="eyebrow">结束这张行动卡</p>
    <h3>这次行动最后带来了什么？</h3>
    <p className="muted small">行动做到了、只做了一部分或条件没满足，都可以如实记录。提交结果后，这张卡才会归入历史。</p>
    <div className="act-result-picker">
      <button className={solved === true ? "selected" : ""} onClick={() => setSolved(true)}>有一点帮助</button>
      <button className={solved === false ? "selected" : ""} onClick={() => setSolved(false)}>没有达到预期</button>
    </div>
    <textarea value={note} onChange={e => setNote(e.target.value)} placeholder="可选：发生了什么？下次想保留或调整什么？" rows={3}/>
    <button className="primary" disabled={solved === null} onClick={() => onSave(solved!, note.trim())}>提交结果并结束行动</button>
  </div>;
}

function CoachApp({ username, switchToAba, logout }: { username: string; switchToAba: () => void; logout: () => void }) {
  type CoachTab = "chat" | "emotion" | "growth" | "record" | "knowledge";
  type RecordSubTab = "journal" | "weekly";
  const [tab, setTab] = useState<CoachTab>("chat");
  const [recordSub, setRecordSub] = useState<RecordSubTab>("journal");
  const [message, setMessage] = useState("");
  const [pendingCoachMessage, setPendingCoachMessage] = useState("");
  const [coachSendError, setCoachSendError] = useState("");
  const coachThreadRef = useRef<HTMLDivElement>(null);
  // 情绪多维记录（今日）
  const [moodDetail, setMoodDetail] = useState<MoodDetail>({ emotions: ["calm"], intensity: 3, triggers: [], body: [], coping: "" });
  const [customEmotion, setCustomEmotion] = useState("");
  const [showAllMoods, setShowAllMoods] = useState(false);
  const [journal, setJournal] = useState("");
  const [articleId, setArticleId] = useState<string | null>(null);
  // ACT 六步法：以「一个问题」为单位发起一个 session，可随时再来一次
  // session = { id, problem, steps: [{ key, reflection, completedAt }], resolution, createdAt, updatedAt, status }
  const ACT_SESSIONS_KEY = `coach_act_sessions:${username}`;
  const [actSessions, setActSessions] = useState<ActSession[]>(() => {
    try {
      const scoped = localStorage.getItem(ACT_SESSIONS_KEY);
      const legacy = localStorage.getItem("coach_act_sessions");
      const raw = scoped || legacy;
      if (!scoped && legacy) localStorage.setItem(ACT_SESSIONS_KEY, legacy);
      if (raw) return (JSON.parse(raw) as ActSession[]).map(session => ({
        ...session,
        mode: session.mode || "full",
        actionPlan: session.actionPlan || null,
        resolution: session.resolution || { solved: null, note: "", updatedAt: null },
      }));
    } catch { /* ignore */ }
    return [];
  });
  useEffect(() => {
    try { localStorage.setItem(ACT_SESSIONS_KEY, JSON.stringify(actSessions)); } catch { /* ignore */ }
  }, [actSessions]);
  // OSKAR session（解决方案聚焦 · 本地持久化）
  const OSKAR_SESSIONS_KEY = `coach_oskar_sessions:${username}`;
  const [oskarSessions, setOskarSessions] = useState<OskarSession[]>(() => {
    try {
      const raw = localStorage.getItem(OSKAR_SESSIONS_KEY);
      if (raw) return JSON.parse(raw) as OskarSession[];
    } catch { /* ignore */ }
    return [];
  });
  useEffect(() => {
    try { localStorage.setItem(OSKAR_SESSIONS_KEY, JSON.stringify(oskarSessions)); } catch { /* ignore */ }
  }, [oskarSessions]);
  const [activeOskarId, setActiveOskarId] = useState<string | null>(null);
  const [oskarTopic, setOskarTopic] = useState("");
  const [growthHydrated, setGrowthHydrated] = useState(false);
  useEffect(() => {
    let active = true;
    api.growthSessions().then(remote => {
      if (!active) return;
      setActSessions(local => {
        const merged = new Map<string, ActSession>();
        for (const session of remote.sessions as ActSession[]) merged.set(session.id, session);
        for (const session of local) {
          const saved = merged.get(session.id);
          if (!saved || session.updatedAt > saved.updatedAt) merged.set(session.id, session);
        }
        return Array.from(merged.values()).map(session => ({
          ...session,
          mode: session.mode || "full",
          actionPlan: session.actionPlan || null,
          resolution: session.resolution || { solved: null, note: "", updatedAt: null },
        }));
      });
      setGrowthHydrated(true);
    }).catch(() => {
      if (active) setGrowthHydrated(true);
    });
    return () => { active = false; };
  }, [username]);
  useEffect(() => {
    if (!growthHydrated) return;
    const timer = window.setTimeout(() => {
      api.saveGrowthSessions(actSessions).catch(() => { /* local copy remains available for retry */ });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [actSessions, growthHydrated]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showAllActHistory, setShowAllActHistory] = useState(false);
  const [newProblem, setNewProblem] = useState("");
  const [actMode, setActMode] = useState<ActMode>("quick");
  // Growth 成长方法选择
  type GrowthModality = "act" | "oskar" | "ifs" | "cbt" | "dbt";
  const [growthModality, setGrowthModality] = useState<GrowthModality | null>(null);
  // 方法卡片定义
  const MODALITY_CARDS: { id: GrowthModality; name: string; icon: string; desc: string; color: string; bg: string; tag: string }[] = [
    { id: "act", name: "ACT 接纳承诺", icon: "🧘", desc: "接纳情绪，与念头拉开距离，从紧绷回到可选择的状态", color: "#C4884D", bg: "#fdf6ed", tag: "情绪接纳" },
    { id: "oskar", name: "OSKAR 方案聚焦", icon: "🎯", desc: "聚焦想要的未来，找到你已经有的筹码，选一小步往前走", color: "#5B9BD5", bg: "#edf5fc", tag: "行动导向" },
    { id: "ifs", name: "IFS 内在对话", icon: "🧩", desc: "倾听内在不同「部分」的声音，理解它们的意图，找到内在平衡", color: "#7B68AE", bg: "#f5f2fa", tag: "部分工作" },
    { id: "cbt", name: "CBT 认知练习", icon: "🧠", desc: "识别自动思维，检验它是不是真的，用更灵活的想法替代它", color: "#5A9E6F", bg: "#edf6f0", tag: "思维重塑" },
    { id: "dbt", name: "DBT 辩证行为", icon: "⚖️", desc: "在接纳与改变之间找到平衡，练习痛苦耐受和情绪调节技能", color: "#6B8E9B", bg: "#edf2f5", tag: "辩证平衡" },
  ];
  const getModalityStatus = (id: GrowthModality): { label: string; active: boolean } => {
    if (id === "act") {
      if (pendingAction) return { label: "行动卡待尝试", active: true };
      if (activeSessionId) return { label: "进行中", active: true };
      const inProgress = sortedSessions.find(s => s.status !== "completed");
      if (inProgress) return { label: `进行中 ${ACT_STEPS.filter(st => inProgress.steps[st.key].completedAt).length}/${inProgress.mode === "quick" ? 3 : ACT_STEPS.length}`, active: true };
      if (sortedSessions.filter(s => s.status === "completed").length > 0) return { label: `已完成 ${sortedSessions.filter(s => s.status === "completed").length} 次`, active: false };
      return { label: "未开始", active: false };
    }
    if (id === "oskar") {
      if (pendingOskarAction) return { label: "行动卡待尝试", active: true };
      if (activeOskarId) return { label: "进行中", active: true };
      const inProgress = sortedOskarSessions.find(s => s.status === "in_progress");
      if (inProgress) return { label: `进行中 ${OSKAR_STEPS.filter(st => inProgress.steps[st.key].completedAt).length}/${OSKAR_STEPS.length}`, active: true };
      if (sortedOskarSessions.filter(s => s.status === "completed").length > 0) return { label: `已完成 ${sortedOskarSessions.filter(s => s.status === "completed").length} 次`, active: false };
      return { label: "未开始", active: false };
    }
    return { label: "即将上线", active: false };
  };
  // 知识库：视图模式（"tree"=分类树首屏 / "list"=文章列表）、搜索、选中的分类/子分类
  const [activeCategory, setActiveCategory] = useState<string>("全部");
  const [activeSubcategory, setActiveSubcategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  // 周报：选中的周（0=本周，-1=上周）
  const [weekOffset, setWeekOffset] = useState(0);
  const { data: coachOverview } = useQuery({ queryKey: ["coach-overview"], queryFn: api.coachOverview });
  const { data: coachHistory = [] } = useQuery({ queryKey: ["chat", "coach"], queryFn: () => api.chatMessages("coach") });
  const { data: savedMoods = [] } = useQuery({ queryKey: ["coach-moods"], queryFn: api.moods });
  const { data: savedJournals = [] } = useQuery({ queryKey: ["coach-journals"], queryFn: api.journals });
  const { data: articleCatalog } = useQuery({ queryKey: ["coach-articles"], queryFn: () => api.coachArticles(searchQuery || undefined), placeholderData: prev => prev });
  const { data: categoryTree } = useQuery({ queryKey: ["coach-categories"], queryFn: api.coachCategories });
  const { data: selectedArticle } = useQuery({ queryKey: ["coach-article", articleId], queryFn: () => api.coachArticle(articleId!), enabled: Boolean(articleId) });
  const coachChatMutation = useMutation({
    mutationFn: (text: string) => api.coachChat(text),
    onMutate: (text) => {
      setPendingCoachMessage(text);
      setCoachSendError("");
      setMessage("");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["chat", "coach"] });
      setPendingCoachMessage("");
    },
    onError: (_error, text) => {
      setMessage(text);
      setCoachSendError("没有发送成功，输入框已保留，可重新发送。");
    },
  });
  useEffect(() => {
    const thread = coachThreadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [coachHistory.length, pendingCoachMessage, coachChatMutation.isPending]);
  const moodMutation = useMutation({
    mutationFn: () => {
      const primaryLabel = moodDetail.emotions[0] ? moodLabel(moodDetail.emotions[0]) : "未命名情绪";
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
  const weeklyMutation = useMutation({
    mutationFn: (offset: number) => api.coachWeeklyReport(offset),
  });
  const weeklyExportMutation = useMutation({
    mutationFn: api.exportCoachWeeklyReportPdf,
  });
  const send = () => {
    const text = message.trim();
    if (!text || coachChatMutation.isPending) return;
    coachChatMutation.mutate(text);
  };
  const clearCoachChat = useMutation({
    mutationFn: () => api.clearChatMessages("coach"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat", "coach"] });
    }
  });
  const exportCoachJournals = () => {
    if (!savedJournals.length) return;
    api.exportJournalsHtml();
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
    growth: ["成长练习", "把反复卡住你的事，慢慢变成下一小步"],
    record: ["记录", "写下当下，回看整周"],
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
  const pendingAction = useMemo(
    () => sortedSessions.find(session => session.actionPlan && !session.resolution.updatedAt) || null,
    [sortedSessions]
  );

  const updateSession = (id: string, updater: (s: ActSession) => ActSession) => {
    setActSessions(prev => prev.map(s => (s.id === id ? { ...updater(s), updatedAt: new Date().toISOString() } : s)));
  };

  const startNewSession = () => {
    const problem = newProblem.trim();
    if (!problem) return;
    const session = newActSession(problem, actMode);
    setActSessions(prev => [session, ...prev]);
    setActiveSessionId(session.id);
    setNewProblem("");
  };

  const restartSession = (id: string) => {
    setActSessions(prev => prev.map(s => (s.id === id ? newActSession(s.problem, s.mode) : s)));
    setActiveSessionId(id);
  };
  const deleteSession = (id: string) => {
    setActSessions(prev => prev.filter(session => session.id !== id));
    if (activeSessionId === id) setActiveSessionId(null);
  };

  const goToJournalFromAct = () => {
    setActiveSessionId(null);
    setRecordSub("journal");
    setTab("record");
  };

  // ─── OSKAR session helpers ───
  const sortedOskarSessions = useMemo(
    () => [...oskarSessions].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [oskarSessions]
  );
  const activeOskarSession = useMemo(
    () => oskarSessions.find(s => s.id === activeOskarId) || null,
    [oskarSessions, activeOskarId]
  );
  const pendingOskarAction = useMemo(
    () => sortedOskarSessions.find(s => s.smallAction && s.smallAction.status === "planned") || null,
    [sortedOskarSessions]
  );
  const updateOskarSession = (id: string, updater: (s: OskarSession) => OskarSession) => {
    setOskarSessions(prev => prev.map(s => (s.id === id ? { ...updater(s), updatedAt: new Date().toISOString() } : s)));
  };
  const startNewOskarSession = () => {
    const topic = oskarTopic.trim();
    if (!topic) return;
    const session = newOskarSession(topic);
    setOskarSessions(prev => [session, ...prev]);
    setActiveOskarId(session.id);
    setOskarTopic("");
  };
  const restartOskarSession = (id: string) => {
    setOskarSessions(prev => prev.map(s => (s.id === id ? newOskarSession(s.topic) : s)));
    setActiveOskarId(id);
  };
  const goToJournalFromOskar = () => {
    setActiveOskarId(null);
    setRecordSub("journal");
    setTab("record");
  };
  const linkActToOskar = (problem: string) => {
    const session = newOskarSession(problem);
    setOskarSessions(prev => [session, ...prev]);
    setActiveOskarId(session.id);
    setActiveSessionId(null);
  };
  const linkOskarToAct = (topic: string) => {
    setActiveOskarId(null);
    setNewProblem(topic);
  };
  const renderOskarSessionDetail = (session: OskarSession) => {
    const completedCount = OSKAR_STEPS.filter(step => session.steps[step.key].completedAt).length;
    const currentIndex = OSKAR_STEPS.findIndex(step => !session.steps[step.key].completedAt);
    const allDone = currentIndex === -1;
    const currentStep = allDone ? null : OSKAR_STEPS[currentIndex];
    return <>
      <button className="back-link" onClick={() => setActiveOskarId(null)}><ChevronLeft/> 返回</button>
      <div className="act-progress">
        <p className="eyebrow">OSKAR · 解决方案聚焦 · {session.smallAction ? "已形成行动" : `进行中 ${completedCount}/${OSKAR_STEPS.length}`}</p>
        <div className="act-progress-bar"><span style={{ width: `${session.smallAction ? 100 : (completedCount / OSKAR_STEPS.length) * 85}%` }} /></div>
        <h2 className="act-problem">{session.topic}</h2>
        <div className="act-completion-hints"><span className={completedCount === OSKAR_STEPS.length ? "done" : ""}>过程 {completedCount}/{OSKAR_STEPS.length}</span><span className={session.smallAction ? "done" : ""}>行动 {session.smallAction ? "已形成" : "待形成"}</span><span className={session.smallAction?.status === "done" ? "done" : ""}>实践 {session.smallAction ? ({ planned: "待尝试", tried: "已尝试", done: "已完成" } as const)[session.smallAction.status] : "未开始"}</span></div>
      </div>
      {!allDone && currentStep && <OskarStepForm
        key={currentStep.key}
        step={currentStep}
        session={session}
        index={currentIndex}
        total={OSKAR_STEPS.length}
        onSave={(reflection) => updateOskarSession(session.id, s => ({
          ...s,
          steps: { ...s.steps, [currentStep.key]: { reflection, completedAt: new Date().toISOString() } }
        }))}
        onToJournal={goToJournalFromOskar}
      />}
      {allDone && !session.smallAction && <OskarSmallActionForm
        session={session}
        onSave={(action) => updateOskarSession(session.id, s => ({
          ...s, smallAction: action,
        }))}
      />}
      {session.smallAction && <OskarActionCard
        session={session}
        onStatus={(status, note = "") => updateOskarSession(session.id, s => ({
          ...s,
          smallAction: s.smallAction ? { ...s.smallAction, status, note, updatedAt: new Date().toISOString() } : null,
          status: status === "done" ? "completed" : s.status,
        }))}
        onRestart={() => restartOskarSession(session.id)}
      />}
      <details className="act-step-list">
        <summary>查看本次 OSKAR 过程记录</summary>
        <ol>{OSKAR_STEPS.map(step => (
          <li key={step.key}>
            <strong>{step.name}</strong>
            {session.steps[step.key].completedAt
              ? <p>{session.steps[step.key].reflection || "（未填写）"}</p>
              : <p className="muted small">未完成</p>}
          </li>
        ))}</ol>
      </details>
      <div className="growth-detail-actions" style={{ marginTop: 14 }}>
        <button className="secondary" onClick={() => linkOskarToAct(session.topic)}>🧠 先处理情绪（ACT）</button>
      </div>
    </>;
  };

  const renderActSessionDetail = (session: ActSession) => {
    const activeSteps = session.mode === "quick"
      ? ACT_STEPS.filter(step => ["awareness", "defusion", "action"].includes(step.key))
      : ACT_STEPS;
    const completedCount = activeSteps.filter(step => session.steps[step.key].completedAt).length;
    const currentIndex = activeSteps.findIndex(step => !session.steps[step.key].completedAt);
    const allDone = currentIndex === -1;
    const currentStep = allDone ? null : activeSteps[currentIndex];
    return <>
      <button className="back-link" onClick={() => setActiveSessionId(null)}><ChevronLeft/> 返回</button>
      <div className="act-progress">
        <p className="eyebrow">{session.mode === "quick" ? "2分钟快速模式" : "完整模式"} · {session.actionPlan ? "已形成行动" : `进行中 ${completedCount}/${activeSteps.length}`}</p>
        <div className="act-progress-bar"><span style={{ width: `${session.actionPlan ? 100 : (completedCount / activeSteps.length) * 85}%` }} /></div>
        <h2 className="act-problem">{session.problem}</h2>
        <div className="act-completion-hints"><span className={completedCount === activeSteps.length ? "done" : ""}>过程 {completedCount}/{activeSteps.length}</span><span className={session.actionPlan ? "done" : ""}>行动 {session.actionPlan ? "已形成" : "待形成"}</span><span className={session.actionPlan?.status === "completed" ? "done" : ""}>实践 {session.actionPlan ? ({ planned: "待尝试", tried: "已尝试", completed: "已完成", blocked: "需调整" } as const)[session.actionPlan.status] : "未开始"}</span></div>
      </div>
      {!allDone && currentStep && <ActStepForm
        key={currentStep.key}
        step={currentStep}
        session={session}
        index={currentIndex}
        total={activeSteps.length}
        onSave={(reflection) => updateSession(session.id, s => ({
          ...s,
          steps: { ...s.steps, [currentStep.key]: { reflection, completedAt: new Date().toISOString() } }
        }))}
        onBlocked={(reason, fallback) => updateSession(session.id, s => ({
          ...s,
          steps: { ...s.steps, [currentStep.key]: { reflection: `暂时跳过：${reason}。替代方式：${fallback}`, completedAt: new Date().toISOString() } }
        }))}
        onToJournal={goToJournalFromAct}
      />}
      {allDone && !session.actionPlan && <ActActionPlanForm
        session={session}
        onSave={(actionPlan) => updateSession(session.id, s => ({
          ...s, actionPlan,
          status: "in_progress"
        }))}
      />}
      {session.actionPlan && <ActActionCard
        session={session}
        onStatus={(status, obstacle = "") => updateSession(session.id, s => ({
          ...s,
          actionPlan: s.actionPlan ? { ...s.actionPlan, status, obstacle, updatedAt: new Date().toISOString() } : null,
        }))}
        onRestart={() => restartSession(session.id)}
      />}
      {session.actionPlan && session.actionPlan.status !== "planned" && !session.resolution.updatedAt && <ActResultForm
        session={session}
        onSave={(solved, note) => {
          updateSession(session.id, s => ({
            ...s,
            resolution: { solved, note, updatedAt: new Date().toISOString() },
            status: "completed"
          }));
          setActiveSessionId(null);
        }}
      />}
      {session.resolution.updatedAt && <div className={`act-result-summary ${session.resolution.solved ? "helped" : "not-helped"}`}>
        <strong>{session.resolution.solved ? "这次行动有一点帮助" : "这次行动没有达到预期"}</strong>
        {session.resolution.note && <p>{session.resolution.note}</p>}
      </div>}
      {(session.actionPlan || allDone) && <div className="growth-detail-actions" style={{ marginTop: 14 }}>
        <button className="secondary" onClick={() => linkActToOskar(session.problem)}>🎯 用 OSKAR 找解决方案</button>
      </div>}
      <details className="act-step-list">
        <summary>查看本次过程记录</summary>
        <ol>{activeSteps.map(step => (
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
      <section className="card coach-chat">
        <div className="section-title"><span><MessageCircleHeart size={19}/> 陪伴对话</span>{coachHistory.length > 0 && <div style={{display:"flex",gap:10,alignItems:"center"}}><small style={{display:"flex",gap:10,alignItems:"center"}}><button className="text-button" onClick={() => api.exportChat("coach")}><Download size={14}/> 导出</button><button className="text-button clear-chat-btn" onClick={() => { if (confirm("确定清空全部陪伴对话吗？此操作不可恢复")) clearCoachChat.mutate(); }} disabled={clearCoachChat.isPending}>清空</button></small></div>}</div>
        <div className="coach-thread" ref={coachThreadRef}>
          {coachHistory.length === 0 && !pendingCoachMessage && <div className="editorial-empty coach-empty">
            <img src="/brand/coach-reflection.webp" alt="" width="960" height="640" loading="lazy"/>
            <div><strong>不需要先整理好</strong><p>想到哪里就说到哪里。这里先陪你把压在心里的事慢慢说清楚。</p></div>
          </div>}
          {coachHistory.map(item => <div className={item.role === "user" ? "coach-bubble user-message" : "coach-bubble"} key={item.id}><span>{item.content}</span><time className="chat-message-time">{formatChatTimestamp(item.created_at)}</time></div>)}
          {pendingCoachMessage && <div className="coach-bubble user-message pending-message"><span>{pendingCoachMessage}</span>{coachSendError && <small className="chat-send-error">{coachSendError}</small>}<time className="chat-message-time">刚刚</time></div>}
          {coachChatMutation.isPending && <div className="coach-bubble pending-reply"><span className="typing-dots" aria-label="正在回复"><i/><i/><i/></span></div>}
        </div>
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="现在最想说的一句话…" onKeyDown={e => { if (e.key === "Enter" && message.trim() && !coachChatMutation.isPending) send(); }} /><button onClick={send} disabled={!message.trim() || coachChatMutation.isPending}>发送</button></div>
      </section>
    </>,
    emotion: (() => {
      const burdenEmotions = new Set(["anxious", "tense", "restless", "overwhelmed", "sad", "exhausted", "empty", "lonely", "angry", "frustrated", "ashamed", "guilty", "confused", "doubtful", "numb", "helpless"]);
      const records = savedMoods.map(item => {
        const detail = parseMoodDetail(item.note);
        return {
          ...item,
          detail,
          date: new Date(`${item.entry_date}T12:00:00`),
          burden: Boolean(detail?.emotions.some(key => burdenEmotions.has(key))),
        };
      });
      const recentRecords = records.slice(0, 3);
      const previousRecords = records.slice(3, 6);
      const highBurdenDays = (rows: typeof records) => rows.filter(item => item.burden && item.intensity >= 4).length;
      const burdenAverage = (rows: typeof records) => rows.length
        ? rows.reduce((sum, item) => sum + (item.burden ? item.intensity : 0), 0) / rows.length
        : 0;
      let coachTrend = { status: "insufficient", title: "继续记录，历史会逐渐清楚", message: `目前有 ${records.length} 条情绪记录；累计6条后，比较最近3条与此前3条，不要求连续打卡。` };
      if (recentRecords.length >= 3 && previousRecords.length >= 3) {
        const recentHigh = highBurdenDays(recentRecords);
        const previousHigh = highBurdenDays(previousRecords);
        const loadDelta = burdenAverage(recentRecords) - burdenAverage(previousRecords);
        if (recentHigh < previousHigh || loadDelta <= -0.5) {
          coachTrend = { status: "progress", title: "最近记录中的情绪负荷有所下降", message: `较强负面情绪由此前3条中的 ${previousHigh} 条，降至最近3条中的 ${recentHigh} 条。` };
        } else if (recentHigh > previousHigh || loadDelta >= 0.5) {
          coachTrend = { status: "regression", title: "最近记录中的情绪负荷需要关注", message: `较强负面情绪由此前3条中的 ${previousHigh} 条，增至最近3条中的 ${recentHigh} 条。` };
        } else {
          coachTrend = { status: "stable", title: "最近记录中的情绪负荷基本稳定", message: `前后两组记录中的较强负面情绪均为 ${recentHigh} 条，没有观察到明确变化。` };
        }
      }
      const history30 = records.slice(0, 30).reverse();
      const weekGroups = new Map<string, typeof records>();
      records.forEach(item => {
        const monday = new Date(item.date);
        monday.setDate(item.date.getDate() - ((item.date.getDay() + 6) % 7));
        const key = monday.toISOString().slice(0, 10);
        if (!weekGroups.has(key)) weekGroups.set(key, []);
        weekGroups.get(key)!.push(item);
      });
      const moodWeeks = Array.from(weekGroups.entries()).sort(([a], [b]) => a.localeCompare(b)).slice(-4).map(([key, rows]) => {
        const start = new Date(`${key}T12:00:00`);
        return {
          key,
          label: `${start.getMonth() + 1}/${start.getDate()}`,
          count: rows.length,
          average: rows.reduce((sum, item) => sum + item.intensity, 0) / rows.length,
        };
      });
      const recentDetails = records.map(item => item.detail).filter(Boolean) as MoodDetail[];
      const last7 = recentDetails.slice(0, 7);
      const emotionCounts: Record<string, number> = {};
      last7.forEach(d => d.emotions.forEach(k => { emotionCounts[k] = (emotionCounts[k] || 0) + 1; }));
      const topEmotions = Object.entries(emotionCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);
      const triggerCounts: Record<string, number> = {};
      records.slice(0, 30).forEach(item => item.detail?.triggers.forEach(trigger => { triggerCounts[trigger] = (triggerCounts[trigger] || 0) + 1; }));
      const topTriggers = Object.entries(triggerCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);

      const toggleIn = <T,>(arr: T[], v: T) => arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v];
      const toggleEmotion = (key: string) => {
        setMoodDetail(prev => {
          const next = toggleIn(prev.emotions, key);
          return { ...prev, emotions: next.length ? next : ["calm"] };
        });
      };
      const toggleTrigger = (label: string) => setMoodDetail(prev => ({ ...prev, triggers: toggleIn(prev.triggers, label) }));
      const toggleBody = (label: string) => setMoodDetail(prev => ({ ...prev, body: toggleIn(prev.body, label) }));
      const addCustomEmotion = () => {
        const label = customEmotion.trim().slice(0, 20);
        if (!label) return;
        const builtIn = Object.entries(MOOD_LABEL_MAP).find(([, value]) => value === label)?.[0];
        const key = builtIn || `custom:${label}`;
        setMoodDetail(prev => ({ ...prev, emotions: prev.emotions.includes(key) ? prev.emotions : [...prev.emotions, key] }));
        setCustomEmotion("");
      };

      const canSave = moodDetail.emotions.length > 0;
      const primaryLabel = moodDetail.emotions.map(moodLabel).join(" · ");

      return <>
        <section className="card emotion-form">
          <h3 className="coach-section-head">今天的情绪</h3>

          <div className="form-row">
            <div className="emotion-step-head"><span>1</span><div><label className="form-label">先选择最接近的情绪</label><small>可以多选，先选最明显的 1–3 个就够了。</small></div></div>
            <div className="emotion-current-selection"><span>已选择</span><strong>{primaryLabel}</strong></div>
            <div className="mood-families">
              {MOOD_FAMILIES.slice(0, showAllMoods ? MOOD_FAMILIES.length : 3).map(family => (
                <div className="mood-family" key={family.group}>
                  <span className="mood-family-title">{family.group}</span>
                  <div className="mood-chips">
                    {family.items.map(item => <button key={item.key} className={moodDetail.emotions.includes(item.key) ? "selected" : ""} onClick={() => toggleEmotion(item.key)}>{item.label}</button>)}
                  </div>
                </div>
              ))}
              <button className="more-moods-button" onClick={() => setShowAllMoods(!showAllMoods)}>
                {showAllMoods ? "收起更多情绪" : "查看更多情绪（低落、压力、迷茫）"}
              </button>
              <div className="mood-family custom-mood-family">
                <span className="mood-family-title">没有合适的词？写下自己的感受</span>
                <div className="custom-emotion-input">
                  <input
                    value={customEmotion}
                    maxLength={20}
                    onChange={e => setCustomEmotion(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addCustomEmotion(); } }}
                    placeholder="例如：悬着、憋闷、被理解"
                  />
                  <button onClick={addCustomEmotion} disabled={!customEmotion.trim()}>添加</button>
                </div>
                {moodDetail.emotions.some(key => key.startsWith("custom:")) && <div className="mood-chips custom-emotion-selected">
                  {moodDetail.emotions.filter(key => key.startsWith("custom:")).map(key =>
                    <button className="selected" key={key} onClick={() => toggleEmotion(key)}>{moodLabel(key)} ×</button>)}
                </div>}
              </div>
            </div>
          </div>

          <div className="form-row">
            <div className="emotion-step-head"><span>2</span><div><label className="form-label">再选择此刻的强度</label><small>以情绪最明显的那一刻为准，看它对说话、做事或休息的影响。</small></div></div>
            <div className="intensity-selection"><strong>{moodDetail.intensity} / 5</strong><span>{INTENSITY_LABELS[moodDetail.intensity - 1]}</span></div>
            <div className="intensity-bar">
              {[1, 2, 3, 4, 5].map(n => <button key={n} className={moodDetail.intensity === n ? "selected" : ""} aria-label={`${n}级，${INTENSITY_LABELS[n - 1]}`} onClick={() => setMoodDetail(prev => ({ ...prev, intensity: n }))}><strong>{n}</strong><small>{["很轻", "轻微", "明显", "较强", "难应对"][n - 1]}</small></button>)}
            </div>
            <div className="intensity-guide"><span><b>1</b>注意到了，但基本不影响日常</span><span><b>3</b>明显影响当下，需要调整一下</span><span><b>5</b>很难继续当前事情，需要先照顾自己</span></div>
          </div>

          <div className="form-row">
            <div className="emotion-step-head optional"><span>3</span><div><label className="form-label">需要时再补充</label><small>场景、身体感受和应对方式都可以跳过。</small></div></div>
            <label className="form-label secondary-label">触发场景（可多选）</label>
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

        <h3 className="coach-section-head emotion-review-heading">最近变化</h3>
        <section className={`coach-trend-conclusion ${coachTrend.status}`}>
          <div><span>{coachTrend.status === "progress" ? "改善" : coachTrend.status === "regression" ? "需关注" : coachTrend.status === "stable" ? "稳定" : "数据不足"}</span><h2>{coachTrend.title}</h2></div>
          <p>{coachTrend.message}</p>
        </section>
        <section className="card coach-trend-card">
          <div className="section-title"><span>最近30条情绪强度</span><small>{records[0] ? `上次 ${records[0].date.getMonth() + 1}/${records[0].date.getDate()}` : "尚无记录"}</small></div>
          <div className="coach-month-chart" aria-label="最近30条情绪强度趋势">
            {history30.map(item => <i className={`recorded level-${item.intensity}`} title={`${item.date.getMonth() + 1}/${item.date.getDate()} 强度${item.intensity}/5`} key={item.id}>
              <span style={{ height: `${item.intensity * 20}%` }}/>
            </i>)}
            {!history30.length && <em>保存第一条记录后，这里会保留历史趋势。</em>}
          </div>
          <div className="coach-week-list">{moodWeeks.map(week => <div key={week.key}>
            <span>{week.label}</span><div><i style={{ width: `${week.average ? week.average / 5 * 100 : 0}%` }}/></div>
            <strong>{week.average === null ? "—" : week.average.toFixed(1)}</strong><small>{week.count}天</small>
          </div>)}</div>
          <div className="coach-patterns">
            <div><span>常见情绪</span><strong>{topEmotions.map(([key]) => moodLabel(key)).join(" · ") || "尚无记录"}</strong></div>
            <div><span>明确触发因素</span><strong>{topTriggers.length ? topTriggers.map(([trigger, count]) => `${trigger} ${count}次`).join(" · ") : "尚未记录触发因素"}</strong></div>
          </div>
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
                  <strong>{detail ? detail.emotions.map(moodLabel).join(" · ") : item.mood}</strong>
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
    growth: (() => {
      if (activeSession) return <section className="card act-session">{renderActSessionDetail(activeSession)}</section>;
      if (activeOskarSession) return <section className="card act-session">{renderOskarSessionDetail(activeOskarSession)}</section>;
      if (growthModality === "act") return <>
        <div className="modality-back" onClick={() => { setGrowthModality(null); setActiveSessionId(null); }}>← 返回方法列表</div>
        {pendingAction && pendingAction.actionPlan && <section className="pending-action-section">
          <div className="pending-action-heading"><div><p className="eyebrow">正在进行的行动</p><h2>{pendingAction.problem}</h2></div><button className="text-button" onClick={() => setActiveSessionId(pendingAction.id)}>查看过程</button></div>
          <ActActionCard
            session={pendingAction}
            onStatus={(status, obstacle = "") => updateSession(pendingAction.id, s => ({
              ...s,
              actionPlan: s.actionPlan ? { ...s.actionPlan, status, obstacle, updatedAt: new Date().toISOString() } : null,
            }))}
            onRestart={() => restartSession(pendingAction.id)}
          />
          {pendingAction.actionPlan.status !== "planned" && <ActResultForm
            session={pendingAction}
            onSave={(solved, note) => updateSession(pendingAction.id, s => ({
              ...s,
              resolution: { solved, note, updatedAt: new Date().toISOString() },
              status: "completed"
            }))}
          />}
        </section>}
        <section className="growth-explainer">
          <div>
            <span>这里能帮你做什么？</span>
            <h2>不是逼自己想开，而是从"被问题困住"回到"我可以选择"</h2>
            <p>适合脑子反复想、情绪放不下，或知道该做什么却迟迟动不了的时候。</p>
          </div>
          <details>
            <summary>了解练习如何进行</summary>
            <ol>
              <li><b>1</b><span><strong>说清卡点</strong><small>先把最困扰你的那件事放下来</small></span></li>
              <li><b>2</b><span><strong>拉开距离</strong><small>看见念头和感受，不急着被它推着走</small></span></li>
              <li><b>3</b><span><strong>带走一步</strong><small>最后得到一个现实可做的小行动</small></span></li>
            </ol>
          </details>
        </section>
        <section className="card act-intake">
          <h3 className="coach-section-head">选一件此刻最卡住你的事</h3>
          <div className="act-intake-section">
            <div className="act-intake-label"><b>1</b><span><strong>写下这件事</strong><small>一句话就够，不用先分析原因</small></span></div>
            <textarea value={newProblem} onChange={e => setNewProblem(e.target.value)} placeholder="例如：和家人有分歧，我不知道该怎么开口。" rows={3}/>
            <details className="growth-example-details">
              <summary>不知道怎么写？查看 4 个参考例子</summary>
              <div className="growth-examples">
                {[
                  "一想到明天要处理的事，我就开始紧张",
                  "我总觉得自己做得不够好",
                  "和家人有分歧，我不知道该怎么开口",
                  "我想休息一下，却一直有负罪感",
                ].map(example => <button className={newProblem === example ? "selected" : ""} onClick={() => setNewProblem(example)} key={example}>{example}</button>)}
              </div>
            </details>
          </div>
          <div className="act-intake-section">
            <div className="act-intake-label"><b>2</b><span><strong>选择练习方式</strong><small>这是流程选择，不是问题示例</small></span></div>
            <div className="act-mode-picker">
              <button className={actMode === "quick" ? "selected" : ""} onClick={() => setActMode("quick")}><strong>先做 2 分钟</strong><small>走 3 个关键步骤，快速理出下一步</small></button>
              <button className={actMode === "full" ? "selected" : ""} onClick={() => setActMode("full")}><strong>慢慢梳理一次</strong><small>完整走过 6 步，适合反复卡住的事</small></button>
            </div>
          </div>
          <button className="primary" disabled={!newProblem.trim()} onClick={startNewSession}>开始{actMode === "quick" ? "快速练习" : "完整练习"}</button>
        </section>
        <h3 className="coach-section-head">过往问题（{sortedSessions.length}）</h3>
        {sortedSessions.length === 0 ? <p className="muted small">发起第一个问题后，会按时间倒序保存在这里。</p> :
          <div className="act-history">{sortedSessions.slice(0, showAllActHistory ? sortedSessions.length : 3).map(session => {
            const completedCount = ACT_STEPS.filter(step => session.steps[step.key].completedAt).length;
            return <article key={session.id} className={`act-history-item ${session.status}`}>
              <button className="act-history-open" onClick={() => setActiveSessionId(session.id)}>
                <div className="act-history-head">
                  <strong>{session.problem}</strong>
                  <small>{new Date(session.updatedAt).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</small>
                </div>
                <p className="muted small">
                  {session.actionPlan
                    ? session.resolution.updatedAt
                      ? `行动卡 · 已结束 · ${session.resolution.solved ? "有帮助" : "未达到预期"}`
                      : `行动卡 · ${{ planned: "待尝试", tried: "待提交结果", completed: "待提交结果", blocked: "待调整或提交结果" }[session.actionPlan.status]}`
                    : session.status === "completed" ? "已完成旧版练习" : `进行中 ${completedCount}/${session.mode === "quick" ? 3 : ACT_STEPS.length}`}
                </p>
              </button>
              <button className="act-history-delete" aria-label={`删除问题：${session.problem}`} onClick={() => {
                if (confirm(`确定删除"${session.problem}"吗？删除后无法恢复。`)) deleteSession(session.id);
              }}>删除</button>
            </article>;
          })}
          {sortedSessions.length > 3 && <button className="act-history-more" onClick={() => setShowAllActHistory(!showAllActHistory)}>
            {showAllActHistory ? "收起较早问题" : `展开其余 ${sortedSessions.length - 3} 个问题`}
          </button>}
          </div>}
      </>;
      if (growthModality === "oskar") return <>
        <div className="modality-back" onClick={() => { setGrowthModality(null); setActiveOskarId(null); }}>← 返回方法列表</div>
        {pendingOskarAction && pendingOskarAction.smallAction && <section className="pending-action-section">
          <div className="pending-action-heading"><div><p className="eyebrow">待尝试的一小步（OSKAR）</p><h2>{pendingOskarAction.topic}</h2></div><button className="text-button" onClick={() => setActiveOskarId(pendingOskarAction.id)}>查看过程</button></div>
          <OskarActionCard
            session={pendingOskarAction}
            onStatus={(status, note = "") => updateOskarSession(pendingOskarAction.id, s => ({
              ...s,
              smallAction: s.smallAction ? { ...s.smallAction, status, note, updatedAt: new Date().toISOString() } : null,
              status: status === "done" ? "completed" : s.status,
            }))}
            onRestart={() => restartOskarSession(pendingOskarAction.id)}
          />
        </section>}
        <section className="card act-intake">
          <h3 className="coach-section-head">走出卡点 · OSKAR 自助引导</h3>
          <p className="muted small" style={{ marginBottom: 12 }}>ACT 帮你拉开距离。当你想往前走一步时，用 OSKAR 五步指引自己从"想要的"走到"一小步"。</p>
          <div className="act-intake-section">
            <div className="act-intake-label"><b>1</b><span><strong>你此刻想改变什么？</strong><small>一句话就够，聚焦你"想要的"而非"不想要的"</small></span></div>
            <textarea value={oskarTopic} onChange={e => setOskarTopic(e.target.value)} placeholder="例如：我想早上出门更从容一点。" rows={3}/>
          </div>
          <button className="primary" disabled={!oskarTopic.trim()} onClick={startNewOskarSession}>开始 OSKAR 五步</button>
        </section>
        {sortedOskarSessions.length > 0 && <>
          <h3 className="coach-section-head">OSKAR 过往（{sortedOskarSessions.length}）</h3>
          <div className="act-history">{sortedOskarSessions.map(session => {
            const completedCount = OSKAR_STEPS.filter(step => session.steps[step.key].completedAt).length;
            return <article key={session.id} className="act-history-item">
              <button className="act-history-open" onClick={() => setActiveOskarId(session.id)}>
                <div className="act-history-head">
                  <strong>{session.topic}</strong>
                  <small>{new Date(session.updatedAt).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</small>
                </div>
                <p className="muted small">
                  {session.smallAction
                    ? `行动卡 · ${session.smallAction.status === "done" ? "已做到" : session.smallAction.status === "tried" ? "已尝试" : "待尝试"} · ${completedCount}/${OSKAR_STEPS.length} 步`
                    : session.status === "completed" ? "已完成" : `进行中 ${completedCount}/${OSKAR_STEPS.length}`}
                </p>
              </button>
            </article>;
          })}</div>
        </>}
      </>;
      if (growthModality) return <>
        <div className="modality-back" onClick={() => setGrowthModality(null)}>← 返回方法列表</div>
        <section className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>{MODALITY_CARDS.find(m => m.id === growthModality)?.icon}</div>
          <h3 style={{ color: MODALITY_CARDS.find(m => m.id === growthModality)?.color }}>{MODALITY_CARDS.find(m => m.id === growthModality)?.name}</h3>
          <p className="muted" style={{ marginTop: 8 }}>该练习正在开发中，敬请期待。</p>
        </section>
      </>;
      const activeMod = ["act", "oskar"].find(id => getModalityStatus(id as GrowthModality).active);
      return <>
        {activeMod && (() => {
          const mod = MODALITY_CARDS.find(m => m.id === activeMod)!;
          const st = getModalityStatus(activeMod as GrowthModality);
          return <div className="growth-recommend" style={{ borderColor: mod.color, background: mod.bg }} onClick={() => setGrowthModality(activeMod as GrowthModality)}>
            <span className="growth-recommend-badge" style={{ background: mod.color }}>继续练习</span>
            <span className="growth-recommend-icon">{mod.icon}</span>
            <div>
              <strong>{mod.name}</strong>
              <small>{st.label} — 点击继续</small>
            </div>
          </div>;
        })()}
        <section className="growth-explainer">
          <div>
            <span>成长工具箱</span>
            <h2>选一个适合你此刻状态的方法</h2>
            <p>每一种方法都是不同的钥匙。有时候你需要先被理解，有时候你需要一条路。</p>
          </div>
        </section>
        <div className="modality-gallery">
          {MODALITY_CARDS.map(mod => {
            const st = getModalityStatus(mod.id);
            return (
              <button key={mod.id} className={`modality-card ${st.active ? "active" : ""}`} style={{ "--mod-color": mod.color, "--mod-bg": mod.bg } as React.CSSProperties} onClick={() => setGrowthModality(mod.id)}>
                <div className="modality-card-icon" style={{ background: mod.bg }}>{mod.icon}</div>
                <div className="modality-card-body">
                  <div className="modality-card-head">
                    <span className="modality-card-name" style={{ color: mod.color }}>{mod.name}</span>
                    <span className={`modality-card-tag ${st.active ? "pulse" : ""}`} style={{ background: st.active ? mod.color : "#e8e2d8", color: st.active ? "white" : "#8b7e6e" }}>{st.label}</span>
                  </div>
                  <p>{mod.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
        {(pendingAction || pendingOskarAction) && <section className="pending-action-section" style={{ marginTop: 16 }}>
          <div className="pending-action-heading"><div><p className="eyebrow">待处理的行动</p></div></div>
          {pendingAction && pendingAction.actionPlan && <div style={{ marginTop: 8 }}>
            <button className="text-button" style={{ color: "#C4884D", fontWeight: 700 }} onClick={() => { setGrowthModality("act"); setActiveSessionId(pendingAction.id); }}>🧘 ACT: {pendingAction.problem.slice(0, 20)}…</button>
          </div>}
          {pendingOskarAction && pendingOskarAction.smallAction && <div style={{ marginTop: 4 }}>
            <button className="text-button" style={{ color: "#5B9BD5", fontWeight: 700 }} onClick={() => { setGrowthModality("oskar"); setActiveOskarId(pendingOskarAction.id); }}>🎯 OSKAR: {pendingOskarAction.topic.slice(0, 20)}…</button>
          </div>}
        </section>}
      </>;
    })(),
    record: <>
      <div className="record-subtabs">
        <button className={recordSub === "journal" ? "selected" : ""} onClick={() => setRecordSub("journal")}><PenLine size={16}/> 日记</button>
        <button className={recordSub === "weekly" ? "selected" : ""} onClick={() => setRecordSub("weekly")}><BarChart3 size={16}/> 周报</button>
      </div>
      {recordSub === "journal" ? <>
        <section className="card journal-card">
          <div className="journal-heading"><p className="eyebrow">今天的记录</p><h3>留下一件你想记住的事</h3><span>不需要同时回答多个问题，写几句话也可以。</span></div>
          <details className="journal-prompts">
            <summary>不知道写什么？看两个开头</summary>
            <button onClick={() => setJournal("今天有一个瞬间让我注意到……")}>今天有一个瞬间让我注意到……</button>
            <button onClick={() => setJournal("如果朋友处在我今天的位置，我会对他说……")}>如果朋友处在我今天的位置，我会对他说……</button>
          </details>
          <label className="journal-answer-label">你的记录<textarea value={journal} onChange={e => setJournal(e.target.value)} placeholder="想到什么写什么，不必完整"/></label>
          <button className="coach-main-button" disabled={!journal.trim() || journalMutation.isPending} onClick={() => journalMutation.mutate()}>保存今日反思</button>
        </section>
        <div className="record-section-head">
          <h3 className="coach-section-head">过往记录（{savedJournals.length}）</h3>
          {savedJournals.length > 0 && <button className="text-button" onClick={exportCoachJournals}><Download size={14}/> 导出 HTML</button>}
        </div>
        <div className="journal-history">{savedJournals.length ? savedJournals.map(item => <article key={item.id}><time>{new Date(item.created_at).toLocaleDateString("zh-CN", {month: "short", day: "numeric"})}</time><div><strong>{item.content.slice(0, 18)}</strong><p>{item.content}</p></div></article>) : <p className="muted">保存第一篇反思后会显示在这里。</p>}</div>
      </> : <>
        <section className="card weekly-card">
          <div className="weekly-week-switch">
            <button className={weekOffset === 0 ? "selected" : ""} onClick={() => setWeekOffset(0)}>本周</button>
            <button className={weekOffset === -1 ? "selected" : ""} onClick={() => setWeekOffset(-1)}>上周</button>
          </div>
          <p className="muted small">周报会整理本周的情绪、日记和对话记录，帮助你看见反复出现的压力来源和已经做出的调整。</p>
          <button className="primary" disabled={weeklyMutation.isPending} onClick={() => weeklyMutation.mutate(weekOffset)}>
            {weeklyMutation.isPending ? "正在生成…" : weeklyMutation.data ? `重新生成${weekOffset === 0 ? "本周" : "上周"}周报` : `生成${weekOffset === 0 ? "本周" : "上周"}周报`}
          </button>
          {weeklyMutation.isError && <p className="muted small">生成失败，请稍后再试。</p>}
          {weeklyMutation.data && <>
            <div className="weekly-meta">
              <span>{weeklyMutation.data.week_start} ~ {weeklyMutation.data.week_end}</span>
              <span>情绪 {weeklyMutation.data.mood_count} · 日记 {weeklyMutation.data.journal_count} · 对话 {weeklyMutation.data.chat_count}</span>
              {weeklyMutation.data.fallback && <small>· 基础整理版</small>}
            </div>
            <div className="weekly-content">{weeklyMutation.data.content}</div>
            <button
              className="secondary"
              disabled={weeklyExportMutation.isPending}
              onClick={() => weeklyExportMutation.mutate(weeklyMutation.data)}
            >
              <Download size={15}/> {weeklyExportMutation.isPending ? "正在导出…" : "导出 PDF"}
            </button>
            {weeklyExportMutation.isError && <p className="muted small">导出失败，请稍后再试。</p>}
          </>}
        </section>
      </>}
    </>,
    knowledge: articleId ? <section className="article-detail"><button className="back-link" onClick={() => setArticleId(null)}><ChevronLeft/> 返回知识库</button>{selectedArticle ? <><p className="eyebrow">{CATEGORY_LABELS[selectedArticle.category] || selectedArticle.category}{selectedArticle.subcategory ? ` · ${selectedArticle.subcategory}` : ""} · {selectedArticle.read_time}</p><h2>{selectedArticle.title}</h2><p className="article-summary">{selectedArticle.summary}</p><div className="article-content">{selectedArticle.content}</div>{selectedArticle.related && selectedArticle.related.length > 0 && <><h3 className="related-articles-head">📚 相关文章</h3><div className="knowledge-list">{selectedArticle.related.map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{item.subcategory} · {item.read_time}</small><strong>{item.title}</strong><ChevronRight/></button>)}</div></>}</> : <p>正在加载文章…</p>}</section> : (() => {
      const items = articleCatalog?.items || [];
      const isSearching = searchQuery.trim().length > 0;
      // 搜索模式：直接显示搜索结果
      if (isSearching) {
        return <>
          <div className="knowledge-search">
            <input autoFocus value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="🔍 搜索文章标题、摘要、内容…"/>
            {searchQuery && <button className="clear-search" onClick={() => setSearchQuery("")}>清除</button>}
          </div>
          {items.length === 0 ? <p className="muted">未找到包含「{searchQuery}」的文章。</p> : <><p className="muted">找到 {items.length} 篇相关文章</p><div className="knowledge-list">{items.map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{CATEGORY_LABELS[item.category] || item.category}{item.subcategory ? ` · ${item.subcategory}` : ""} · {item.read_time}</small><strong>{item.title}</strong><p>{item.summary}</p><ChevronRight/></button>)}</div></>}
        </>;
      }
      // 选中了具体子分类：显示该子分类下的文章
      if (activeSubcategory) {
        const subItems = items.filter(item => item.category === activeCategory && item.subcategory === activeSubcategory);
        return <>
          <button className="back-link" onClick={() => setActiveSubcategory(null)}><ChevronLeft/> 返回分类</button>
          <h2 className="subcategory-head">{activeSubcategory}</h2>
          {subItems.length === 0 ? <p className="muted">该分类下还没有内容。</p> : <div className="knowledge-list">{subItems.map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{item.read_time} · {item.level}</small><strong>{item.title}</strong><p>{item.summary}</p><ChevronRight/></button>)}</div>}
        </>;
      }
      // 默认：分类树首屏 + 一级分类切换
      const tree = categoryTree?.items || [];
      const currentCat = tree.find(c => c.id === activeCategory);
      return <>
        <div className="knowledge-search">
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="🔍 搜索文章标题、摘要、内容…"/>
        </div>
        {activeCategory === "全部" ? (
          <div className="category-tree">{tree.map(cat => <button key={cat.id} className="category-card" onClick={() => setActiveCategory(cat.id)}>
            <span className="category-icon">{cat.icon}</span>
            <div className="category-body"><strong>{cat.name}</strong><small>{cat.desc}</small><span className="category-count">{cat.count} 篇 · {cat.children.length} 个子分类</span></div>
            <ChevronRight/>
          </button>)}</div>
        ) : (
          // 展开某个一级分类：显示其子分类
          currentCat ? <>
            <button className="back-link" onClick={() => setActiveCategory("全部")}><ChevronLeft/> 全部分类</button>
            <div className="category-tree">
              <div className="category-card current"><span className="category-icon">{currentCat.icon}</span><div className="category-body"><strong>{currentCat.name}</strong><small>{currentCat.desc}</small></div></div>
            </div>
            <div className="subcategory-grid">{currentCat.children.map(ch => <button key={ch.id} className="subcategory-card" onClick={() => setActiveSubcategory(ch.name)}>
              <span>{ch.icon}</span><div><strong>{ch.name}</strong><small>{ch.desc}</small></div><span className="subcategory-count">{ch.count}</span>
            </button>)}</div>
            <h3 className="related-articles-head">📂 {currentCat.name} 全部文章</h3>
            <div className="knowledge-list">{items.filter(it => it.category === currentCat.id).map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{item.subcategory} · {item.read_time}</small><strong>{item.title}</strong><p>{item.summary}</p><ChevronRight/></button>)}</div>
          </> : <p className="muted">分类加载中…</p>
        )}
      </>;
    })()
  }[tab];
  const navItems = [
    ["chat", "陪伴", MessageCircleHeart], ["emotion", "情绪", Smile], ["growth", "成长", Sprout],
    ["record", "记录", PenLine], ["knowledge", "知识库", BookOpen]
  ] as const;
  return <main className="coach-shell">
    <header className={`coach-hero compact ${tab === "chat" ? "coach-chat-hero" : ""}`}>
      <button onClick={switchToAba}><ChevronLeft /> 返回 ABA 家庭训练</button>
      <p className="eyebrow">家长陪伴 · {headers[tab][0]}</p>
      <h1>{headers[tab][1]}</h1>
      <p>一个安全、温和、不评判的空间</p>
    </header>
    <section className={`coach-content ${tab === "chat" ? "coach-chat-content" : ""}`}>{page}{tab === "knowledge" && <button className="coach-logout" onClick={logout}>退出登录</button>}</section>
    <nav className="coach-nav">{navItems.map(([id, label, Icon]) => <button className={tab === id ? "active" : ""} onClick={() => { setTab(id as CoachTab); if (id === "growth") { setGrowthModality(null); setActiveSessionId(null); setActiveOskarId(null); } }} key={id}><Icon/><span>{label}</span></button>)}</nav>
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
  const mode: ProductMode = "coach";
  const setMode = (_next: ProductMode) => {};
  const { data: bootstrap, isError } = useQuery({
    queryKey: ["bootstrap"],
    queryFn: api.bootstrap,
    enabled: authenticated,
    staleTime: 5 * 60_000,
  });
  const user = bootstrap?.user;
  const logout = () => {
    api.tokenStore.clear();
    queryClient.clear();
    setAuthenticated(false);
  };
  if (!authenticated || isError) return <Auth mode={mode} setMode={setMode} onDone={() => {
    queryClient.clear();
    setAuthenticated(true);
  }} />;
  if (!user) return <main className="loading"><RefreshCw/> 正在准备家长陪伴空间…</main>;
  if (user.role === "expert") return <ExpertApp username={user.username} logout={logout}/>;
  if (user.role === "admin") return <main className="auth"><div className="brand-mark"><ShieldCheck/></div><p className="eyebrow">管理员账户</p><h1>请进入系统管理后台</h1><p className="muted">管理员与家长、专家工作空间已完全分开。</p><button className="primary" onClick={() => location.href = "/admin/"}>打开管理后台</button><button className="danger" onClick={logout}>退出登录</button></main>;
  return <CoachApp username={user.username} switchToAba={() => {}} logout={logout} />;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><QueryClientProvider client={queryClient}><NetworkStatus/><App/></QueryClientProvider></React.StrictMode>
);
