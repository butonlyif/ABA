from datetime import date, datetime, timedelta, timezone
from html import escape

import fitz
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from platform_shared.app import create_app
from platform_shared.database import get_db
from platform_shared.deps import add_ai_usage
from platform_shared.models import ChatMessage, User
from platform_shared.schemas import ChatAnswer, ChatOut, ChatRequest
from platform_shared.security import current_user

from app.models import CoachGrowthState, GrowthProgress, JournalEntry, MoodEntry
from app.schemas import (
    CoachGrowthStateIn,
    CoachGrowthStateOut,
    JournalIn,
    JournalOut,
    MoodIn,
    MoodOut,
    WeeklyReportExport,
)
from app.services.ai import generate
from app.services.coach_content import articles, search, article, related, categories
from app.services.coach_weekly import generate_weekly_summary
from app.services.context_builder import build_coach_context

coach_router = APIRouter(prefix="/api/v1")


# ====================================
# 共享聊天路由（product 默认 coach）
# ====================================

@coach_router.get("/chat/messages", response_model=list[ChatOut])
def chat_messages(product: str = "coach", user: User = Depends(current_user), db: Session = Depends(get_db)):
    if product not in {"aba", "coach"}:
        raise HTTPException(400, "未知产品")
    rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == product
    ).order_by(ChatMessage.created_at.desc()).limit(50)).all()
    return rows[::-1]


@coach_router.delete("/chat/messages")
def clear_chat_messages(product: str = "coach", user: User = Depends(current_user), db: Session = Depends(get_db)):
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


# ====================================
# Coach 路由
# ====================================

@coach_router.get("/coach/overview")
def coach_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today_mood = db.scalar(select(MoodEntry).where(MoodEntry.user_id == user.id).order_by(MoodEntry.entry_date.desc()))
    journal_count = db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.user_id == user.id))
    return {"mood_today": today_mood.mood if today_mood else None, "journal_count": journal_count, "growth_stage": "接纳", "message": "今天也给自己留一点空间。"}


@coach_router.get("/coach/moods", response_model=list[MoodOut])
def list_moods(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(MoodEntry).where(MoodEntry.user_id == user.id).order_by(MoodEntry.entry_date.desc()).limit(30)).all()


@coach_router.post("/coach/moods", response_model=MoodOut)
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


@coach_router.get("/coach/journals", response_model=list[JournalOut])
def list_journals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id).order_by(JournalEntry.created_at.desc()).limit(50)).all()


