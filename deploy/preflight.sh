#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_ROOT="${PROJECT_ROOT}/apps/api"
MIGRATION_REPORT="${1:-}"
BACKUP_ARCHIVE="${2:-}"

if [[ -z "${MIGRATION_REPORT}" || -z "${BACKUP_ARCHIVE}" ]]; then
  echo "用法: bash deploy/preflight.sh <migration-report.json> <backup.tar.gz>"
  exit 2
fi

cd "${API_ROOT}"
./.venv/bin/python scripts/security_preflight.py
./.venv/bin/python -m pytest -q
./.venv/bin/alembic heads
./.venv/bin/python scripts/release_preflight.py \
  --migration-report "${MIGRATION_REPORT}" \
  --backup "${BACKUP_ARCHIVE}"

cd "${PROJECT_ROOT}"
npm --workspace @aba/mobile-web run build
npm --workspace @aba/admin-web run build

echo "预发布门禁全部通过。"
