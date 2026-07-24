import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Baby, BarChart3, BookOpen, Check, ChevronLeft, ChevronRight, CircleUserRound, HeartHandshake, Home, Inbox, MessageCircleHeart, PenLine, Play, Plus, Send, ShieldCheck, Smile, Sparkles, Sprout, Target, UserRoundCheck, WifiOff } from "lucide-react";
import { api, Child, ExpertClient, ExpertProfile, Session, Task } from "./api";
import "./styles.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 20_000 } } });
type Tab = "home" | "child" | "training" | "progress" | "me";
type ProductMode = "aba" | "coach";

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
    <h1>让每一次陪伴<br/>都看得见成长</h1>
    <p className="muted">专业的 ABA 家庭训练与家长成长支持</p>
    <form className="auth-card" onSubmit={submit}>
      <p className="entry-label">选择要进入的空间</p>
      <div className="entry-grid">
        <button type="button" className={`entry-option aba-entry ${mode === "aba" ? "selected" : ""}`} onClick={() => setMode("aba")}>
          <span className="entry-icon"><Target /></span>
          <span><strong>ABA 智能助手</strong><small>孩子档案 · 评估 · 训练</small></span>
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
      <button className={`primary ${mode === "coach" ? "coach-primary" : ""}`} disabled={username.length < 2 || password.length < 8}>
        {signup ? "创建家庭账户" : mode === "coach" ? "进入家长陪伴" : "进入 ABA 智能助手"}
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
    mutationFn: () => api.createChild({ name, diagnosis }),
    onSuccess: () => { query.invalidateQueries({ queryKey: ["children"] }); done(); }
  });
  return <section className="empty-state">
    <div className="round-icon"><Baby /></div>
    <h2>先建立孩子档案</h2>
    <p>只需基础信息，之后可以随时完善。</p>
    <input placeholder="孩子的小名" value={name} onChange={e => setName(e.target.value)} />
    <input placeholder="诊断信息（可选）" value={diagnosis} onChange={e => setDiagnosis(e.target.value)} />
    <button className="primary" onClick={() => mutation.mutate()} disabled={!name || mutation.isPending}><Plus size={18}/> 创建档案</button>
  </section>;
}

