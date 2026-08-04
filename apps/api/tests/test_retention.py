from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Assessment,
    ChatMessage,
    Child,
    ChildRecordFile,
    CoachGrowthState,
    JournalEntry,
    MoodEntry,
    Report,
    Task,
    TrainingSession,
    User,
)
from app.security import hash_password
from app.services.retention import purge_expired_customer_data


class MemoryStorage:
    def __init__(self):
        self.items = {}
        self.deleted = []

    def put(self, key, data, content_type):
        self.items[key] = (data, content_type)

    def get(self, key):
        return self.items[key]

    def delete(self, key):
        self.deleted.append(key)
        self.items.pop(key, None)


def test_retention_removes_only_expired_process_data():
    now = datetime(2026, 7, 26, 12, 0, 0)
    old = now - timedelta(days=31)
    recent = now - timedelta(days=29)
    storage = MemoryStorage()
    storage.put("reports/old.pdf", b"old", "application/pdf")

    db = SessionLocal()
    user = User(username="retention", password_hash=hash_password("strongpass"))
    db.add(user)
    db.flush()
    child = Child(user_id=user.id, name="小星", status_snapshot={"overall_level": 2})
    db.add(child)
    db.flush()
    task = Task(user_id=user.id, child_id=child.id, name="长期训练项目")
    record = ChildRecordFile(
        user_id=user.id, child_id=child.id, original_name="长期保留.pdf",
        file_key="records/keep.pdf", content_type="application/pdf", size_bytes=10,
        created_at=old,
    )
    db.add_all([
        task,
        record,
        Assessment(user_id=user.id, child_id=child.id, answers={}, score=1, stage="start", idempotency_key="old", submitted_at=old),
        Assessment(user_id=user.id, child_id=child.id, answers={}, score=2, stage="start", idempotency_key="new", submitted_at=recent),
        TrainingSession(user_id=user.id, child_id=child.id, skill_name="旧训练", idempotency_key="old", created_at=old),
        TrainingSession(user_id=user.id, child_id=child.id, skill_name="新训练", idempotency_key="new", created_at=recent),
        MoodEntry(user_id=user.id, mood="旧情绪", entry_date=old.date(), created_at=old),
        JournalEntry(user_id=user.id, content="旧记录", created_at=old),
        ChatMessage(user_id=user.id, product="coach", role="user", content="旧对话", created_at=old),
        Report(user_id=user.id, child_id=child.id, title="旧报告", summary="", content={}, file_key="reports/old.pdf", created_at=old),
        CoachGrowthState(user_id=user.id, sessions=[
            {"id": "old", "createdAt": old.isoformat()},
            {"id": "new", "createdAt": recent.isoformat()},
            {"id": "legacy-without-date"},
        ]),
    ])
    db.commit()

    counts = purge_expired_customer_data(db, now=now, storage=storage)

    assert counts["assessments"] == 1
    assert counts["training_sessions"] == 1
    assert counts["coach_growth_sessions"] == 1
    assert storage.deleted == ["reports/old.pdf"]
    assert db.scalar(select(User).where(User.id == user.id))
    assert db.scalar(select(Child).where(Child.id == child.id)).status_snapshot == {"overall_level": 2}
    assert db.scalar(select(Task).where(Task.id == task.id))
    assert db.scalar(select(ChildRecordFile).where(ChildRecordFile.id == record.id))
    assert [row.idempotency_key for row in db.scalars(select(Assessment)).all()] == ["new"]
    assert [row.skill_name for row in db.scalars(select(TrainingSession)).all()] == ["新训练"]
    assert db.scalars(select(MoodEntry)).all() == []
    assert db.scalars(select(JournalEntry)).all() == []
    assert db.scalars(select(ChatMessage)).all() == []
    assert db.scalars(select(Report)).all() == []
    assert [item["id"] for item in db.get(CoachGrowthState, user.id).sessions] == ["new", "legacy-without-date"]
    db.close()


def test_original_record_file_delete_keeps_derived_child_status(client, auth, monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr("app.main.get_storage", lambda: storage)
    monkeypatch.setattr(
        "app.main.analyze_medical_record",
        lambda text: ({"overall_level": 3, "source": "medical_record"}, "已整理"),
    )
    child = client.post("/api/v1/children", headers=auth, json={"name": "小星"}).json()
    uploaded = client.post(
        f"/api/v1/children/{child['id']}/upload-record",
        headers=auth,
        files={"file": ("assessment.txt", b"language and daily living assessment", "text/plain")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["status_snapshot"]["overall_level"] == 3

    files = client.get(f"/api/v1/children/{child['id']}/record-files", headers=auth).json()
    assert len(files) == 1
    assert files[0]["original_name"] == "assessment.txt"
    download = client.get(
        f"/api/v1/children/{child['id']}/record-files/{files[0]['id']}",
        headers=auth,
    )
    assert download.content == b"language and daily living assessment"

    deleted = client.delete(
        f"/api/v1/children/{child['id']}/record-files/{files[0]['id']}",
        headers=auth,
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/children/{child['id']}/record-files", headers=auth).json() == []
    remaining_child = client.get("/api/v1/children", headers=auth).json()[0]
    assert remaining_child["status_snapshot"]["overall_level"] == 3
