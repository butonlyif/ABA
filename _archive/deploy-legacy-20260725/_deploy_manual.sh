#!/usr/bin/env bash
# 手动部署脚本（绕过 ControlMaster 限制，适配 sandbox 环境）
# 用法: bash deploy/_deploy_manual.sh [main|all]
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 读取 deploy.env
DEPLOY_ENV="${SCRIPT_DIR}/deploy.env"
set -a; . "$DEPLOY_ENV"; set +a

SERVER_IP="${SERVER_IP:-170.106.143.145}"
SERVER_USER="${SERVER_USER:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-~/AI_codex}"
SSH_PASS="${SSH_PASS:-}"

if [[ -z "$SSH_PASS" ]]; then
    echo "[错误] 未配置 SSH_PASS"; exit 1
fi

export SSHPASS="$SSH_PASS"
TARGET="${1:-main}"

# 不使用 ControlMaster（sandbox 兼容）
SSH_BASE=(-o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ControlMaster=no -o ControlPath=none)
SSH_OPTS=(ssh "${SSH_BASE[@]}")
RSYNC_SSH=(ssh "${SSH_BASE[@]}")

echo ""
echo "==> 项目根: $PROJECT_ROOT"
echo "==> 目标服务器: ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}"
echo "==> 重建目标: $TARGET"
echo ""

# ---------- 1. rsync 同步代码（排除 data/，保护用户数据）----------
echo "==> [1/4] rsync src/MVP_web 代码（排除 data/）..."
sshpass -e rsync -av \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude 'data/' \
    --exclude '.env' \
    --exclude '.env.local' \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/src/MVP_web/" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/src/MVP_web/"

echo ""
echo "==> [2/4] rsync deploy 配置 + 知识库..."
sshpass -e rsync -av \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/deploy/docker-compose.yml" \
    "$PROJECT_ROOT/deploy/Dockerfile" \
    "$DEPLOY_ENV" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/deploy/"

sshpass -e rsync -av \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/.dockerignore" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.dockerignore"

# 知识库（--delete 保持同步）
sshpass -e ssh "${SSH_BASE[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "mkdir -p ${REMOTE_DIR}/docs/知识库" 2>/dev/null || true
sshpass -e rsync -av --delete \
    --exclude '.DS_Store' \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/docs/知识库/" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/docs/知识库/"

echo ""
echo "==> [3/4] 跳过 src/aba/图片（SKIP_IMAGES，未变更）"
echo ""

# ---------- 4. 远程 build + 启动 ----------
echo "==> [4/4] 远程 build + 启动..."
COMPOSE="docker compose --env-file deploy/deploy.env -f deploy/docker-compose.yml"

case "$TARGET" in
    admin)  SVC="aba-admin" ;;
    main)   SVC="aba-assistant" ;;
    all|*)  SVC="" ;;
esac

REMOTE_CMD="cd ${REMOTE_DIR} && ${COMPOSE} up -d --build ${SVC}"
sshpass -e ssh "${SSH_BASE[@]}" "${SERVER_USER}@${SERVER_IP}" "$REMOTE_CMD"

echo ""
echo "==> 容器状态："
sshpass -e ssh "${SSH_BASE[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "cd ${REMOTE_DIR} && ${COMPOSE} ps"

# 三方校验
echo ""
echo "==> 三方校验 app_prototype.py..."
LOCAL_MD5="$(md5 -q "$PROJECT_ROOT/src/MVP_web/app_prototype.py" 2>/dev/null \
    || md5sum "$PROJECT_ROOT/src/MVP_web/app_prototype.py" 2>/dev/null | awk '{print $1}')"
SRV_MD5="$(sshpass -e ssh "${SSH_BASE[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "md5sum ${REMOTE_DIR}/src/MVP_web/app_prototype.py 2>/dev/null | awk '{print \$1}'")"
CTR_MD5="$(sshpass -e ssh "${SSH_BASE[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "docker exec aba-assistant md5sum /app/src/MVP_web/app_prototype.py 2>/dev/null | awk '{print \$1}'")"
echo "    本地源码:   ${LOCAL_MD5:-?}"
echo "    服务器源码: ${SRV_MD5:-?}"
echo "    容器内代码: ${CTR_MD5:-?}"

echo ""
echo "==> 部署完成！"