@coach_router.post("/coach/journals", response_model=JournalOut, status_code=201)
def save_journal(body: JournalIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = JournalEntry(user_id=user.id, **body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@coach_router.get("/coach/growth-sessions", response_model=CoachGrowthStateOut)
def get_growth_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    state = db.get(CoachGrowthState, user.id)
    if state:
        return state
    return CoachGrowthStateOut(sessions=[], updated_at=datetime.utcnow())


@coach_router.put("/coach/growth-sessions", response_model=CoachGrowthStateOut)
def save_growth_sessions(body: CoachGrowthStateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    state = db.get(CoachGrowthState, user.id)
    if state:
        state.sessions = body.sessions
        state.updated_at = datetime.utcnow()
    else:
        state = CoachGrowthState(user_id=user.id, sessions=body.sessions)
        db.add(state)
    db.commit()
    db.refresh(state)
    return state


@coach_router.get("/coach/growth")
def growth(user: User = Depends(current_user), db: Session = Depends(get_db)):
    saved = {item.stage: item.status for item in db.scalars(select(GrowthProgress).where(GrowthProgress.user_id == user.id))}
    return {"stages": [{"stage": stage, "status": saved.get(stage, "completed" if stage == 1 else "active" if stage == 2 else "locked")} for stage in range(1, 6)]}


@coach_router.post("/coach/weekly-report")
def coach_weekly_report(week_offset: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """生成人生教练 AI 周报。week_offset: 0=本周，-1=上周。"""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    next_monday = monday + timedelta(days=7)
    moods = db.scalars(select(MoodEntry).where(
        MoodEntry.user_id == user.id, MoodEntry.entry_date >= monday, MoodEntry.entry_date < next_monday,
    ).order_by(MoodEntry.entry_date)).all()
    journals = db.scalars(select(JournalEntry).where(
        JournalEntry.user_id == user.id, JournalEntry.created_at >= datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc),
        JournalEntry.created_at < datetime(next_monday.year, next_monday.month, next_monday.day, tzinfo=timezone.utc),
    ).order_by(JournalEntry.created_at)).all()
    chat_count = db.scalar(select(func.count()).select_from(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == "coach", ChatMessage.role == "user",
        ChatMessage.created_at >= datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc),
        ChatMessage.created_at < datetime(next_monday.year, next_monday.month, next_monday.day, tzinfo=timezone.utc),
    )) or 0
    content, ai_call = generate_weekly_summary(moods, journals, chat_count, week_offset)
    add_ai_usage(db, user, "coach_weekly", ai_call)
    db.commit()
    return {
        "week_start": monday.isoformat(),
        "week_end": (monday + timedelta(days=6)).isoformat(),
        "mood_count": len(moods),
        "journal_count": len(journals),
        "chat_count": chat_count,
        "content": content,
        "provider": ai_call.provider,
        "fallback": ai_call.fallback,
    }


@coach_router.post("/coach/weekly-report/export")
def export_coach_weekly_report(body: WeeklyReportExport, user: User = Depends(current_user)):
    paragraphs = "".join(f"<p>{escape(line)}</p>" for line in body.content.splitlines() if line.strip())
    html = f"""
    <h1>家长陪伴周报</h1>
    <p class="period">{escape(body.week_start)} 至 {escape(body.week_end)}</p>
    <table>
      <tr><td>情绪记录</td><td>{body.mood_count} 条</td></tr>
      <tr><td>日记记录</td><td>{body.journal_count} 条</td></tr>
      <tr><td>陪伴对话</td><td>{body.chat_count} 次</td></tr>
    </table>
    <h2>本周回顾</h2>
    {paragraphs}
    <p class="note">本报告用于个人回顾，不替代专业医疗或心理服务。</p>
    """
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_htmlbox(
        fitz.Rect(48, 46, 547, 796),
        html,
        css="body{font-family:sans-serif;color:#3f382f;font-size:11pt;line-height:1.65}"
            "h1{color:#725b42;font-size:23pt;margin-bottom:4px}"
            "h2{color:#725b42;font-size:15pt;margin-top:22px}"
            ".period{color:#817568;margin-top:0}"
            "table{border-collapse:collapse;width:100%;margin:18px 0}"
            "td{border:1px solid #ded5c9;padding:8px}"
            ".note{color:#91887f;font-size:8pt;margin-top:28px}",
    )
    content = document.tobytes(garbage=4, deflate=True)
    document.close()
    filename = f"coach-weekly-{body.week_start}.pdf"
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@coach_router.get("/coach/articles")
def list_coach_articles(q: str | None = None, user: User = Depends(current_user)):
    if q:
        return {"items": search(q)}
    return {"items": articles()}


@coach_router.get("/coach/categories")
def list_coach_categories(user: User = Depends(current_user)):
    return {"items": categories()}


@coach_router.get("/coach/articles/{article_id}")
def get_coach_article(article_id: str, user: User = Depends(current_user)):
    item = article(article_id)
    if not item:
        raise HTTPException(404, "文章不存在")
    return {**item, "related": related(article_id)}


@coach_router.post("/coach/chat", response_model=ChatAnswer)
def coach_chat(body: ChatRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    history_rows = db.scalars(select(ChatMessage).where(
        ChatMessage.user_id == user.id, ChatMessage.product == "coach"
    ).order_by(ChatMessage.created_at.desc()).limit(10)).all()[::-1]
    recent_moods = db.scalars(select(MoodEntry).where(
        MoodEntry.user_id == user.id,
    ).order_by(MoodEntry.entry_date.desc()).limit(5)).all()
    recent_journals = db.scalars(select(JournalEntry).where(
        JournalEntry.user_id == user.id,
    ).order_by(JournalEntry.created_at.desc()).limit(3)).all()
    context = build_coach_context(recent_moods, recent_journals)
    answer, _, ai_call = generate("coach", body.message, [{"role": row.role, "content": row.content} for row in history_rows], context)
    db.add_all([
        ChatMessage(user_id=user.id, product="coach", role="user", content=body.message),
        ChatMessage(user_id=user.id, product="coach", role="assistant", content=answer),
    ])
    add_ai_usage(db, user, "coach", ai_call)
    db.commit()
    return ChatAnswer(answer=answer)


app = create_app("Coach Family API", extra_routers=[coach_router])


@app.get("/", include_in_schema=False)
def open_mobile_web():
    """Developer convenience: opening the API port leads to the PWA."""
    return RedirectResponse("http://localhost:5174/")
