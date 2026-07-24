import asyncio
import io
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import AiUsage, Assessment, AuditLog, ChatMessage, Child, ExpertAssignment, ExpertMessage, ExpertProfile, GrowthProgress, JournalEntry, MoodEntry, RefreshToken, Report, SystemEvent, Task, TrainingSession, Trial, User
from .schemas import (
    AdminPasswordReset, AdminUserCreate, AssessmentOut, AssessmentSubmit, ChatAnswer, ChatOut, ChatRequest, ChildIn, ChildOut, Credentials,
    ExpertProfileIn, ExpertQuestion, ExpertReply, ExpertSelect, JournalIn, JournalOut, MoodIn, MoodOut, RefreshRequest, ReportOut, ReportRequest, SessionIn, SessionOut, TaskIn,
    TaskOut, TaskPatch, TokenPair, TrialIn, UserOut,
)
from .services.assessment import questions as real_assessment_questions, score_and_tasks
from .services.ai import generate
from .services.flashcards import card as flashcard_image, catalog as flashcard_catalog
from .services.jobs import enqueue_report
from .services.coach_content import article as coach_article, articles as coach_articles
from .services.rate_limit import limiter
from .services.storage import get_storage
from .security import (
    create_access_token, current_user, hash_password, random_refresh_token,
    token_digest, verify_password,
)

settings = get_settings()
upload_root = Path(settings.upload_path)
request_counts: Counter[tuple[str, str, int]] = Counter()
request_duration_ms: Counter[tuple[str, str]] = Counter()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_runtime()
    if settings.environment == "development":
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", openapi_url="/api/v1/openapi.json", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        event_db = SessionLocal()
        try:
            event_db.add(SystemEvent(
                level="error", category="api", message=type(exc).__name__,
                details={"path": request.url.path, "method": request.method, "request_id": request_id},
            ))
            event_db.commit()
        finally:
            event_db.close()
        raise
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    request_counts[(request.method, path, response.status_code)] += 1
    request_duration_ms[(request.method, path)] += round((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    return response


def add_ai_usage(db: Session, user: User, product: str, call) -> None:
    db.add(AiUsage(
        user_id=user.id, product=product, provider=call.provider, model=call.model,
        success=call.success, fallback=call.fallback, prompt_tokens=call.prompt_tokens,
        completion_tokens=call.completion_tokens, latency_ms=call.latency_ms,
        error_type=call.error_type,
    ))


def owned_child(db: Session, user: User, child_id: str) -> Child:
    child = db.scalar(select(Child).where(Child.id == child_id, Child.user_id == user.id))
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    db.add(AuditLog(
        user_id=user.id, action="child.data_accessed", resource_type="child",
        resource_id=child.id, details={"owner_verified": True},
    ))
    db.commit()
    return child


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


def expert_user(user: User = Depends(current_user)) -> User:
    if user.role != "expert":
        raise HTTPException(403, "需要专家权限")
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    raw = random_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_digest(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    ))
    db.commit()
    return TokenPair(access_token=create_access_token(user), refresh_token=raw)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(1))
    checks = {"database": "ok", "redis": "disabled"}
    if settings.redis_url:
        from redis import Redis
        Redis.from_url(settings.redis_url).ping()
        checks["redis"] = "ok"
    return {"status": "ready", "checks": checks}


@app.get("/metrics", include_in_schema=False)
def metrics():
    lines = [
        "# HELP aba_http_requests_total Total HTTP requests.",
        "# TYPE aba_http_requests_total counter",
    ]
    for (method, path, status), value in sorted(request_counts.items()):
        lines.append(f'aba_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}')
    lines += [
        "# HELP aba_http_request_duration_milliseconds_total Cumulative HTTP request duration.",
        "# TYPE aba_http_request_duration_milliseconds_total counter",
    ]
    for (method, path), value in sorted(request_duration_ms.items()):
        lines.append(f'aba_http_request_duration_milliseconds_total{{method="{method}",path="{path}"}} {value}')
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/", include_in_schema=False)
def open_mobile_web():
    """Developer convenience: opening the API port leads to the PWA."""
    return RedirectResponse("http://localhost:5173/")


@app.post("/api/v1/auth/register", response_model=TokenPair, status_code=201)
def register(body: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "用户名已存在")
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return issue_tokens(db, user)


