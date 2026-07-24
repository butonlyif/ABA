"""Block a release until data, schema, queue and storage checks pass."""
import argparse
import hashlib
import json
import tarfile
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal, engine
from app.models import Child, Report, Task, TrainingSession, User
from app.services.storage import get_storage


def verify_backup(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "备份文件不存在"
    with tarfile.open(path, "r:gz") as archive:
        manifest_file = archive.extractfile("aba-backup/manifest.json")
        if not manifest_file:
            return False, "备份清单不存在"
        manifest = json.load(manifest_file)
        for name, expected in manifest["files"].items():
            handle = archive.extractfile(f"aba-backup/{name}")
            if not handle:
                return False, f"备份缺少 {name}"
            content = handle.read()
            if len(content) != expected["size"] or hashlib.sha256(content).hexdigest() != expected["sha256"]:
                return False, f"备份校验失败 {name}"
    return True, "备份校验通过"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration-report", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--allow-local", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    checks: list[dict] = []

    def check(name: str, passed: bool, detail) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("environment", settings.environment in {"staging", "production"} or args.allow_local, settings.environment)
    alembic = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic)
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    head = script.get_current_head()
    check("database_migration", current == head, {"current": current, "head": head})

    db = SessionLocal()
    try:
        counts = {
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "children": db.scalar(select(func.count()).select_from(Child)) or 0,
            "tasks": db.scalar(select(func.count()).select_from(Task)) or 0,
            "training_sessions": db.scalar(select(func.count()).select_from(TrainingSession)) or 0,
            "reports": db.scalar(select(func.count()).select_from(Report)) or 0,
        }
        check("database_read", True, counts)
    finally:
        db.close()

    key = f"preflight/{uuid4()}.txt"
    try:
        storage = get_storage()
        storage.put(key, b"aba-preflight", "text/plain")
        content, _ = storage.get(key)
        storage.delete(key)
        check("object_storage", content == b"aba-preflight", settings.storage_backend)
    except Exception as exc:
        check("object_storage", False, type(exc).__name__)

    if settings.redis_url:
        try:
            from redis import Redis
            check("redis", bool(Redis.from_url(settings.redis_url).ping()), "connected")
        except Exception as exc:
            check("redis", False, type(exc).__name__)
    else:
        check("redis", args.allow_local, "disabled")

    if args.migration_report:
        report = json.loads(args.migration_report.read_text(encoding="utf-8"))
        users = report.get("per_user", {})
        passed = (
            not report.get("dry_run", True)
            and not report.get("failures")
            and not report.get("conflicts")
            and bool(users)
            and all(item.get("validated") for item in users.values())
        )
        check("legacy_migration", passed, {
            "users": len(users), "failures": report.get("failures", []),
            "conflicts": report.get("conflicts", []),
        })
    else:
        check("legacy_migration", args.allow_local, "未提供迁移报告")

    if args.backup:
        passed, detail = verify_backup(args.backup)
        check("verified_backup", passed, detail)
    else:
        check("verified_backup", args.allow_local, "未提供备份")

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ready": all(item["passed"] for item in checks),
        "checks": checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
