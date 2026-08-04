from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Assessment,
    ChatMessage,
    CoachGrowthState,
    ExpertMessage,
    GrowthProgress,
    JournalEntry,
    MoodEntry,
    Report,
    TrainingSession,
)
from .storage import get_storage


RETENTION_DAYS = 30


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _session_timestamp(session: dict) -> datetime | None:
    candidates = [
        (session.get("resolution") or {}).get("updatedAt"),
        session.get("updatedAt"),
        session.get("createdAt"),
    ]
    for value in candidates:
        if not isinstance(value, str):
            continue
        try:
            return _naive_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            continue
    return None


def purge_expired_customer_data(
    db: Session,
    *,
    now: datetime | None = None,
    storage=None,
) -> dict[str, int]:
    """Permanently remove customer process data older than 30 days.

    Account data, child profiles, task definitions, and original child record files
    are deliberately not part of this cleanup.
    """
    cutoff = _naive_utc(now or datetime.utcnow()) - timedelta(days=RETENTION_DAYS)
    counts: dict[str, int] = {}

    for model, timestamp_name in (
        (Assessment, "submitted_at"),
        (TrainingSession, "created_at"),
        (ChatMessage, "created_at"),
        (MoodEntry, "created_at"),
        (JournalEntry, "created_at"),
        (ExpertMessage, "created_at"),
        (GrowthProgress, "updated_at"),
    ):
        rows = db.scalars(select(model).where(getattr(model, timestamp_name) < cutoff)).all()
        counts[model.__tablename__] = len(rows)
        for row in rows:
            db.delete(row)

    report_storage = storage or get_storage()
    expired_reports = db.scalars(select(Report).where(Report.created_at < cutoff)).all()
    deleted_reports = 0
    for report in expired_reports:
        if report.file_key:
            try:
                report_storage.delete(report.file_key)
            except Exception:
                # Keep the database row so the next daily run can retry the file.
                continue
        db.delete(report)
        deleted_reports += 1
    counts[Report.__tablename__] = deleted_reports

    pruned_sessions = 0
    for state in db.scalars(select(CoachGrowthState)).all():
        retained = []
        for session in state.sessions or []:
            timestamp = _session_timestamp(session)
            if timestamp is not None and timestamp < cutoff:
                pruned_sessions += 1
            else:
                retained.append(session)
        if len(retained) != len(state.sessions or []):
            state.sessions = retained
            state.updated_at = datetime.utcnow()
    counts["coach_growth_sessions"] = pruned_sessions

    db.commit()
    return counts
