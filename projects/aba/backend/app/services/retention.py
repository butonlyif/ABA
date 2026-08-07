from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_shared.models import ChatMessage
from platform_shared.services.storage import get_storage
from app.models import Assessment, Report, TrainingSession


RETENTION_DAYS = 30


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def purge_expired_customer_data(
    db: Session,
    *,
    now: datetime | None = None,
    storage=None,
) -> dict[str, int]:
    """Permanently remove ABA customer process data older than 30 days.

    Account data, child profiles, task definitions, and original child record files
    are deliberately not part of this cleanup.
    """
    cutoff = _naive_utc(now or datetime.utcnow()) - timedelta(days=RETENTION_DAYS)
    counts: dict[str, int] = {}

    for model, timestamp_name in (
        (Assessment, "submitted_at"),
        (TrainingSession, "created_at"),
    ):
        rows = db.scalars(select(model).where(getattr(model, timestamp_name) < cutoff)).all()
        counts[model.__tablename__] = len(rows)
        for row in rows:
            db.delete(row)

    aba_chats = db.scalars(select(ChatMessage).where(
        ChatMessage.created_at < cutoff, ChatMessage.product == "aba"
    )).all()
    counts[ChatMessage.__tablename__] = len(aba_chats)
    for row in aba_chats:
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

    db.commit()
    return counts
