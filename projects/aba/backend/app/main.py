import asyncio
import io
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from platform_shared.app import create_app
from platform_shared.config import get_settings
from platform_shared.database import SessionLocal, get_db
from platform_shared.models import AuditLog, ChatMessage, ExpertAssignment, RefreshToken, SystemEvent, AiUsage, User
from platform_shared.security import current_user, hash_password
from platform_shared.deps import admin_user, add_ai_usage
from platform_shared.safety import crisis_response
from platform_shared.services.rate_limit import limiter
from platform_shared.services.storage import get_storage
from platform_shared.schemas import AdminPasswordReset, AdminUserCreate, ChatAnswer, ChatOut, ChatRequest

from app.models import Assessment, Child, ChildRecordFile, Report, Task, TrainingSession, Trial
from app.schemas import (
    AssessmentOut, AssessmentSubmit, BootstrapOut, ChildIn, ChildOut, ChildRecordFileOut,
    ReorderBody, ReportOut, ReportRequest, SessionIn, SessionOut, TaskIn, TaskOut, TaskPatch, TrialIn,
)
from app.services.assessment import questions as real_assessment_questions, score_and_tasks, skill_catalog
from app.services.ai import analyze_medical_record, generate
from app.services.flashcards import card as flashcard_image, catalog as flashcard_catalog
from app.services.jobs import enqueue_report
from app.services.context_builder import build_aba_context
from app.services.avatar import avatar_url_for, generate_avatar_svg
from app.services.retention import purge_expired_customer_data

settings = get_settings()
upload_root = Path(settings.upload_path)
MIN_TRIALS_PER_SESSION = 5
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024

aba_router = APIRouter(prefix="/api/v1")


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


@aba_router.get("/bootstrap", response_model=BootstrapOut)
def bootstrap(user: User = Depends(current_user), db: Session = Depends(get_db)):
    children = []
    if user.role not in {"expert", "admin"}:
        children = db.scalars(
            select(Child).where(Child.user_id == user.id).order_by(Child.created_at)
        ).all()
    return BootstrapOut(user=user, children=children)


@aba_router.get("/children", response_model=list[ChildOut])
def list_children(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Child).where(Child.user_id == user.id).order_by(Child.created_at)).all()