@app.post("/api/v1/auth/login", response_model=TokenPair)
def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    limiter.check(request, "login", settings.login_rate_limit, 300)
    user = db.scalar(select(User).where(User.username == body.username))
    now = datetime.now(timezone.utc)
    if user and not user.is_active:
        raise HTTPException(403, "账户已停用")
    if user and user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now:
        raise HTTPException(429, "登录尝试过多，请稍后再试")
    ok, legacy = verify_password(body.password, user.password_hash) if user else (False, False)
    if not user or not ok:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.commit()
        raise HTTPException(401, "用户名或密码错误")
    user.failed_logins = 0
    user.locked_until = None
    if legacy:
        user.password_hash = hash_password(body.password)
    db.commit()
    return issue_tokens(db, user)


@app.post("/api/v1/auth/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == token_digest(body.refresh_token),
        RefreshToken.revoked_at.is_(None),
    ))
    now = datetime.now(timezone.utc)
    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(401, "刷新令牌无效")
    stored.revoked_at = now
    user = db.get(User, stored.user_id)
    db.commit()
    return issue_tokens(db, user)


@app.post("/api/v1/auth/logout", status_code=204)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_digest(body.refresh_token)))
    if stored:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/v1/children", response_model=list[ChildOut])
def list_children(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Child).where(Child.user_id == user.id).order_by(Child.created_at)).all()


