from html import escape

import fitz
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..database import SessionLocal
from ..models import Child, Report, SystemEvent, Task, TrainingSession
from .storage import get_storage


def _percentage(session: TrainingSession) -> int:
    values = [trial.result for trial in session.trials]
    return round(values.count("I") / len(values) * 100) if values else 0


def _pdf(title: str, summary: str, content: dict) -> bytes:
    steps = "".join(f"<li>{escape(step)}</li>" for step in content["next_steps"])
    html = f"""
    <h1>{escape(title)}</h1>
    <p style="color:#6c5b7b">ABA 家庭训练进展报告</p>
    <h2>训练概览</h2><p>{escape(summary)}</p>
    <table>
      <tr><td>训练次数</td><td>{content["training"]["sessions"]}</td></tr>
      <tr><td>训练天数</td><td>{content["training"]["days"]}</td></tr>
      <tr><td>平均独立正确率</td><td>{content["training"]["average_percentage"]}%</td></tr>
      <tr><td>任务完成</td><td>{content["tasks"]["completed"]}/{content["tasks"]["total"]}</td></tr>
    </table>
    <h2>下一步建议</h2><ul>{steps}</ul>
    """
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_htmlbox(
        fitz.Rect(50, 50, 545, 792),
        html,
        css="body{font-family:sans-serif;color:#332d38;font-size:12pt;line-height:1.6}"
            "h1{color:#6c5b7b;font-size:24pt}h2{margin-top:22px;color:#527a70}"
            "table{border-collapse:collapse;width:100%}td{border:1px solid #ddd;padding:9px}",
    )
    result = document.tobytes(garbage=4, deflate=True)
    document.close()
    return result


def complete_report(report_id: str) -> None:
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if not report or report.status == "completed":
            return
        child = db.get(Child, report.child_id)
        sessions = db.scalars(
            select(TrainingSession).options(selectinload(TrainingSession.trials)).where(
                TrainingSession.user_id == report.user_id,
                TrainingSession.child_id == report.child_id,
                TrainingSession.status == "completed",
            ).order_by(TrainingSession.created_at.desc())
        ).all()
        percentages = [_percentage(item) for item in sessions]
        average = round(sum(percentages) / len(percentages)) if percentages else 0
        training_days = len({item.created_at.date().isoformat() for item in sessions})
        task_total = db.scalar(select(func.count()).select_from(Task).where(
            Task.user_id == report.user_id, Task.child_id == report.child_id
        )) or 0
        task_done = db.scalar(select(func.count()).select_from(Task).where(
            Task.user_id == report.user_id, Task.child_id == report.child_id, Task.status == "completed"
        )) or 0
        report.summary = f"共完成 {len(sessions)} 次训练，覆盖 {training_days} 天，平均独立正确率 {average}%。"
        report.content = {
            "overview": report.summary,
            "training": {"sessions": len(sessions), "days": training_days, "average_percentage": average},
            "tasks": {"total": task_total, "completed": task_done},
            "strengths": ["能够持续完成家庭训练"] if sessions else ["已建立训练计划"],
            "next_steps": ["保持短时高频训练", "根据提示等级逐步撤除辅助", "每周复盘一次趋势"],
        }
        report.file_key = f"reports/{report.user_id}/{report.id}.pdf"
        get_storage().put(report.file_key, _pdf(report.title, report.summary, report.content), "application/pdf")
        report.status = "completed"
        db.commit()
    except Exception as exc:
        db.rollback()
        report = db.get(Report, report_id)
        if report:
            report.status = "failed"
            report.summary = f"生成失败：{type(exc).__name__}"
            db.add(SystemEvent(
                level="error", category="report", message="报告生成失败",
                details={"report_id": report_id, "error_type": type(exc).__name__},
            ))
            db.commit()
        raise
    finally:
        db.close()
