#!/usr/bin/env bash
# ============================================================
# ABA 智能助手 - 一键打开 SSH 隧道访问后台
#
# 用法：
#   bash deploy/tunnel.sh
#
# 跑起来后让窗口挂着，浏览器打开 http://127.0.0.1:8502
# 按 Ctrl+C 关闭隧道
#
# 环境变量（可选覆盖）：
#   SERVER_IP=xxx      默认 170.106.143.145
#   SERVER_USER=xxx    默认 ubuntu
#   LOCAL_PORT=xxx     默认 8502
#   SSH_KEY=/path/key  指定 SSH 私钥
# ============================================================

# 故意不开 set -u：macOS 自带 bash 3.2 对空数组 "${arr[@]}" 不友好
set -eo pipefail

SERVER_IP="${SERVER_IP:-170.106.143.145}"
SERVER_USER="${SERVER_USER:-ubuntu}"
LOCAL_PORT="${LOCAL_PORT:-8502}"
SSH_KEY="${SSH_KEY:-}"

SSH_OPTS=()
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS+=("-i" "$SSH_KEY")
fi

# 检查本地端口是否被占
if lsof -iTCP:"$LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "⚠️  本地端口 ${LOCAL_PORT} 已被占用。可能是上次的隧道还在跑。"
    echo "    查看占用： lsof -iTCP:${LOCAL_PORT} -sTCP:LISTEN"
    echo "    或者用其他端口： LOCAL_PORT=8503 bash deploy/tunnel.sh"
    exit 1
fi

echo "==> 建立 SSH 隧道 127.0.0.1:${LOCAL_PORT} → ${SERVER_USER}@${SERVER_IP}:8502"
echo "==> 浏览器打开 http://127.0.0.1:${LOCAL_PORT}"
echo "==> 按 Ctrl+C 关闭"
echo ""

exec ssh "${SSH_OPTS[@]}" \
    -N \
    -L "${LOCAL_PORT}:127.0.0.1:8502" \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    "${SERVER_USER}@${SERVER_IP}"
