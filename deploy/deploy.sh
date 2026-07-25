#!/bin/bash
# ABA 部署脚本 - 开发阶段使用
# 用法: bash deploy/deploy.sh [api|web|all] (默认 all)
#
# 原理:
#   API: 正常 docker build（Python 代码无缓存问题）
#   Web: 本地 vite build → rsync → docker cp（绕过 Docker build 缓存）
#   这样保证前端代码每次都最新

set -euo pipefail

REMOTE="ubuntu@170.106.143.145"
SSH_CMD="sshpass -p Dwang220124 ssh -o StrictHostKeyChecking=no"
SCP_CMD="sshpass -p Dwang220124 scp -o StrictHostKeyChecking=no"
PROJECT="/Users/wangxin/Documents/trae_projects/ABA"
TARGET="${1:-all}"

echo "=== ABA 部署 $(date '+%Y-%m-%d %H:%M:%S') ==="

# === API 部署（docker build）===
deploy_api() {
  echo "--- [API] 同步源码 ---"
  RSYNC_RSH="${SSH_CMD}" rsync -az \
    apps/api/app/ \
    "${REMOTE}":~/AI_codex/apps/api/app/

  echo "--- [API] 重建镜像并重启 ---"
  ${SSH_CMD} "${REMOTE}" "cd ~/AI_codex && docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml build api 2>&1 | tail -3 && docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml up -d api 2>&1 | tail-3"
  echo "[API] 完成"
}

# === Web 部署（本地构建 + docker cp）===
deploy_web() {
  local MOBILE_DIST="${PROJECT}/apps/mobile-web/dist"
  local ADMIN_DIST="${PROJECT}/apps/admin-web/dist"

  # --- mobile-web ---
  echo "--- [Web:mobile] 本地 vite build ---"
  cd "${PROJECT}/apps/mobile-web" && npx vite build 2>&1 | tail -5

  echo "--- [Web:mobile] 上传到服务器 ---"
  RSYNC_RSH="${SSH_CMD}" rsync -az \
    "${MOBILE_DIST}/" \
    "${REMOTE}":/tmp/aba-web-dist/

  # --- admin-web ---
  echo "--- [Web:admin] 本地 vite build ---"
  cd "${PROJECT}/apps/admin-web" && npx vite build 2>&1 | tail -5

  echo "--- [Web:admin] 上传到服务器 ---"
  RSYNC_RSH="${SSH_CMD}" rsync -az \
    "${ADMIN_DIST}/" \
    "${REMOTE}":/tmp/aba-admin-dist/

  # --- 复制到容器 ---
  echo "--- [Web] 复制到容器 + reload nginx ---"
  ${SSH_CMD} "${REMOTE}" "
    if ! docker ps --format '{{.Names}}' | grep -q '^aba-modern-web-1$'; then
      cd ~/AI_codex && docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml up -d web 2>&1 | tail-3
      sleep 2
    fi
    docker cp /tmp/aba-web-dist/. aba-modern-web-1:/usr/share/nginx/html/
    docker cp /tmp/aba-admin-dist/. aba-modern-web-1:/usr/share/nginx/html/admin/
    docker exec aba-modern-web-1 nginx -s reload
    echo '[Web] 容器内文件验证:'
    echo '  mobile:'; docker exec aba-modern-web-1 sh -c 'wc -c /usr/share/nginx/html/assets/*.js'
    echo '  admin:' ; docker exec aba-modern-web-1 sh -c 'wc -c /usr/share/nginx/html/admin/assets/*.js'
  "

  # 验证外部可访问
  JS_NAME=$(ls "${MOBILE_DIST}/assets/"*.js | xargs basename)
  SZ=$(curl -sI "http://170.106.143.145:8080/assets/${JS_NAME}" | grep -i content-length | awk '{print $2}' | tr -d '\r')
  echo "[Web:mobile] 外部访问验证: assets/${JS_NAME} = ${SZ} bytes"

  ADMIN_JS=$(ls "${ADMIN_DIST}/assets/"*.js 2>/dev/null | xargs basename 2>/dev/null || echo "")
  if [ -n "$ADMIN_JS" ]; then
    ASZ=$(curl -sI "http://170.106.143.145:8080/admin/assets/${ADMIN_JS}" | grep -i content-length | awk '{print $2}' | tr -d '\r')
    echo "[Web:admin] 外部访问验证: admin/assets/${ADMIN_JS} = ${ASZ} bytes"
  fi

  if [ "${SZ:-0}" -gt 10000 ]; then
    echo "[Web] 部署成功 ✓"
  else
    echo "[Web] ⚠️ 文件大小异常，可能未正确更新！"
  fi
}

case "$TARGET" in
  api)  deploy_api ;;
  web)  deploy_web ;;
  all)  deploy_api; deploy_web ;;
  *)   echo "用法: $0 [api|web|all]"; exit 1 ;;
esac

echo "=== 全部完成 ==="