function HomePage({ child, go }: { child: Child; go: (tab: Tab) => void }) {
  const [helpMode, setHelpMode] = useState<"ai" | "expert">("ai");
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("你好，我可以和你一起分析孩子的行为，也能给出适合家庭练习的具体步骤。");
  const { data: history = [] } = useQuery({ queryKey: ["chat", "aba"], queryFn: () => api.chatMessages("aba") });
  useEffect(() => {
    const latest = [...history].reverse().find(item => item.role === "assistant");
    if (latest) setAnswer(latest.content);
  }, [history]);
  const chat = useMutation({ mutationFn: async () => {
    try { return await api.chatStream(message, child.id, setAnswer); }
    catch { return (await api.chat(message, child.id)).answer; }
  }, onMutate: () => setAnswer(""), onSuccess: data => {
    setAnswer(data);
    setMessage("");
    queryClient.invalidateQueries({ queryKey: ["chat", "aba"] });
  } });
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
  const { data: tasks = [] } = useQuery({ queryKey: ["tasks", child.id], queryFn: () => api.tasks(child.id) });
  return <>
    <header className="hero">
      <p className="eyebrow">下午好，家长</p>
      <h1>今天也从一小步开始</h1>
      <div className="child-pill"><span>{child.name.slice(0, 1)}</span><div><strong>{child.name}</strong><small>{child.diagnosis || "档案已建立"}</small></div></div>
    </header>
    <button className="task-highlight" onClick={() => go("training")}>
      <div><small>今日训练</small><strong>{tasks.filter(t => t.status !== "completed").length || "暂无"} 个待完成任务</strong></div>
      <ChevronRight/>
    </button>
    <section className="card chat-card">
      <div className="help-switch">
        <button className={helpMode === "ai" ? "active" : ""} onClick={() => setHelpMode("ai")}><Sparkles/>问 AI</button>
        <button className={helpMode === "expert" ? "active" : ""} onClick={() => setHelpMode("expert")}><UserRoundCheck/>问专家{Boolean(notificationData?.expert_unread) && <b>{notificationData!.expert_unread}</b>}</button>
      </div>
      {helpMode === "ai" ? <>
        <div className="section-title"><span><Sparkles size={18}/> ABA 智能问答</span><small>即时回答</small></div>
        <div className="bubble">{chat.isPending ? "正在查找知识库并整理回答…" : answer}</div>
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="描述一个具体场景…" /><button onClick={() => chat.mutate()} disabled={!message}>发送</button></div>
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
    <div className="quick-grid">
      <button onClick={() => go("child")}><Target/><span>能力评估<small>找到训练起点</small></span></button>
      <button onClick={() => go("progress")}><BarChart3/><span>成长进展<small>查看近期趋势</small></span></button>
    </div>
  </>;
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
  const { data } = useQuery({ queryKey: ["questions"], queryFn: api.questions });
  const [answers, setAnswers] = useState<Record<string, number>>(() => JSON.parse(localStorage.getItem(`assessment_${child.id}`) || "{}"));
  const [assessmentKey] = useState(() => {
    const storageKey = `assessment_key_${child.id}`;
    const existing = localStorage.getItem(storageKey);
    if (existing) return existing;
    const created = crypto.randomUUID();
    localStorage.setItem(storageKey, created);
    return created;
  });
  const [questionIndex, setQuestionIndex] = useState(0);
  const submit = useMutation({
    mutationFn: () => api.submitAssessment(child.id, answers, assessmentKey),
    onSuccess: () => {
      localStorage.removeItem(`assessment_${child.id}`);
      localStorage.removeItem(`assessment_key_${child.id}`);
      queryClient.invalidateQueries({ queryKey: ["tasks", child.id] });
    }
  });
  useEffect(() => localStorage.setItem(`assessment_${child.id}`, JSON.stringify(answers)), [answers, child.id]);
  return <>
    <section className="profile-card"><div className="avatar">{child.name.slice(0, 1)}</div><div><p className="eyebrow">当前孩子</p><h2>{child.name}</h2><p>{child.diagnosis || "尚未填写诊断信息"}</p></div></section>
    <div className="child-switcher">{allChildren.map(item => <button className={item.id === child.id ? "active" : ""} onClick={() => switchChild.mutate(item.id)} key={item.id}>{item.name}</button>)}<button className="add" onClick={() => setShowAdd(!showAdd)}><Plus size={15}/> 添加</button></div>
    {showAdd && <div className="inline-add"><input placeholder="孩子的小名" value={newChildName} onChange={e => setNewChildName(e.target.value)}/><button onClick={() => addChild.mutate()} disabled={!newChildName.trim()}>保存</button></div>}
    <div className="page-heading"><p className="eyebrow">能力评估</p><h1>找到此刻最合适的起点</h1><p>根据孩子近两周的真实表现作答。不确定时选择“有时”。</p></div>
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
  const { data: tasks = [], isLoading } = useQuery({ queryKey: ["tasks", child.id], queryFn: () => api.tasks(child.id) });
  const [session, setSession] = useState<Session | null>(null);
  const { data: activeSession } = useQuery({ queryKey: ["active-session", child.id], queryFn: () => api.activeSession(child.id) });
  useEffect(() => { if (activeSession) setSession(activeSession); }, [activeSession]);
  const start = useMutation({ mutationFn: (task: Task) => api.createSession(child.id, task), onSuccess: setSession });
  const trial = useMutation({ mutationFn: (result: string) => api.addTrial(session!.id, result), onSuccess: setSession });
  const undo = useMutation({ mutationFn: () => api.undoTrial(session!.id), onSuccess: setSession });
  const finish = useMutation({ mutationFn: () => api.finishSession(session!.id), onSuccess: data => { setSession(data); queryClient.invalidateQueries({ queryKey: ["tasks", child.id] }); } });
  if (session && session.status === "active") return <section className="training-live">
    <p className="eyebrow">正在训练</p><h1>{session.skill_name}</h1><p>每次呈现刺激后，记录孩子最少辅助下的反应。</p>
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
    <div className="training-tabs"><button className={view === "tasks" ? "active" : ""} onClick={() => setView("tasks")}>当前任务</button><button className={view === "flashcards" ? "active" : ""} onClick={() => setView("flashcards")}>图片卡</button></div>
    {view === "flashcards" ? <FlashcardCenter/> : isLoading ? <p>正在加载任务…</p> : tasks.length === 0 ? <section className="empty-state"><Target/><h2>还没有训练任务</h2><p>先去“孩子”页完成能力评估。</p></section> :
      <section className="task-list">{tasks.map(task => <article className={`task-card ${task.status}`} key={task.id}>
        <div className="task-icon">{task.status === "completed" ? <Check/> : <Target/>}</div>
        <div><small>{task.category}</small><strong>{task.name}</strong><p>{task.description}</p></div>
        {task.status !== "completed" && <button onClick={() => start.mutate(task)} aria-label={`开始${task.name}`}><Play size={18}/></button>}
      </article>)}</section>}
    {session?.status === "completed" && <div className="success-banner"><Check/> 本次训练已保存，独立正确率 {session.percentage}%</div>}
  </>;
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
      {reports.map(report => <div className={`report-item ${report.status}`} key={report.id}><strong>{report.title}</strong><span className="report-status">{report.status === "pending" ? "生成中" : report.status === "failed" ? "失败" : "已完成"}</span><p>{report.summary}</p>{report.content?.next_steps?.length ? <ul>{report.content.next_steps.map((step: string) => <li key={step}>{step}</li>)}</ul> : null}{report.file_url ? <button className="text-button" onClick={() => api.downloadReport(report.id)}>下载 PDF 报告</button> : null}</div>)}
    </section>
  </>;
}

function CoachApp({ username, switchToAba, logout }: { username: string; switchToAba: () => void; logout: () => void }) {
  type CoachTab = "chat" | "emotion" | "growth" | "journal" | "knowledge";
  const [tab, setTab] = useState<CoachTab>("chat");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    "欢迎回来。这里关注的不是你今天完成了多少，而是你此刻过得怎么样。"
  ]);
  const [mood, setMood] = useState("疲惫");
  const [journal, setJournal] = useState("");
  const [articleId, setArticleId] = useState<string | null>(null);
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
  const moodMutation = useMutation({ mutationFn: () => api.saveMood(mood), onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["coach-moods"] });
    queryClient.invalidateQueries({ queryKey: ["coach-overview"] });
  }});
  const journalMutation = useMutation({ mutationFn: () => api.saveJournal(journal), onSuccess: () => {
    setJournal("");
    queryClient.invalidateQueries({ queryKey: ["coach-journals"] });
    queryClient.invalidateQueries({ queryKey: ["coach-overview"] });
  }});
  const send = () => {
    if (!message.trim()) return;
    coachChatMutation.mutate(message);
  };
  const headers: Record<CoachTab, [string, string]> = {
    chat: ["陪伴", `${username}，先说说现在怎么了`],
    emotion: ["情绪", "看见这一周的状态变化"],
    growth: ["成长", "五个阶段，慢慢来"],
    journal: ["日记", "今天，留一句话给自己"],
    knowledge: ["知识库", "为家长准备的成长内容"]
  };
  const page = {
    chat: <>
      <div className="mood-picker">{["😔 焦虑", "😩 疲惫", "😢 悲伤", "😤 愤怒"].map(item => <button className={mood === item.slice(3) ? "selected" : ""} onClick={() => setMood(item.slice(3))} key={item}>{item}</button>)}</div>
      <section className="card coach-chat">
        <div className="section-title"><span><MessageCircleHeart size={19}/> 陪伴对话</span><small>ACT 成长支持</small></div>
        {messages.map((item, index) => <div className={coachHistory[index]?.role === "user" ? "coach-bubble user-message" : "coach-bubble"} key={index}>{item}</div>)}
        {coachChatMutation.isPending && <div className="coach-bubble">我在听，也在认真想怎么回应你…</div>}
        <div className="chat-input"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="写一句现在最困扰你的事" /><button onClick={send} disabled={!message.trim() || coachChatMutation.isPending}>发送</button></div>
      </section>
      <section className="coach-tip"><strong>今晚可以这样减轻一点</strong><p>把原计划 10 分钟改成 2 分钟，然后请家人接手洗漱前的准备。</p><button onClick={() => setTab("journal")}>写进今日反思</button></section>
    </>,
    emotion: <>
      <section className="card emotion-panel"><div className="fake-chart"><i/><i/><i/><i/><i/><i/><i/></div><div><span>本周平均</span><strong>疲惫偏高</strong></div><div><span>需要关注</span><strong>周三、周五</strong></div></section>
      <h3 className="coach-section-head">记录今天的情绪</h3>
      <div className="mood-picker large">{["😊 平静", "😩 疲惫", "😔 低落", "🫂 孤独"].map(item => <button className={mood === item.slice(3) ? "selected" : ""} onClick={() => setMood(item.slice(3))} key={item}>{item}</button>)}</div>
      <button className="coach-main-button" onClick={() => moodMutation.mutate()}>{moodMutation.isSuccess ? "今天的情绪已保存" : `记一笔：今天感到${mood}`}</button>
      {savedMoods.length > 0 && <p className="saved-summary">最近已记录 {savedMoods.length} 天 · 今日：{coachOverview?.mood_today || mood}</p>}
    </>,
    growth: <div className="growth-list">
      {[
        ["① 觉察", "已完成", "看见自己的情绪和需求，不急着改变。"],
        ["② 接纳", "进行中", "允许疲惫、自责这些感受存在，它们不代表你做得不好。"],
        ["③ 连接", "未开始", "找到能支持你的人和资源，不必一个人扛。"],
        ["④ 行动", "未开始", "从一个小到不会失败的承诺开始。"],
        ["⑤ 整合", "未开始", "把照顾自己变成日常的一部分。"]
      ].map(([name, status, copy]) => <article className={status === "进行中" ? "active" : status === "已完成" ? "done" : ""} key={name}><div><strong>{name}</strong><span>{status}</span></div><p>{copy}</p>{status === "进行中" && <button>继续本阶段练习</button>}</article>)}
    </div>,
    journal: <>
      <section className="card journal-card"><p>今天有没有一个瞬间，你觉得自己其实做得还不错？</p><p>如果朋友处在你的位置，你会对他说什么？</p><textarea value={journal} onChange={e => setJournal(e.target.value)} placeholder="想到什么写什么，不必完整"/><button className="coach-main-button" disabled={!journal.trim() || journalMutation.isPending} onClick={() => journalMutation.mutate()}>保存今日反思</button></section>
      <h3 className="coach-section-head">过往记录</h3>
      <div className="journal-history">{savedJournals.length ? savedJournals.map(item => <article key={item.id}><time>{new Date(item.created_at).toLocaleDateString("zh-CN", {month: "short", day: "numeric"})}</time><div><strong>{item.content.slice(0, 18)}</strong><p>{item.content}</p></div></article>) : <p className="muted">保存第一篇反思后会显示在这里。</p>}</div>
    </>,
    knowledge: articleId ? <section className="article-detail"><button className="back-link" onClick={() => setArticleId(null)}><ChevronLeft/> 返回知识库</button>{selectedArticle ? <><p className="eyebrow">{selectedArticle.category} · {selectedArticle.read_time}</p><h2>{selectedArticle.title}</h2><p className="article-summary">{selectedArticle.summary}</p><div className="article-content">{selectedArticle.content}</div></> : <p>正在加载文章…</p>}</section> : <>
      <div className="knowledge-chips"><span>养育压力</span><span>自我关怀</span><span>情绪</span><span>关系</span><span>正念</span></div>
      <div className="knowledge-list">{articleCatalog?.items.map(item => <button key={item.id} onClick={() => setArticleId(item.id)}><small>{item.subcategory || item.category} · {item.read_time}</small><strong>{item.title}</strong><p>{item.summary}</p><ChevronRight/></button>)}</div>
    </>
  }[tab];
  const navItems = [
    ["chat", "陪伴", MessageCircleHeart], ["emotion", "情绪", Smile], ["growth", "成长", Sprout],
    ["journal", "日记", PenLine], ["knowledge", "知识库", BookOpen]
  ] as const;
  return <main className="coach-shell">
    <header className="coach-hero compact">
      <button onClick={switchToAba}><ChevronLeft /> ABA 智能助手</button>
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
  if (user.role === "admin") return <main className="auth"><div className="brand-mark"><ShieldCheck/></div><p className="eyebrow">管理员账户</p><h1>请进入系统管理后台</h1><p className="muted">管理员与家长、专家工作空间已完全分开。</p><button className="primary" onClick={() => location.href = "http://localhost:5174/"}>打开管理后台</button><button className="danger" onClick={logout}>退出登录</button></main>;
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