@app.post("/api/v1/children", response_model=ChildOut, status_code=201)
def create_child(body: ChildIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    has_child = db.scalar(select(func.count()).select_from(Child).where(Child.user_id == user.id))
    child = Child(user_id=user.id, is_current=not bool(has_child), **body.model_dump())
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@app.patch("/api/v1/children/{child_id}/current", response_model=ChildOut)
def set_current_child(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = owned_child(db, user, child_id)
    for row in db.scalars(select(Child).where(Child.user_id == user.id)):
        row.is_current = row.id == child.id
    db.commit()
    db.refresh(child)
    return child


@app.get("/api/v1/assessments/questions")
def assessment_questions(user: User = Depends(current_user)):
    return {"items": real_assessment_questions()}


@app.post("/api/v1/assessments", response_model=AssessmentOut)
def submit_assessment(
    body: AssessmentSubmit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    owned_child(db, user, body.child_id)
    existing = db.scalar(select(Assessment).where(
        Assessment.user_id == user.id, Assessment.idempotency_key == idempotency_key
    ))
    if existing:
        return AssessmentOut.model_validate(existing)
    result, task_specs = score_and_tasks(body.answers)
    values = list(result["domain_scores"].values())
    score = round(sum(values) / max(len(values), 1), 1)
    stage = f"Level {result['overall_level']}"
    assessment = Assessment(
        user_id=user.id, child_id=body.child_id, answers=body.answers,
        score=score, stage=stage, idempotency_key=idempotency_key,
    )
    generated = [
        Task(
            user_id=user.id, child_id=body.child_id, name=item["name"],
            category=item["category"], description=item["description"], source="assessment",
        )
        for item in task_specs
    ]
    db.add(assessment)
    db.add_all(generated)
    db.commit()
    db.refresh(assessment)
    return AssessmentOut(
        **AssessmentOut.model_validate(assessment).model_dump(exclude={"generated_task_ids"}),
        generated_task_ids=[task.id for task in generated],
    )


@app.get("/api/v1/tasks", response_model=list[TaskOut])
def list_tasks(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    return db.scalars(select(Task).where(Task.user_id == user.id, Task.child_id == child_id).order_by(Task.created_at.desc())).all()


@app.post("/api/v1/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, body.child_id)
    task = Task(user_id=user.id, **body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/api/v1/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not task:
        raise HTTPException(404, "任务不存在")
    task.status = body.status
    db.commit()
    db.refresh(task)
    return task


def session_out(session: TrainingSession) -> SessionOut:
    values = [trial.result for trial in session.trials]
    percentage = round(values.count("I") / len(values) * 100) if values else 0
    return SessionOut(
        id=session.id, child_id=session.child_id, task_id=session.task_id,
        skill_name=session.skill_name, status=session.status, created_at=session.created_at,
        finished_at=session.finished_at, trials=values, percentage=percentage,
    )


@app.get("/api/v1/training-sessions/active", response_model=SessionOut | None)
def active_training_session(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == child_id,
        TrainingSession.status == "active",
    ).order_by(TrainingSession.created_at.desc()))
    return session_out(session) if session else None


@app.post("/api/v1/training-sessions", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    owned_child(db, user, body.child_id)
    existing = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.idempotency_key == idempotency_key
    ))
    if existing:
        return session_out(existing)
    active = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == body.child_id,
        TrainingSession.status == "active",
    ).order_by(TrainingSession.created_at.desc()))
    if active:
        return session_out(active)
    session = TrainingSession(user_id=user.id, idempotency_key=idempotency_key, **body.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@app.post("/api/v1/training-sessions/{session_id}/trials", response_model=SessionOut)
def add_trial(session_id: str, body: TrialIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    if not session or session.status != "active":
        raise HTTPException(404, "训练会话不存在或已结束")
    db.add(Trial(session_id=session.id, result=body.result, sequence=len(session.trials) + 1))
    db.commit()
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(TrainingSession.id == session_id))
    return session_out(session)


@app.delete("/api/v1/training-sessions/{session_id}/trials/latest", response_model=SessionOut)
def undo_trial(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    if not session:
        raise HTTPException(404, "训练会话不存在")
    if session.trials:
        db.delete(session.trials[-1])
        db.commit()
        db.expire_all()
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(TrainingSession.id == session_id))
    return session_out(session)


@app.post("/api/v1/training-sessions/{session_id}/finish", response_model=SessionOut)
def finish_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    if not session:
        raise HTTPException(404, "训练会话不存在")
    session.status = "completed"
    session.finished_at = datetime.now(timezone.utc)
    if session.task_id:
        task = db.scalar(select(Task).where(Task.id == session.task_id, Task.user_id == user.id))
        if task:
            task.status = "completed"
    db.commit()
    return session_out(session)


@app.get("/api/v1/progress")
def progress(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    sessions = db.scalars(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == child_id,
        TrainingSession.status == "completed",
    ).order_by(TrainingSession.created_at.desc())).all()
    items = [session_out(item) for item in sessions]
    return {
        "completed_sessions": len(items),
        "training_days": len({item.created_at.date().isoformat() for item in items}),
        "average_percentage": round(sum(item.percentage for item in items) / len(items)) if items else 0,
        "timeline": items[:20],
    }


@app.post("/api/v1/reports", response_model=ReportOut, status_code=202)
def generate_report(body: ReportRequest, background: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = owned_child(db, user, body.child_id)
    report = Report(
        user_id=user.id, child_id=child.id, title=f"{child.name}的训练进展报告",
        status="pending", summary="报告正在生成，请稍候。", content={},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    enqueue_report(report.id, background)
    return report


@app.get("/api/v1/reports", response_model=list[ReportOut])
def list_reports(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    reports = db.scalars(select(Report).where(
        Report.user_id == user.id, Report.child_id == child_id
    ).order_by(Report.created_at.desc())).all()
    return [
        ReportOut(
            **ReportOut.model_validate(report).model_dump(exclude={"file_url"}),
            file_url=f"/api/v1/reports/{report.id}/file" if report.file_key else None,
        )
        for report in reports
    ]


@app.get("/api/v1/reports/{report_id}/file")
def download_report(report_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    report = db.scalar(select(Report).where(Report.id == report_id, Report.user_id == user.id))
    if not report or not report.file_key:
        raise HTTPException(404, "报告文件尚未生成")
    try:
        content, content_type = get_storage().get(report.file_key)
    except FileNotFoundError:
        raise HTTPException(404, "报告文件不存在")
    filename = f"ABA-report-{report.created_at.date().isoformat()}.pdf"
    return Response(
        content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def safe_answer(message: str) -> str:
    risk_words = ("自杀", "伤害孩子", "不想活", "杀了")
    if any(word in message for word in risk_words):
        return "你描述的情况可能涉及立即安全风险。请先离开危险物品、联系可信赖的家人或当地紧急服务，并尽快寻求专业人员现场帮助。"
    return "先记录行为发生前的情境、具体行为和随后结果（ABC）。从一次只调整一个变量开始，并强化孩子可以替代问题行为的沟通方式。"


@app.post("/api/v1/chat/stream")
async def chat_stream(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.child_id:
        owned_child(db, user, body.child_id)
    history = [
        {"role": item.role, "content": item.content}
        for item in db.scalars(select(ChatMessage).where(
            ChatMessage.user_id == user.id, ChatMessage.product == "aba"
        ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    ]
    answer, sources, ai_call = generate("aba", body.message, history)
    db.add_all([
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="user", content=body.message),
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="assistant", content=answer, sources=sources),
    ])
    add_ai_usage(db, user, "aba", ai_call)
    db.commit()
    async def chunks():
        parts = answer.split("，")
        for index, part in enumerate(parts):
            suffix = "，" if index < len(parts) - 1 else ""
            yield f"data: {part}{suffix}\n\n"
            await asyncio.sleep(0)
        yield "event: done\ndata: [DONE]\n\n"
    return StreamingResponse(chunks(), media_type="text/event-stream")


@app.post("/api/v1/chat/public")
def public_chat(body: ChatRequest, request: Request):
    limiter.check(request, "public-chat", settings.public_chat_rate_limit, 60)
    return {"answer": safe_answer(body.message), "anonymous": True}


@app.post("/api/v1/chat", response_model=ChatAnswer)
def chat(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.child_id:
        owned_child(db, user, body.child_id)
    history_rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == "aba"
    ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    answer, sources, ai_call = generate("aba", body.message, [{"role": row.role, "content": row.content} for row in history_rows])
    db.add_all([
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="user", content=body.message),
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="assistant", content=answer, sources=sources),
    ])
    add_ai_usage(db, user, "aba", ai_call)
    db.commit()
    return ChatAnswer(answer=answer, sources=[{"title": item["title"]} for item in sources])


@app.get("/api/v1/chat/messages", response_model=list[ChatOut])
def chat_messages(product: str = "aba", user: User = Depends(current_user), db: Session = Depends(get_db)):
    if product not in {"aba", "coach"}:
        raise HTTPException(400, "未知产品")
    rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == product
    ).order_by(ChatMessage.created_at.desc()).limit(50)).all()
    return rows[::-1]


@app.get("/api/v1/coach/overview")
def coach_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today_mood = db.scalar(select(MoodEntry).where(MoodEntry.user_id == user.id).order_by(MoodEntry.entry_date.desc()))
    journal_count = db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user.id))
    return {"mood_today": today_mood.mood if today_mood else None, "journal_count": journal_count, "growth_stage": "接纳", "message": "今天也给自己留一点空间。"}


@app.get("/api/v1/coach/moods", response_model=list[MoodOut])
def list_moods(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(MoodEntry).where(MoodEntry.user_id == user.id).order_by(MoodEntry.entry_date.desc()).limit(30)).all()


@app.post("/api/v1/coach/moods", response_model=MoodOut)
def save_mood(body: MoodIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = db.scalar(select(MoodEntry).where(MoodEntry.user_id == user.id, MoodEntry.entry_date == datetime.now().date()))
    if entry:
        entry.mood, entry.intensity, entry.note = body.mood, body.intensity, body.note
    else:
        entry = MoodEntry(user_id=user.id, **body.model_dump())
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.get("/api/v1/coach/journals", response_model=list[JournalOut])
def list_journals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id).order_by(JournalEntry.created_at.desc()).limit(50)).all()


@app.post("/api/v1/coach/journals", response_model=JournalOut, status_code=201)
def save_journal(body: JournalIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = JournalEntry(user_id=user.id, **body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.get("/api/v1/coach/growth")
def growth(user: User = Depends(current_user), db: Session = Depends(get_db)):
    saved = {item.stage: item.status for item in db.scalars(select(GrowthProgress).where(GrowthProgress.user_id == user.id))}
    return {"stages": [{"stage": stage, "status": saved.get(stage, "completed" if stage == 1 else "active" if stage == 2 else "locked")} for stage in range(1, 6)]}


@app.get("/api/v1/coach/articles")
def list_coach_articles(user: User = Depends(current_user)):
    return {"items": coach_articles()}


@app.get("/api/v1/coach/articles/{article_id}")
def get_coach_article(article_id: str, user: User = Depends(current_user)):
    item = coach_article(article_id)
    if not item:
        raise HTTPException(404, "文章不存在")
    return item


@app.post("/api/v1/coach/chat", response_model=ChatAnswer)
def coach_chat(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    history_rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == "coach"
    ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    answer, _, ai_call = generate("coach", body.message, [{"role": row.role, "content": row.content} for row in history_rows])
    db.add_all([
        ChatMessage(user_id=user.id, product="coach", role="user", content=body.message),
        ChatMessage(user_id=user.id, product="coach", role="assistant", content=answer),
    ])
    add_ai_usage(db, user, "coach", ai_call)
    db.commit()
    return ChatAnswer(answer=answer)


@app.get("/api/v1/flashcards")
def flashcards(user: User = Depends(current_user)):
    return {"groups": flashcard_catalog()}


@app.get("/api/v1/flashcards/{category}/{index}")
def flashcard(category: str, index: int, user: User = Depends(current_user)):
    data, label = flashcard_image(category, index)
    if data is None:
        raise HTTPException(404, "卡片不存在")
    if data.startswith(b"\x89PNG"):
        media_type = "image/png"
    elif data.startswith(b"\xff\xd8"):
        media_type = "image/jpeg"
    elif data.startswith(b"RIFF"):
        media_type = "image/webp"
    else:
        media_type = "application/octet-stream"
    return Response(data, media_type=media_type, headers={"X-Card-Label": label})


@app.get("/api/v1/admin/overview")
def admin_overview(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "children": db.scalar(select(func.count()).select_from(Child)),
        "training_sessions": db.scalar(select(func.count()).select_from(TrainingSession)),
        "reports": db.scalar(select(func.count()).select_from(Report)),
    }


@app.get("/api/v1/admin/users")
def admin_users(
    admin: User = Depends(admin_user), db: Session = Depends(get_db),
    limit: int = 20, offset: int = 0, q: str = "", role: str | None = None, active: bool | None = None,
):
    conditions = []
    if q.strip():
        conditions.append(User.username.ilike(f"%{q.strip()}%"))
    if role:
        conditions.append(User.role == role)
    if active is not None:
        conditions.append(User.is_active.is_(active))
    base = select(User).where(*conditions)
    total = db.scalar(select(func.count()).select_from(User).where(*conditions))
    users = db.scalars(base.order_by(User.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 100))).all()
    return {"total": total, "items": [
        {
            "id": item.id, "username": item.username, "role": item.role,
            "created_at": item.created_at,
            "is_active": item.is_active,
            "children_count": db.scalar(select(func.count()).select_from(Child).where(Child.user_id == item.id)),
        }
        for item in users
    ]}


@app.post("/api/v1/admin/users", status_code=201)
def create_user_by_admin(body: AdminUserCreate, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "用户名已存在")
    target = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(target)
    db.flush()
    db.add(AuditLog(user_id=admin.id, action="admin.user.created", resource_type="user", resource_id=target.id, details={"role": body.role}))
    db.commit()
    db.refresh(target)
    return {"id": target.id, "username": target.username, "role": target.role, "created_at": target.created_at, "is_active": True, "children_count": 0}


@app.patch("/api/v1/admin/users/{user_id}/role")
def set_user_role(user_id: str, role: str, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    if role not in {"user", "expert", "admin"}:
        raise HTTPException(400, "未知角色")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "用户不存在")
    if target.id == admin.id and role != "admin":
        raise HTTPException(400, "不能取消自己的管理员权限")
    target.role = role
    db.add(AuditLog(user_id=admin.id, action="admin.user.role_changed", resource_type="user", resource_id=target.id, details={"role": role}))
    db.commit()
    return {"id": target.id, "role": target.role}


@app.get("/api/v1/admin/users/{user_id}")
def admin_user_detail(user_id: str, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "用户不存在")
    assignment = db.get(ExpertAssignment, target.id)
    if assignment and assignment.status != "active":
        assignment = None
    expert = db.get(User, assignment.expert_id) if assignment else None
    return {
        "id": target.id, "username": target.username, "role": target.role, "created_at": target.created_at,
        "is_active": target.is_active,
        "children_count": db.scalar(select(func.count()).select_from(Child).where(Child.user_id == target.id)),
        "training_count": db.scalar(select(func.count()).select_from(TrainingSession).where(TrainingSession.user_id == target.id)),
        "reports_count": db.scalar(select(func.count()).select_from(Report).where(Report.user_id == target.id)),
        "expert_name": expert.username if expert else None,
    }


@app.patch("/api/v1/admin/users/{user_id}/status")
def set_user_status(user_id: str, active: bool, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "用户不存在")
    if target.id == admin.id and not active:
        raise HTTPException(400, "不能停用自己的管理员账户")
    target.is_active = active
    if active:
        target.locked_until = None
    if not active:
        db.execute(delete(RefreshToken).where(RefreshToken.user_id == target.id))
    db.add(AuditLog(user_id=admin.id, action="admin.user.status_changed", resource_type="user", resource_id=target.id, details={"active": active}))
    db.commit()
    return {"id": target.id, "is_active": active}


@app.patch("/api/v1/admin/users/{user_id}/password")
def reset_user_password(user_id: str, body: AdminPasswordReset, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "用户不存在")
    target.password_hash = hash_password(body.password)
    target.failed_logins = 0
    target.locked_until = None
    db.execute(delete(RefreshToken).where(RefreshToken.user_id == target.id))
    db.add(AuditLog(user_id=admin.id, action="admin.user.password_reset", resource_type="user", resource_id=target.id, details={}))
    db.commit()
    return {"id": target.id, "password_reset": True}


@app.get("/api/v1/admin/audit-logs")
def admin_audit_logs(admin: User = Depends(admin_user), db: Session = Depends(get_db), limit: int = 50):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 100))).all()
    actors = {item.id: item.username for item in db.scalars(select(User)).all()}
    return {"items": [
        {
            "id": item.id, "actor": actors.get(item.user_id, "系统"), "action": item.action,
            "resource_id": item.resource_id, "details": item.details, "created_at": item.created_at,
        }
        for item in rows
    ]}


@app.get("/api/v1/admin/operations")
def admin_operations(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    ai_total = db.scalar(select(func.count()).select_from(AiUsage).where(AiUsage.created_at >= since)) or 0
    ai_fallback = db.scalar(select(func.count()).select_from(AiUsage).where(
        AiUsage.created_at >= since, AiUsage.fallback.is_(True)
    )) or 0
    tokens = db.execute(select(
        func.coalesce(func.sum(AiUsage.prompt_tokens), 0),
        func.coalesce(func.sum(AiUsage.completion_tokens), 0),
        func.coalesce(func.avg(AiUsage.latency_ms), 0),
    ).where(AiUsage.created_at >= since)).one()
    queue = {"mode": "local", "queued": 0, "started": 0, "failed": 0, "scheduled": 0}
    if settings.redis_url:
        try:
            from redis import Redis
            from rq import Queue
            from rq.registry import FailedJobRegistry, ScheduledJobRegistry, StartedJobRegistry

            connection = Redis.from_url(settings.redis_url)
            reports_queue = Queue("reports", connection=connection)
            queue = {
                "mode": "redis", "queued": reports_queue.count,
                "started": StartedJobRegistry("reports", connection=connection).count,
                "failed": FailedJobRegistry("reports", connection=connection).count,
                "scheduled": ScheduledJobRegistry("reports", connection=connection).count,
            }
        except Exception as exc:
            queue = {"mode": "unavailable", "queued": 0, "started": 0, "failed": 0, "scheduled": 0, "error": type(exc).__name__}
    events = db.scalars(select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(20)).all()
    return {
        "queue": queue,
        "reports": {
            "pending": db.scalar(select(func.count()).select_from(Report).where(Report.status == "pending")) or 0,
            "failed": db.scalar(select(func.count()).select_from(Report).where(Report.status == "failed")) or 0,
            "completed": db.scalar(select(func.count()).select_from(Report).where(Report.status == "completed")) or 0,
        },
        "ai_24h": {
            "calls": ai_total, "fallbacks": ai_fallback,
            "prompt_tokens": tokens[0], "completion_tokens": tokens[1],
            "average_latency_ms": round(float(tokens[2] or 0)),
        },
        "events": [
            {
                "id": item.id, "level": item.level, "category": item.category,
                "message": item.message, "details": item.details, "created_at": item.created_at,
            }
            for item in events
        ],
    }


@app.post("/api/v1/admin/reports/{report_id}/retry", status_code=202)
def retry_report(
    report_id: str, background: BackgroundTasks,
    admin: User = Depends(admin_user), db: Session = Depends(get_db),
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    if report.status != "failed":
        raise HTTPException(409, "只有失败的报告可以重试")
    report.status = "pending"
    report.summary = "报告正在重新生成，请稍候。"
    db.add(AuditLog(
        user_id=admin.id, action="admin.report.retried", resource_type="report",
        resource_id=report.id, details={},
    ))
    db.commit()
    enqueue_report(report.id, background)
    return {"id": report.id, "status": "pending"}


@app.get("/api/v1/experts")
def list_experts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    selected = db.get(ExpertAssignment, user.id)
    if selected and selected.status != "active":
        selected = None
    experts = db.scalars(select(User).where(User.role == "expert", User.is_active.is_(True)).order_by(User.username)).all()
    items = []
    for item in experts:
        profile = db.get(ExpertProfile, item.id)
        client_count = db.scalar(select(func.count()).select_from(ExpertAssignment).where(
            ExpertAssignment.expert_id == item.id, ExpertAssignment.status == "active"
        ))
        accepting = profile.accepting_clients if profile else True
        max_clients = profile.max_clients if profile else 30
        if not accepting and (not selected or selected.expert_id != item.id):
            continue
        items.append({
            "id": item.id,
            "name": profile.display_name if profile else item.username,
            "title": profile.title if profile else "家庭支持专家",
            "specialties": profile.specialties if profile else [],
            "bio": profile.bio if profile else "",
            "credentials": profile.credentials if profile else "",
            "avatar_url": profile.avatar_url if profile else None,
            "accepting_clients": accepting and client_count < max_clients,
            "client_count": client_count,
        })
    return {
        "selected_expert_id": selected.expert_id if selected else None,
        "items": items,
    }


@app.put("/api/v1/experts/selection")
def select_expert(body: ExpertSelect, user: User = Depends(current_user), db: Session = Depends(get_db)):
    expert = db.scalar(select(User).where(User.id == body.expert_id, User.role == "expert"))
    if not expert:
        raise HTTPException(404, "专家不存在")
    profile = db.get(ExpertProfile, expert.id)
    client_count = db.scalar(select(func.count()).select_from(ExpertAssignment).where(
        ExpertAssignment.expert_id == expert.id, ExpertAssignment.status == "active"
    ))
    if profile and (not profile.accepting_clients or client_count >= profile.max_clients):
        raise HTTPException(409, "该专家目前暂停接收新客户")
    assignment = db.get(ExpertAssignment, user.id)
    if assignment:
        assignment.expert_id = expert.id
        assignment.status = "active"
        assignment.created_at = datetime.now(timezone.utc)
        assignment.ended_at = None
    else:
        db.add(ExpertAssignment(user_id=user.id, expert_id=expert.id))
    db.add(AuditLog(
        user_id=user.id, action="expert.selected", resource_type="expert_assignment",
        resource_id=expert.id, details={},
    ))
    db.commit()
    return {"expert_id": expert.id, "name": expert.username}


@app.delete("/api/v1/experts/selection", status_code=204)
def release_expert(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if assignment and assignment.status == "active":
        assignment.status = "ended"
        assignment.ended_at = datetime.now(timezone.utc)
        db.add(AuditLog(
            user_id=user.id, action="expert.released", resource_type="expert_assignment",
            resource_id=assignment.expert_id, details={},
        ))
        db.commit()


@app.get("/api/v1/expert/profile")
def get_expert_profile(expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    profile = db.get(ExpertProfile, expert.id)
    return {
        "display_name": profile.display_name if profile else expert.username,
        "title": profile.title if profile else "家庭支持专家",
        "specialties": profile.specialties if profile else [],
        "bio": profile.bio if profile else "",
        "credentials": profile.credentials if profile else "",
        "avatar_url": profile.avatar_url if profile else None,
        "accepting_clients": profile.accepting_clients if profile else True,
        "max_clients": profile.max_clients if profile else 30,
    }


@app.put("/api/v1/expert/profile")
def update_expert_profile(body: ExpertProfileIn, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    profile = db.get(ExpertProfile, expert.id)
    if profile:
        for key, value in body.model_dump().items():
            setattr(profile, key, value)
    else:
        profile = ExpertProfile(user_id=expert.id, **body.model_dump())
        db.add(profile)
    db.add(AuditLog(
        user_id=expert.id, action="expert.profile_updated", resource_type="expert_profile",
        resource_id=expert.id, details={"accepting_clients": body.accepting_clients},
    ))
    db.commit()
    return get_expert_profile(expert, db)


@app.post("/api/v1/expert/profile/avatar")
async def upload_expert_avatar(
    avatar: UploadFile = File(...), expert: User = Depends(expert_user), db: Session = Depends(get_db),
):
    if avatar.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "仅支持 JPG、PNG 或 WebP 图片")
    content = await avatar.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 5MB")
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "图片文件无效")
    image = image.convert("RGB")
    edge = min(image.size)
    left = (image.width - edge) // 2
    top = (image.height - edge) // 2
    image = image.crop((left, top, left + edge, top + edge))
    image.thumbnail((640, 640))
    avatar_dir = upload_root / "expert_avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    target = avatar_dir / f"{expert.id}.webp"
    image.save(target, "WEBP", quality=88, method=6)
    profile = db.get(ExpertProfile, expert.id)
    avatar_url = f"/api/v1/expert-avatars/{expert.id}"
    if profile:
        profile.avatar_url = avatar_url
    else:
        db.add(ExpertProfile(user_id=expert.id, display_name=expert.username, avatar_url=avatar_url))
    db.add(AuditLog(
        user_id=expert.id, action="expert.avatar_updated", resource_type="expert_profile",
        resource_id=expert.id, details={"content_type": "image/webp"},
    ))
    db.commit()
    return {"avatar_url": avatar_url}


@app.get("/api/v1/expert-avatars/{expert_id}", include_in_schema=False)
def expert_avatar(expert_id: str, db: Session = Depends(get_db)):
    expert = db.scalar(select(User).where(User.id == expert_id, User.role == "expert", User.is_active.is_(True)))
    target = upload_root / "expert_avatars" / f"{expert_id}.webp"
    if not expert or not target.is_file():
        raise HTTPException(404, "专家头像不存在")
    return FileResponse(target, media_type="image/webp", headers={"Cache-Control": "public, max-age=3600"})


@app.post("/api/v1/expert/questions", status_code=201)
def ask_expert(body: ExpertQuestion, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if not assignment or assignment.status != "active":
        raise HTTPException(409, "请先选择专家")
    message = ExpertMessage(client_id=user.id, expert_id=assignment.expert_id, sender_id=user.id, content=body.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "created_at": message.created_at}


@app.get("/api/v1/expert/conversation")
def client_expert_conversation(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if not assignment or assignment.status != "active":
        return {"items": []}
    rows = db.scalars(select(ExpertMessage).where(
        ExpertMessage.client_id == user.id, ExpertMessage.expert_id == assignment.expert_id
    ).order_by(ExpertMessage.created_at)).all()
    for item in rows:
        if item.sender_id == assignment.expert_id and not item.read_at:
            item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"items": [{"id": item.id, "sender": "client" if item.sender_id == user.id else "expert", "content": item.content, "created_at": item.created_at} for item in rows]}


@app.get("/api/v1/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    expert_unread = 0
    if assignment and assignment.status == "active":
        expert_unread = db.scalar(select(func.count()).select_from(ExpertMessage).where(
            ExpertMessage.client_id == user.id, ExpertMessage.expert_id == assignment.expert_id,
            ExpertMessage.sender_id == assignment.expert_id, ExpertMessage.read_at.is_(None),
        ))
    return {"expert_unread": expert_unread}


@app.get("/api/v1/expert/clients")
def expert_clients(expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignments = db.scalars(select(ExpertAssignment).where(
        ExpertAssignment.expert_id == expert.id, ExpertAssignment.status == "active"
    )).all()
    items = []
    for assignment in assignments:
        client = db.get(User, assignment.user_id)
        unread = db.scalar(select(func.count()).select_from(ExpertMessage).where(
            ExpertMessage.client_id == client.id, ExpertMessage.expert_id == expert.id,
            ExpertMessage.sender_id == client.id, ExpertMessage.read_at.is_(None),
        ))
        latest = db.scalar(select(ExpertMessage).where(
            ExpertMessage.client_id == client.id, ExpertMessage.expert_id == expert.id
        ).order_by(ExpertMessage.created_at.desc()))
        items.append({"id": client.id, "name": client.username, "unread": unread, "latest": latest.content if latest else None})
    return {"items": items}


@app.get("/api/v1/expert/clients/{client_id}/messages")
def expert_client_messages(client_id: str, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户不存在")
    rows = db.scalars(select(ExpertMessage).where(
        ExpertMessage.client_id == client_id, ExpertMessage.expert_id == expert.id
    ).order_by(ExpertMessage.created_at)).all()
    for item in rows:
        if item.sender_id == client_id and not item.read_at:
            item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"items": [{"id": item.id, "sender": "expert" if item.sender_id == expert.id else "client", "content": item.content, "created_at": item.created_at} for item in rows]}


@app.post("/api/v1/expert/clients/{client_id}/reply", status_code=201)
def reply_to_client(client_id: str, body: ExpertReply, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户不存在")
    message = ExpertMessage(client_id=client_id, expert_id=expert.id, sender_id=expert.id, content=body.content)
    db.add(message)
    db.commit()
    return {"id": message.id}


@app.post("/api/v1/expert/clients/{client_id}/close")
def close_expert_consultation(client_id: str, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户咨询不存在")
    assignment.status = "ended"
    assignment.ended_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        user_id=expert.id, action="expert.consultation_closed", resource_type="expert_assignment",
        resource_id=client_id, details={},
    ))
    db.commit()
    return {"closed": True}
