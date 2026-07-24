#!/usr/bin/env bash
# 临时备份脚本 - 远程用户数据备份
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_ENV="${SCRIPT_DIR}/deploy.env"
set -a; . "$DEPLOY_ENV"; set +a

SERVER_IP="${SERVER_IP:-170.106.143.145}"
SERVER_USER="${SERVER_USER:-ubuntu}"
SSH_PASS="${SSH_PASS:-}"

if [[ -z "$SSH_PASS" ]]; then
    echo "[错误] 未配置 SSH_PASS"
    exit 1
fi

export SSHPASS="$SSH_PASS"

echo "=== 连接服务器 $SERVER_USER@$SERVER_IP ==="

# 备份用户数据
sshpass -e ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
    "${SERVER_USER}@${SERVER_IP}" \
    'cd ~/AI_codex && mkdir -p backups && STAMP=$(date +%Y%m%d-%H%M%S) && \
     tar -czf backups/data-${STAMP}.tar.gz -C deploy data 2>/dev/null && \
     sha256sum backups/data-${STAMP}.tar.gz > backups/data-${STAMP}.sha256 && \
     echo "=== 备份完成 ===" && \
     ls -lh backups/data-${STAMP}.tar.gz && \
     echo "=== SHA256 ===" && \
     cat backups/data-${STAMP}.sha256 && \
     echo "=== 当前容器状态 ===" && \
     docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -10'
