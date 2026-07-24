"""Idempotent legacy SQLite/JSON importer.

The command is dry-run by default. Pass --apply only after reviewing the JSON
report. Source files are never modified or deleted.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import ChatMessage, Child, GrowthProgress, JournalEntry, MoodEntry, Report, Task, TrainingSession, Trial, User


def legacy_id(namespace: str, value: str) -> str:
    digest = hashlib.md5(f"{namespace}:{value}".encode(), usedforsecurity=False).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def rows(connection: sqlite3.Connection, table: str) -> list[dict]:
    try:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]  # trusted table list only
    except sqlite3.OperationalError:
        return []


def legacy_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        year, month, day = (int(part) for part in value.split("-")[:3])
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def legacy_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", type=Path, default=Path("src/MVP_web/data"))
    parser.add_argument("--report", type=Path, default=Path("migration-report.json"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    source_db = args.legacy_root / "users" / "memory.db"
    if not source_db.exists():
        raise SystemExit(f"Legacy database not found: {source_db}")
    backup_dir = args.report.parent / f"legacy-backup-{datetime.now():%Y%m%d-%H%M%S}"
    report = {
        "dry_run": not args.apply, "source": str(source_db), "counts": {},
        "failures": [], "warnings": [], "conflicts": [], "per_user": {},
    }

    connection = sqlite3.connect(source_db)
    legacy_users = rows(connection, "users")
    legacy_children = rows(connection, "children")
    legacy_tasks = rows(connection, "tasks")
    legacy_conversations = rows(connection, "conversations")
    legacy_reports = rows(connection, "reports")
    report["counts"].update(
        users=len(legacy_users), children=len(legacy_children), tasks=len(legacy_tasks),
        conversations=len(legacy_conversations), reports=len(legacy_reports),
    )
    for item in legacy_users:
        user_id = item["user_id"]
        report["per_user"][user_id] = {
            "username": item["username"],
            "children": sum(row["user_id"] == user_id for row in legacy_children),
            "tasks": sum(row["user_id"] == user_id for row in legacy_tasks),
            "conversations": sum(row["user_id"] == user_id for row in legacy_conversations),
            "reports": sum(row["user_id"] == user_id for row in legacy_reports),
        }

    training_files = list((args.legacy_root / "training").glob("*.json"))
    coach_files = list((args.legacy_root / "users").glob("*/coach_data.json"))
    report["counts"]["training_files"] = len(training_files)
    report["counts"]["coach_files"] = len(coach_files)
    source_files = [source_db, *training_files, *coach_files]
    report["source_manifest"] = {
        str(path.relative_to(args.legacy_root)): {"size": path.stat().st_size, "sha256": file_sha256(path)}
        for path in source_files
    }
    if not args.apply:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    backup_dir.mkdir(parents=True)
    for directory in ("users", "training"):
        source = args.legacy_root / directory
        if source.exists():
            shutil.copytree(source, backup_dir / directory)
    with sqlite3.connect(backup_dir / "users" / "memory.db") as backup_db:
        connection.backup(backup_db)

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        user_id_map: dict[str, str] = {}
        for item in legacy_users:
            legacy_user_id = item["user_id"]
            by_id = db.get(User, legacy_user_id)
            by_name = db.scalar(select(User).where(User.username == item["username"]))
            if by_id and by_name and by_id.id != by_name.id:
                report["conflicts"].append({
                    "legacy_user_id": legacy_user_id, "username": item["username"],
                    "reason": "用户 ID 与用户名分别匹配到不同账户",
                })
                continue
            existing = by_id or by_name
            if existing:
                user_id_map[legacy_user_id] = existing.id
                report["per_user"][legacy_user_id]["result"] = "matched_existing"
            else:
                db.add(User(
                    id=legacy_user_id, username=item["username"], password_hash=item["password_hash"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                ))
                user_id_map[legacy_user_id] = legacy_user_id
                report["per_user"][legacy_user_id]["result"] = "created"
        db.flush()
        for item in legacy_children:
            mapped_user_id = user_id_map.get(item["user_id"])
            if not mapped_user_id:
                report["failures"].append(f"孩子 {item['child_id']} 的所属用户存在冲突，已跳过")
                continue
            if not db.get(Child, item["child_id"]):
                db.add(Child(
                    id=item["child_id"], user_id=mapped_user_id, name=item["name"],
                    birth_date=legacy_date(item.get("birth_date")), diagnosis=item.get("diagnosis"),
                    goals=item.get("intervention_goals"), is_current=False,
                ))
        db.flush()
        for item in legacy_tasks:
            mapped_user_id = user_id_map.get(item["user_id"])
            if not mapped_user_id:
                report["failures"].append(f"任务 {item['task_id']} 的所属用户存在冲突，已跳过")
                continue
            if not db.get(Task, item["task_id"]):
                db.add(Task(
                    id=item["task_id"], user_id=mapped_user_id, child_id=item["child_id"],
                    name=item["task_name"], description=item.get("task_description"),
                    category=item.get("category") or "基础能力", status=item.get("status") or "pending",
                    source="assessment" if item.get("is_auto_generated") else "manual",
                ))
        db.flush()
        imported_conversations = imported_reports = 0
        for item in legacy_conversations:
            mapped_user_id = user_id_map.get(item["user_id"])
            message_id = legacy_id("conversation", str(item["id"]))
            if mapped_user_id and not db.get(ChatMessage, message_id):
                metadata = json.loads(item.get("metadata") or "{}")
                db.add(ChatMessage(
                    id=message_id, user_id=mapped_user_id, product="aba",
                    role=item["role"], content=item["content"], sources=metadata.get("sources", []),
                    created_at=datetime.fromisoformat(item["timestamp"]),
                ))
                imported_conversations += 1
        for item in legacy_reports:
            mapped_user_id = user_id_map.get(item["user_id"])
            if mapped_user_id and not db.get(Report, item["report_id"]):
                try:
                    content = json.loads(item.get("content") or "{}")
                except json.JSONDecodeError:
                    content = {"legacy_text": item.get("content") or ""}
                db.add(Report(
                    id=item["report_id"], user_id=mapped_user_id, child_id=item["child_id"],
                    status="completed", title=item.get("title") or "历史报告",
                    summary=item.get("summary") or "", content=content,
                    created_at=datetime.fromisoformat(item["created_at"]),
                ))
                imported_reports += 1
        imported_sessions = imported_trials = imported_moods = imported_journals = imported_growth = 0
        for path in training_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            legacy_user_id = path.stem
            user_id = user_id_map.get(legacy_user_id)
            if not user_id:
                report["warnings"].append(f"训练文件 {path.name} 没有对应客户账号，作为孤立测试数据跳过")
                continue
            for item in payload.get("sessions", []):
                session_id = legacy_id("training", f"{user_id}:{item['session_id']}")
                if db.get(TrainingSession, session_id):
                    continue
                session = TrainingSession(
                    id=session_id, user_id=user_id, child_id=item["child_id"],
                    task_id=item.get("task_id"), skill_name=item["skill_name"],
                    status="completed" if item.get("finished") else "active",
                    idempotency_key=f"legacy:{item['session_id']}",
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
                db.add(session)
                for sequence, result in enumerate(item.get("trials", []), 1):
                    normalized = {"+": "I", "-": "E"}.get(result, result)
                    db.add(Trial(session_id=session_id, sequence=sequence, result=normalized))
                    imported_trials += 1
                imported_sessions += 1
        for path in coach_files:
            legacy_user_id = path.parent.name
            user_id = user_id_map.get(legacy_user_id)
            if not user_id:
                report["warnings"].append(f"教练文件 {path.name} 没有对应客户账号，已在原始备份中保留")
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            moods_by_day: dict[date, dict] = {}
            for item in payload.get("mood_log", []):
                moment = legacy_datetime(item.get("time"))
                moods_by_day[moment.date()] = item
            for entry_date, item in moods_by_day.items():
                existing = db.scalar(select(MoodEntry).where(
                    MoodEntry.user_id == user_id, MoodEntry.entry_date == entry_date
                ))
                note_parts = [
                    f"触发：{item.get('trigger')}" if item.get("trigger") else "",
                    f"身体感受：{item.get('body_feeling')}" if item.get("body_feeling") else "",
                    f"想法：{item.get('thought')}" if item.get("thought") else "",
                    item.get("note") or "",
                ]
                if not existing:
                    db.add(MoodEntry(
                        id=legacy_id("coach-mood", f"{legacy_user_id}:{entry_date}"),
                        user_id=user_id, mood=f"{item.get('emoji', '')} {item.get('label', '')}".strip(),
                        intensity=int(item.get("intensity") or item.get("score") or 3),
                        note="\n".join(part for part in note_parts if part),
                        entry_date=entry_date, created_at=legacy_datetime(item.get("time")),
                    ))
                    imported_moods += 1
            for index, item in enumerate(payload.get("journal_entries", [])):
                journal_id = legacy_id("coach-journal", f"{legacy_user_id}:{item.get('time')}:{index}")
                if not db.get(JournalEntry, journal_id):
                    db.add(JournalEntry(
                        id=journal_id, user_id=user_id, content=item.get("content") or "",
                        prompt=item.get("mood"), created_at=legacy_datetime(item.get("time")),
                    ))
                    imported_journals += 1
            stage = int(payload.get("growth_stage") or 1)
            for stage_number in range(1, min(stage, 6) + 1):
                existing = db.scalar(select(GrowthProgress).where(
                    GrowthProgress.user_id == user_id, GrowthProgress.stage == stage_number
                ))
                if not existing:
                    db.add(GrowthProgress(
                        id=legacy_id("coach-growth", f"{legacy_user_id}:{stage_number}"),
                        user_id=user_id, stage=stage_number,
                        status="completed" if stage_number < stage else "active",
                    ))
                    imported_growth += 1
            report["per_user"][legacy_user_id]["coach_raw_records"] = {
                "moods": len(payload.get("mood_log", [])),
                "journals": len(payload.get("journal_entries", [])),
                "personal_records": len(payload.get("personal_records", [])),
                "growth_projects": len(payload.get("growth_projects", [])),
                "raw_backup": f"users/{legacy_user_id}/coach_data.json",
            }
        db.commit()
        for legacy_user_id, mapped_user_id in user_id_map.items():
            expected = report["per_user"][legacy_user_id]
            target_counts = {
                "children": db.scalar(select(func.count()).select_from(Child).where(Child.user_id == mapped_user_id)),
                "tasks": db.scalar(select(func.count()).select_from(Task).where(Task.user_id == mapped_user_id)),
                "conversations": db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.user_id == mapped_user_id)),
                "reports": db.scalar(select(func.count()).select_from(Report).where(Report.user_id == mapped_user_id)),
            }
            expected["target_counts"] = target_counts
            expected["validated"] = all(target_counts[key] >= expected[key] for key in target_counts)
        report["imported"] = {
            "users_created": sum(item.get("result") == "created" for item in report["per_user"].values()),
            "users_matched": sum(item.get("result") == "matched_existing" for item in report["per_user"].values()),
            "conversations": imported_conversations, "reports": imported_reports,
            "sessions": imported_sessions, "trials": imported_trials,
            "moods": imported_moods, "journals": imported_journals, "growth": imported_growth,
        }
        report["success"] = not report["failures"] and not report["conflicts"] and all(
            item.get("validated", False) for item in report["per_user"].values()
        )
    except Exception as exc:
        db.rollback()
        report["failures"].append(str(exc))
        raise
    finally:
        db.close()
        connection.close()
        report["backup"] = str(backup_dir)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
