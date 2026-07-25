#!/usr/bin/env bash
# Parallel production deployment. Keeps the legacy 8501/8503 services intact.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/deploy.env"

REMOTE_DIR="${REMOTE_DIR:-/home/${SERVER_USER}/AI_codex}"
REMOTE_BACKUPS="${REMOTE_DIR}/backups"
COMPOSE="docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml"
export SSHPASS="${SSH_PASS:-}"
SSH=(sshpass -e ssh -o StrictHostKeyChecking=no)
RSYNC_SSH="ssh -o StrictHostKeyChecking=no"
TARGET="${SERVER_USER}@${SERVER_IP}"

if [[ -n "${SSH_KEY:-}" ]]; then
  SSH=(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no)
  RSYNC_SSH="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no"
fi

echo "检查服务器连接与 Docker..."
"${SSH[@]}" "${TARGET}" "docker compose version && test -d '${REMOTE_DIR}/src/MVP_web/data'"

echo "创建切流前旧客户数据备份（不修改源数据）..."
"${SSH[@]}" "${TARGET}" "
  set -e
  mkdir -p '${REMOTE_BACKUPS}'
  stamp=\$(date +%Y%m%d-%H%M%S)
  tar -C '${REMOTE_DIR}/src/MVP_web' -czf '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.tar.gz' data
  sha256sum '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.tar.gz' > '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.sha256'
"

echo "同步现代平台代码（不使用 --delete，不同步客户数据）..."
"${SSH[@]}" "${TARGET}" "mkdir -p '${REMOTE_DIR}/apps' '${REMOTE_DIR}/packages' '${REMOTE_DIR}/deploy'"
sshpass -e rsync -az -e "${RSYNC_SSH}" \
  --exclude node_modules --exclude dist --exclude .venv --exclude '*.db' --exclude uploads \
  "${PROJECT_ROOT}/apps/" "${TARGET}:${REMOTE_DIR}/apps/"
sshpass -e rsync -az -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/packages/" "${TARGET}:${REMOTE_DIR}/packages/"
sshpass -e rsync -az -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/package.json" "${PROJECT_ROOT}/package-lock.json" \
  "${TARGET}:${REMOTE_DIR}/"
sshpass -e rsync -az -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/deploy/docker-compose.modern.yml" \
  "${TARGET}:${REMOTE_DIR}/deploy/"

echo "初始化独立生产密钥（已有文件时保持不变）..."
"${SSH[@]}" "${TARGET}" "
  set -e
  cd '${REMOTE_DIR}'
  if test ! -f deploy/modern.env; then
    umask 077
    postgres_password=\$(openssl rand -hex 24)
    jwt_secret=\$(openssl rand -hex 48)
    minio_password=\$(openssl rand -hex 24)
    {
      echo \"POSTGRES_PASSWORD=\${postgres_password}\"
      echo \"ABA_JWT_SECRET=\${jwt_secret}\"
      echo \"ABA_CORS_ORIGINS=http://${SERVER_IP}:8080\"
      echo \"MINIO_ROOT_USER=aba-storage\"
      echo \"MINIO_ROOT_PASSWORD=\${minio_password}\"
    } > deploy/modern.env
  fi
"

echo "构建并启动现代平台独立服务..."
"${SSH[@]}" "${TARGET}" "cd '${REMOTE_DIR}' && ${COMPOSE} up -d --build"

echo "从服务器旧数据执行幂等迁移..."
"${SSH[@]}" "${TARGET}" "
  set -e
  cd '${REMOTE_DIR}'
  ${COMPOSE} run --rm \
    -v '${REMOTE_DIR}/src/MVP_web/data:/legacy-data:ro' \
    -v '${REMOTE_BACKUPS}:/migration-output' \
    api python scripts/migrate_legacy.py \
      --legacy-root /legacy-data \
      --report /migration-output/modern-migration-report.json \
      --apply
"

echo "检查容器、API、迁移报告和客户数量..."
"${SSH[@]}" "${TARGET}" "
  set -e
  cd '${REMOTE_DIR}'
  ${COMPOSE} ps
  ${COMPOSE} run --rm \
    -v '${REMOTE_BACKUPS}:/migration-output:ro' \
    api python scripts/release_preflight.py \
      --migration-report /migration-output/modern-migration-report.json \
      --allow-local
  ${COMPOSE} exec -T api python -c \"
import json, urllib.request
print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/ready')))
\"
  curl -fsS http://127.0.0.1:8080/ >/dev/null
"

echo "部署完成：http://${SERVER_IP}:8080/"
echo "旧服务保持不变：8501 / 8503"
