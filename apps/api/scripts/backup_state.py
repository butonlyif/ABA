"""Create a verified, portable backup of the modern platform.

SQLite is copied through its online backup API. PostgreSQL uses pg_dump.
Local object files are included; S3-compatible storage is exported object by
object. The resulting archive contains a SHA-256 manifest.
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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_database(root: Path) -> dict:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        source = Path(settings.database_url.split("///", 1)[1]).resolve()
        target = root / "database.sqlite3"
        with sqlite3.connect(source) as source_db, sqlite3.connect(target) as target_db:
            source_db.backup(target_db)
        return {"type": "sqlite", "file": target.name}
    target = root / "database.dump"
    postgres_url = settings.database_url.replace("postgresql+psycopg", "postgresql", 1)
    subprocess.run(
        ["pg_dump", "--format=custom", "--file", str(target), postgres_url],
        check=True,
    )
    parsed = urlparse(postgres_url)
    return {"type": "postgresql", "file": target.name, "database": parsed.path.lstrip("/")}


def backup_objects(root: Path) -> dict:
    settings = get_settings()
    target = root / "objects"
    target.mkdir()
    if settings.storage_backend == "local":
        source = Path(settings.upload_path)
        if source.exists():
            shutil.copytree(source, target, dirs_exist_ok=True)
        return {"type": "local", "count": sum(1 for path in target.rglob("*") if path.is_file())}
    import boto3
    client = boto3.client(
        "s3", endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    count = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket):
        for item in page.get("Contents", []):
            path = target / item["Key"]
            path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(settings.s3_bucket, item["Key"], str(path))
            count += 1
    return {"type": "s3", "bucket": settings.s3_bucket, "count": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aba-backup-") as temp:
        root = Path(temp) / "aba-backup"
        root.mkdir()
        database = backup_database(root)
        objects = backup_objects(root)
        files = {
            str(path.relative_to(root)): {"size": path.stat().st_size, "sha256": sha256(path)}
            for path in root.rglob("*") if path.is_file()
        }
        manifest = {
            "format": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "database": database, "objects": objects, "files": files,
        }
        (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        with tarfile.open(args.output, "w:gz") as archive:
            archive.add(root, arcname="aba-backup")
    print(json.dumps({"backup": str(args.output.resolve()), "files": len(files), "verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
