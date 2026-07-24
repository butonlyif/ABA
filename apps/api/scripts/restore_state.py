"""Restore a backup created by backup_state.py.

This command is deliberately locked behind --confirm RESTORE. Always restore
into staging first. It validates every file before changing the target.
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "RESTORE":
        raise SystemExit("拒绝执行：必须明确传入 --confirm RESTORE")
    settings = get_settings()
    with tempfile.TemporaryDirectory(prefix="aba-restore-") as temp:
        root = Path(temp)
        with tarfile.open(args.archive, "r:gz") as archive:
            for member in archive.getmembers():
                target = (root / member.name).resolve()
                if root.resolve() not in target.parents and target != root.resolve():
                    raise SystemExit("备份包含非法路径")
            archive.extractall(root)
        source = root / "aba-backup"
        manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["files"].items():
            path = source / name
            if not path.is_file() or path.stat().st_size != expected["size"] or sha256(path) != expected["sha256"]:
                raise SystemExit(f"备份校验失败：{name}")
        database = manifest["database"]
        if database["type"] == "sqlite":
            if not settings.database_url.startswith("sqlite"):
                raise SystemExit("备份是 SQLite，但目标不是 SQLite")
            target = Path(settings.database_url.split("///", 1)[1]).resolve()
            with sqlite3.connect(source / database["file"]) as source_db, sqlite3.connect(target) as target_db:
                source_db.backup(target_db)
        else:
            if not settings.database_url.startswith("postgresql"):
                raise SystemExit("备份是 PostgreSQL，但目标不是 PostgreSQL")
            postgres_url = settings.database_url.replace("postgresql+psycopg", "postgresql", 1)
            subprocess.run(
                ["pg_restore", "--clean", "--if-exists", "--no-owner", "--dbname", postgres_url, str(source / database["file"])],
                check=True,
            )
        object_root = source / "objects"
        if settings.storage_backend == "local":
            target = Path(settings.upload_path)
            target.mkdir(parents=True, exist_ok=True)
            shutil.copytree(object_root, target, dirs_exist_ok=True)
        else:
            import boto3
            client = boto3.client(
                "s3", endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key, aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
            for path in object_root.rglob("*"):
                if path.is_file():
                    client.upload_file(str(path), settings.s3_bucket, str(path.relative_to(object_root)))
    print(json.dumps({"restored": True, "archive": str(args.archive.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
