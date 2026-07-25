#!/usr/bin/env bash
# 新平台部署（sandbox 兼容版，并行于旧 8501/8503 服务）
# 保留旧平台用户数据，自动迁移到新 PostgreSQL
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/deploy.env"

REMOTE_DIR="${REMOTE_DIR:-/home/${SERVER_USER}/AI_codex}"
REMOTE_BACKUPS="${REMOTE_DIR}/backups"
COMPOSE="docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml"
export SSHPASS="${SSH_PASS:-}"

# sandbox 兼容：禁用 ControlMaster
SSH_OPTS=(-o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ControlMaster=no -o ControlPath=none)
SSH=(sshpass -e ssh "${SSH_OPTS[@]}")
# rsync -e 字符串：sshpass -p 直接传密码（rsync -e 不支持 shell 语法）
RSYNC_SSH="sshpass -p ${SSH_PASS} ssh ${SSH_OPTS[*]}"
TARGET="${SERVER_USER}@${SERVER_IP}"

echo "==> [1/6] 检查服务器连接..."
"${SSH[@]}" "${TARGET}" "docker compose version && echo '连接OK'"

echo ""
echo "==> [2/6] 备份旧平台数据（数据位于 deploy/data/）..."
"${SSH[@]}" "${TARGET}" "
  set -e
  mkdir -p '${REMOTE_BACKUPS}'
  stamp=\$(date +%Y%m%d-%H%M%S)
  # 数据在 deploy/data/（compose bind mount），不在 src/MVP_web/data
  if [[ -d '${REMOTE_DIR}/deploy/data' ]]; then
    tar -C '${REMOTE_DIR}/deploy' -czf '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.tar.gz' data 2>/dev/null
    sha256sum '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.tar.gz' > '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.sha256'
    echo \"备份完成: legacy-data-\${stamp}.tar.gz\"
    ls -lh '${REMOTE_BACKUPS}/legacy-data-'\${stamp}'.tar.gz'
  else
    echo '警告: deploy/data 不存在，跳过备份'
  fi
"

echo ""
echo "==> [3/6] 同步新平台代码..."
"${SSH[@]}" "${TARGET}" "mkdir -p '${REMOTE_DIR}/apps' '${REMOTE_DIR}/packages' '${REMOTE_DIR}/deploy'"

echo "  - apps/ (排除 node_modules/dist/.venv)"
rsync -az \
  --exclude node_modules --exclude dist --exclude .venv --exclude '*.db' --exclude uploads \
  -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/apps/" "${TARGET}:${REMOTE_DIR}/apps/"

echo "  - packages/"
rsync -az \
  -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/packages/" "${TARGET}:${REMOTE_DIR}/packages/"

echo "  - package.json + package-lock.json"
rsync -az \
  -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/package.json" "${PROJECT_ROOT}/package-lock.json" \
  "${TARGET}:${REMOTE_DIR}/"

echo "  - docker-compose.modern.yml"
rsync -az \
  -e "${RSYNC_SSH}" \
  "${PROJECT_ROOT}/deploy/docker-compose.modern.yml" \
  "${TARGET}:${REMOTE_DIR}/deploy/"

echo ""
echo "==> [4/6] 初始化生产密钥（已有则不覆盖）..."
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
    echo '已生成 deploy/modern.env'
  else
    echo 'deploy/modern.env 已存在，保持不变'
  fi
"

echo ""
echo "==> [5/6] 构建并启动新平台（首次构建约 5-10 分钟）..."
"${SSH[@]}" "${TARGET}" "cd '${REMOTE_DIR}' && ${COMPOSE} up -d --build"

echo ""
echo "==> [6/6] 从旧数据迁移到新 PostgreSQL（幂等，不修改源数据）..."
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

echo ""
echo "==> 容器状态："
"${SSH[@]}" "${TARGET}" "cd '${REMOTE_DIR}' && ${COMPOSE} ps"

echo ""
echo "==> 部署完成！"
echo "    新平台：http://${SERVER_IP}:8080/"
echo "    旧平台保持不变：8501 / 8503"