@aba_router.post("/children", response_model=ChildOut, status_code=201)
def create_child(body: ChildIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    has_child = db.scalar(select(func.count()).select_from(Child).where(Child.user_id == user.id))
    child = Child(user_id=user.id, is_current=not bool(has_child), **body.model_dump())
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@aba_router.post("/children/{child_id}/import-record", response_model=ChildOut)
async def import_medical_record(child_id: str, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """上传病例文件（txt/md/pdf），AI 分析后更新孩子状态快照。"""
    child = owned_child(db, user, child_id)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text", "")
    else:
        raw = await request.body()
        text = raw.decode("utf-8", errors="ignore")
    if not text.strip():
        raise HTTPException(400, "病例内容为空")
    snapshot, summary = analyze_medical_record(text)
    if snapshot:
        snapshot["updated_at"] = datetime.utcnow().isoformat()
        child.status_snapshot = snapshot
        db.commit()
        db.refresh(child)
    return child


@aba_router.post("/children/{child_id}/upload-record", response_model=ChildOut)
async def upload_medical_record(child_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """上传病例文件（txt/md/pdf），AI 分析后更新孩子状态快照。"""
    child = owned_child(db, user, child_id)
    raw = await file.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "文件不能超过 20MB")
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        import fitz
        doc = fitz.open(stream=raw, filetype="pdf")
        text = "".join(page.get_text() for page in doc)
    elif ext in ("doc", "docx"):
        import zipfile, re
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", "", xml)
        except Exception:
            text = raw.decode("utf-8", errors="ignore")
    else:
        text = raw.decode("utf-8", errors="ignore")
    if not text.strip():
        raise HTTPException(400, "无法从文件中提取文本")
    snapshot, summary = analyze_medical_record(text)
    suffix = f".{ext}" if ext else ""
    file_key = f"medical_records/{user.id}/{child.id}/{uuid4()}{suffix}"
    storage = get_storage()
    storage.put(file_key, raw, file.content_type or "application/octet-stream")
    record_file = ChildRecordFile(
        user_id=user.id,
        child_id=child.id,
        original_name=(filename or "未命名文件")[:255],
        file_key=file_key,
        content_type=(file.content_type or "application/octet-stream")[:120],
        size_bytes=len(raw),
    )
    try:
        db.add(record_file)
        if snapshot:
            snapshot["updated_at"] = datetime.utcnow().isoformat()
            child.status_snapshot = snapshot
        db.commit()
        db.refresh(child)
    except Exception:
        db.rollback()
        storage.delete(file_key)
        raise
    return child


@aba_router.get("/children/{child_id}/record-files", response_model=list[ChildRecordFileOut])
def list_child_record_files(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    return db.scalars(
        select(ChildRecordFile).where(
            ChildRecordFile.child_id == child_id,
            ChildRecordFile.user_id == user.id,
        ).order_by(ChildRecordFile.created_at.desc())
    ).all()


@aba_router.get("/children/{child_id}/record-files/{file_id}")
def download_child_record_file(
    child_id: str,
    file_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_child(db, user, child_id)
    record_file = db.scalar(select(ChildRecordFile).where(
        ChildRecordFile.id == file_id,
        ChildRecordFile.child_id == child_id,
        ChildRecordFile.user_id == user.id,
    ))
    if not record_file:
        raise HTTPException(404, "原始文件不存在")
    content, stored_type = get_storage().get(record_file.file_key)
    encoded_name = quote(record_file.original_name)
    return Response(
        content=content,
        media_type=record_file.content_type or stored_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@aba_router.delete("/children/{child_id}/record-files/{file_id}", status_code=204)
def delete_child_record_file(
    child_id: str,
    file_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    child = owned_child(db, user, child_id)
    record_file = db.scalar(select(ChildRecordFile).where(
        ChildRecordFile.id == file_id,
        ChildRecordFile.child_id == child.id,
        ChildRecordFile.user_id == user.id,
    ))
    if not record_file:
        raise HTTPException(404, "原始文件不存在")
    get_storage().delete(record_file.file_key)
    db.delete(record_file)
    db.add(AuditLog(
        user_id=user.id,
        action="child.record_file_deleted",
        resource_type="child_record_file",
        resource_id=record_file.id,
        details={"child_id": child.id, "original_name": record_file.original_name},
    ))
    db.commit()
    return Response(status_code=204)


@aba_router.patch("/children/{child_id}/current", response_model=ChildOut)
def set_current_child(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = owned_child(db, user, child_id)
    for row in db.scalars(select(Child).where(Child.user_id == user.id)):
        row.is_current = row.id == child.id
    db.commit()
    db.refresh(child)
    return child


# ─── 孩子头像 ──────────────────────────────────────────────

@aba_router.post("/children/{child_id}/avatar", response_model=ChildOut)
async def upload_child_avatar(
    child_id: str,
    avatar: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """上传孩子头像（jpg/png/webp，≤ 5MB）"""
    child = owned_child(db, user, child_id)
    if avatar.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, "仅支持 JPG、PNG 或 WebP 图片")
    content = await avatar.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(413, "图片不能超过 5MB")
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "无法识别该图片")
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    avatar_dir = upload_root / "child_avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    target = avatar_dir / f"{child.id}.webp"
    image.save(target, "WEBP", quality=88, method=6)
    child.avatar_url = avatar_url_for(child.id, child.avatar_seed)
    if not child.avatar_seed:
        child.avatar_seed = (child.name or "星")[:80]
    db.add(AuditLog(
        user_id=user.id, action="child.avatar_uploaded",
        resource_type="child", resource_id=child.id,
        details={"content_type": "image/webp"},
    ))
    db.commit()
    db.refresh(child)
    return child


@aba_router.delete("/children/{child_id}/avatar", response_model=ChildOut)
def remove_child_avatar(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """移除孩子头像（之后回退到自动生成卡通）"""
    child = owned_child(db, user, child_id)
    target = upload_root / "child_avatars" / f"{child.id}.webp"
    target.unlink(missing_ok=True)
    child.avatar_url = None
    if not child.avatar_seed:
        child.avatar_seed = (child.name or "星")[:80]
    db.add(AuditLog(
        user_id=user.id, action="child.avatar_removed",
        resource_type="child", resource_id=child.id, details={},
    ))
    db.commit()
    db.refresh(child)
    return child


@aba_router.post("/children/{child_id}/avatar/regenerate", response_model=ChildOut)
def regenerate_child_avatar(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """基于 seed 自动生成卡通头像（清空已上传文件，用 SVG 兜底）"""
    child = owned_child(db, user, child_id)
    if not child.avatar_seed:
        child.avatar_seed = (child.name or "星")[:80]
    target = upload_root / "child_avatars" / f"{child.id}.webp"
    target.unlink(missing_ok=True)
    child.avatar_url = avatar_url_for(child.id, child.avatar_seed)
    db.add(AuditLog(
        user_id=user.id, action="child.avatar_regenerated",
        resource_type="child", resource_id=child.id,
        details={"seed": child.avatar_seed},
    ))
    db.commit()
    db.refresh(child)
    return child


@aba_router.get("/child-avatars/{child_id}", include_in_schema=False)
def child_avatar(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """头像静态读取：优先返回已上传 webp；缺失走卡通 SVG。"""
    child = owned_child(db, user, child_id)
    target = upload_root / "child_avatars" / f"{child.id}.webp"
    if target.is_file():
        return FileResponse(target, media_type="image/webp", headers={"Cache-Control": "private, max-age=60"})
    seed = child.avatar_seed or child.id
    svg = generate_avatar_svg(seed or "星")
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "private, max-age=60"})


@aba_router.get("/assessments/questions")
def assessment_questions(user: User = Depends(current_user)):
    return {"items": real_assessment_questions()}


@aba_router.post("/assessments", response_model=AssessmentOut)
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
    # 更新孩子状态快照
    child_obj = owned_child(db, user, body.child_id)
    child_obj.status_snapshot = {
        "domains": dict(result["domain_scores"]),
        "domain_levels": dict(result["domain_levels"]),
        "overall_level": result["overall_level"],
        "updated_at": datetime.utcnow().isoformat(),
        "source": "assessment",
    }
    db.commit()
    db.refresh(assessment)
    return AssessmentOut(
        **AssessmentOut.model_validate(assessment).model_dump(exclude={"generated_task_ids"}),
        generated_task_ids=[task.id for task in generated],
    )


@aba_router.get("/training/templates")
def training_templates(user: User = Depends(current_user)):
    """训练技能模板库（按领域分组），供"添加训练"指引使用。"""
    return skill_catalog()


@aba_router.get("/tasks", response_model=list[TaskOut])
def list_tasks(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    return db.scalars(select(Task).where(Task.user_id == user.id, Task.child_id == child_id).order_by(Task.sort_order.asc(), Task.created_at.desc())).all()


@aba_router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, body.child_id)
    max_order = db.scalar(select(func.coalesce(func.max(Task.sort_order), -1)).where(Task.user_id == user.id, Task.child_id == body.child_id)) or -1
    task = Task(user_id=user.id, sort_order=max_order + 1, **body.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# 具体路径必须在 /{task_id} 之前，否则 "reorder" 会被匹配为 task_id
@aba_router.patch("/tasks/reorder", response_model=list[TaskOut])
def reorder_tasks(child_id: str, body: ReorderBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    for item in body.order:
        t = db.scalar(select(Task).where(Task.id == item["id"], Task.user_id == user.id))
        if t:
            t.sort_order = item["sort_order"]
    db.commit()
    return db.scalars(select(Task).where(Task.user_id == user.id, Task.child_id == child_id).order_by(Task.sort_order.asc())).all()


@aba_router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not task:
        raise HTTPException(404, "任务不存在")
    db.delete(task)
    db.commit()
    return None


@aba_router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not task:
        raise HTTPException(404, "任务不存在")
    if body.status is not None:
        task.status = body.status
    if body.sort_order is not None:
        task.sort_order = body.sort_order
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


def _independent_rate(sessions: list[TrainingSession]) -> int:
    values = [trial.result for session in sessions for trial in session.trials]
    return round(values.count("I") / len(values) * 100) if values else 0


def _progress_insights(sessions: list[TrainingSession]) -> dict:
    now = datetime.now(timezone.utc)
    today = now.date()
    current_monday = today - timedelta(days=today.weekday())
    weekly = []
    for weeks_ago in range(3, -1, -1):
        start = current_monday - timedelta(weeks=weeks_ago)
        end = start + timedelta(days=7)
        rows = [
            session for session in sessions
            if start <= session.created_at.date() < end
        ]
        values = [trial.result for session in rows for trial in session.trials]
        counts = {result: values.count(result) for result in ("I", "V", "M", "P", "E")}
        weekly.append({
            "week_start": start.isoformat(),
            "label": f"{start.month}/{start.day}",
            "sessions": len(rows),
            "trials": len(values),
            "independent_rate": round(counts["I"] / len(values) * 100) if values else None,
            "results": counts,
        })

    ordered = sorted(sessions, key=lambda row: row.created_at, reverse=True)
    recent, previous = ordered[:3], ordered[3:6]
    if len(recent) < 3 or len(previous) < 3:
        trend = {
            "status": "insufficient",
            "title": "继续记录，趋势会更清楚",
            "message": f"目前有 {len(ordered)} 次完整训练；每次至少记录 {MIN_TRIALS_PER_SESSION} 个回合，累计 6 次后可以比较趋势。",
            "delta": None,
            "recent_rate": _independent_rate(recent) if recent else None,
            "previous_rate": _independent_rate(previous) if previous else None,
            "evidence_sessions": len(ordered),
        }
    else:
        recent_rate = _independent_rate(recent)
        previous_rate = _independent_rate(previous)
        delta = recent_rate - previous_rate
        if delta >= 5:
            status, title = "progress", "独立完成正在进步"
        elif delta <= -5:
            status, title = "regression", "独立完成可能回退"
        else:
            status, title = "stable", "独立完成保持稳定"
        trend = {
            "status": status,
            "title": title,
            "message": f"最近 3 次训练独立率 {recent_rate}%，此前 3 次为 {previous_rate}%。",
            "delta": delta,
            "recent_rate": recent_rate,
            "previous_rate": previous_rate,
            "evidence_sessions": 6,
        }

    recent_cutoff = today - timedelta(days=28)
    previous_cutoff = today - timedelta(days=56)
    skill_names = sorted({session.skill_name for session in sessions if session.created_at.date() >= previous_cutoff})
    skills = []
    priority = {"regression": 0, "progress": 1, "stable": 2, "insufficient": 3}
    for skill_name in skill_names:
        current_rows = [
            row for row in sessions
            if row.skill_name == skill_name and row.created_at.date() >= recent_cutoff
        ]
        previous_rows = [
            row for row in sessions
            if row.skill_name == skill_name and previous_cutoff <= row.created_at.date() < recent_cutoff
        ]
        current_rate = _independent_rate(current_rows) if current_rows else None
        previous_rate = _independent_rate(previous_rows) if previous_rows else None
        delta = current_rate - previous_rate if current_rate is not None and previous_rate is not None else None
        if len(current_rows) < 2 or len(previous_rows) < 2:
            status = "insufficient"
        elif delta is not None and delta >= 5:
            status = "progress"
        elif delta is not None and delta <= -5:
            status = "regression"
        else:
            status = "stable"
        skills.append({
            "skill_name": skill_name,
            "current_rate": current_rate,
            "previous_rate": previous_rate,
            "delta": delta,
            "status": status,
            "current_sessions": len(current_rows),
            "previous_sessions": len(previous_rows),
        })
    skills.sort(key=lambda item: (priority[item["status"]], -(abs(item["delta"]) if item["delta"] is not None else 0)))
    return {"trend": trend, "weekly": weekly, "skills": skills}


@aba_router.get("/training-sessions/active", response_model=SessionOut | None)
def active_training_session(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == child_id,
        TrainingSession.status == "active",
    ).order_by(TrainingSession.created_at.desc()))
    return session_out(session) if session else None


@aba_router.post("/training-sessions", response_model=SessionOut, status_code=201)
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
        if active.task_id == body.task_id:
            return session_out(active)
        active.status = "completed"
        if not active.finished_at:
            active.finished_at = func.now()
        db.flush()
    session = TrainingSession(user_id=user.id, idempotency_key=idempotency_key, **body.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_out(session)


@aba_router.post("/training-sessions/{session_id}/trials", response_model=SessionOut)
def add_trial(session_id: str, body: TrialIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    if not session or session.status != "active":
        raise HTTPException(404, "训练会话不存在或已结束")
    db.add(Trial(session_id=session.id, result=body.result, sequence=len(session.trials) + 1))
    db.commit()
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    return session_out(session)


@aba_router.delete("/training-sessions/{session_id}/trials/latest", response_model=SessionOut)
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
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    return session_out(session)


@aba_router.post("/training-sessions/{session_id}/finish", response_model=SessionOut)
def finish_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.id == session_id, TrainingSession.user_id == user.id
    ))
    if not session:
        raise HTTPException(404, "训练会话不存在")
    if len(session.trials) < MIN_TRIALS_PER_SESSION:
        raise HTTPException(400, f"至少记录 {MIN_TRIALS_PER_SESSION} 个回合才能完成本次训练")
    session.status = "completed"
    session.finished_at = datetime.now(timezone.utc)
    if session.task_id:
        task = db.scalar(select(Task).where(Task.id == session.task_id, Task.user_id == user.id))
        if task and not task.is_daily:
            # 每日任务保持 active，普通任务完成后隐藏（不删除，报告仍使用）
            task.status = "completed"
    db.commit()
    return session_out(session)


@aba_router.get("/progress")
def progress(child_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_child(db, user, child_id)
    all_sessions = db.scalars(select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == child_id,
        TrainingSession.status == "completed",
    ).order_by(TrainingSession.created_at.desc())).all()
    sessions = [session for session in all_sessions if len(session.trials) >= MIN_TRIALS_PER_SESSION]
    items = [session_out(item) for item in sessions]
    insights = _progress_insights(sessions)
    return {
        "completed_sessions": len(items),
        "training_days": len({item.created_at.date().isoformat() for item in items}),
        "average_percentage": round(sum(item.percentage for item in items) / len(items)) if items else 0,
        "last_training_at": (items[0].finished_at or items[0].created_at).isoformat() if items else None,
        "timeline": items[:20],
        **insights,
    }


@aba_router.post("/reports", response_model=ReportOut, status_code=202)
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


@aba_router.get("/reports", response_model=list[ReportOut])
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


@aba_router.get("/reports/{report_id}/file")
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
    risk = crisis_response(message, "aba")
    if risk:
        return risk
    return "先记录行为发生前的情境、具体行为和随后结果（ABC）。从一次只调整一个变量开始，并强化孩子可以替代问题行为的沟通方式。"


@aba_router.post("/chat/stream")
async def chat_stream(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = owned_child(db, user, body.child_id) if body.child_id else None
    history = [
        {"role": item.role, "content": item.content}
        for item in db.scalars(select(ChatMessage).where(
            ChatMessage.user_id == user.id, ChatMessage.product == "aba"
        ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    ]
    recent_sessions = db.scalars(select(TrainingSession).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == body.child_id,
        TrainingSession.status == "completed",
    ).order_by(TrainingSession.created_at.desc()).limit(5)).all() if child else []
    context = build_aba_context(child, recent_sessions)
    answer, sources, ai_call = generate("aba", body.message, history, context)
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


@aba_router.post("/chat/public")
def public_chat(body: ChatRequest, request: Request):
    limiter.check(request, "public-chat", settings.public_chat_rate_limit, 60)
    return {"answer": safe_answer(body.message), "anonymous": True}


@aba_router.post("/chat", response_model=ChatAnswer)
def chat(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = owned_child(db, user, body.child_id) if body.child_id else None
    history_rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == "aba"
    ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    recent_sessions = db.scalars(select(TrainingSession).where(
        TrainingSession.user_id == user.id, TrainingSession.child_id == body.child_id,
        TrainingSession.status == "completed",
    ).order_by(TrainingSession.created_at.desc()).limit(5)).all() if child else []
    context = build_aba_context(child, recent_sessions)
    answer, sources, ai_call = generate("aba", body.message, [{"role": row.role, "content": row.content} for row in history_rows], context)
    db.add_all([
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="user", content=body.message),
        ChatMessage(user_id=user.id, product="aba", child_id=body.child_id, role="assistant", content=answer, sources=sources),
    ])
    add_ai_usage(db, user, "aba", ai_call)
    db.commit()
    return ChatAnswer(answer=answer, sources=[{"title": item["title"]} for item in sources])


@aba_router.get("/chat/messages", response_model=list[ChatOut])
def chat_messages(product: str = "aba", user: User = Depends(current_user), db: Session = Depends(get_db)):
    if product not in {"aba", "coach"}:
        raise HTTPException(400, "未知产品")
    rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == product
    ).order_by(ChatMessage.created_at.desc()).limit(50)).all()
    return rows[::-1]


@aba_router.delete("/chat/messages")
def clear_chat_messages(product: str = "aba", user: User = Depends(current_user), db: Session = Depends(get_db)):
    """清空指定产品的聊天历史（软删除：直接物理删除聊天记录）。"""
    if product not in {"aba", "coach"}:
        raise HTTPException(400, "未知产品")
    rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == product
    )).all()
    for row in rows:
        db.delete(row)
    db.commit()
    return {"deleted": len(rows)}


@aba_router.get("/flashcards")
def flashcards(user: User = Depends(current_user)):
    return {"groups": flashcard_catalog()}


@aba_router.get("/flashcards/{category}/{index}")
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
    return Response(data, media_type=media_type, headers={"X-Card-Label": quote(label, safe="")})


@aba_router.get("/admin/overview")
def admin_overview(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.scalar(select(func.count()).select_from(User)),
        "children": db.scalar(select(func.count()).select_from(Child)),
        "training_sessions": db.scalar(select(func.count()).select_from(TrainingSession)),
        "reports": db.scalar(select(func.count()).select_from(Report)),
    }


@aba_router.get("/admin/users")
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


@aba_router.post("/admin/users", status_code=201)
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


@aba_router.patch("/admin/users/{user_id}/role")
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


@aba_router.get("/admin/users/{user_id}")
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


@aba_router.patch("/admin/users/{user_id}/status")
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


@aba_router.patch("/admin/users/{user_id}/password")
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


@aba_router.get("/admin/audit-logs")
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


@aba_router.get("/admin/operations")
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


@aba_router.post("/admin/reports/{report_id}/retry", status_code=202)
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


@asynccontextmanager
async def aba_lifespan(_: FastAPI):
    stop_retention = asyncio.Event()

    async def retention_loop():
        while not stop_retention.is_set():
            def run_cleanup():
                cleanup_db = SessionLocal()
                try:
                    purge_expired_customer_data(cleanup_db)
                finally:
                    cleanup_db.close()

            try:
                await asyncio.to_thread(run_cleanup)
            except Exception:
                # A transient database/storage failure is retried on the next cycle.
                pass
            try:
                await asyncio.wait_for(stop_retention.wait(), timeout=24 * 60 * 60)
            except asyncio.TimeoutError:
                continue

    retention_task = asyncio.create_task(retention_loop())
    try:
        yield
    finally:
        stop_retention.set()
        await retention_task


app = create_app("ABA Family API", extra_routers=[aba_router], lifespan_extra=aba_lifespan)


@app.get("/", include_in_schema=False)
def open_mobile_web():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("http://localhost:5173/")
