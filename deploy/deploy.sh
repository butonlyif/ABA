#!/bin/bash
# ABA 部署脚本 - 支持 SSH(回退)与 TAT(默认优先)双通道
# 用法: bash deploy/deploy.sh [api|web|all] (默认 all)
#
# 通道选择:
#   1) 若 deploy/tat.env 存在且字段齐全 → 走腾讯云 TAT 自动化助手(443/HTTPS,不碰 22 端口)
#   2) 否则走 SSH(回退):开发期用密钥 ~/.ssh/aba_tencent,临时可用 SSH_PASSWORD 覆盖
#
# 原理同旧版:
#   API: rsync/推送源码 → 重建镜像 → docker compose up -d api
#   Web: 本地 vite build → 上传 dist → docker cp → nginx reload

set -euo pipefail

PROJECT="/Users/wangxin/Documents/trae_projects/ABA"
TARGET="${1:-all}"
REMOTE_HOST="170.106.143.145"
REMOTE_USER="ubuntu"
REMOTE_DIR="~/AI_codex"

echo "=== ABA 部署 $(date '+%Y-%m-%d %H:%M:%S') ==="

# ---------------------------------------------------------------------------
# TAT 通道:走腾讯云 API,完全不走 22 端口
# ---------------------------------------------------------------------------
load_tat_env() {
  local f="${PROJECT}/deploy/tat.env"
  [[ -f "$f" ]] || return 1
  set -a; source "$f"; set +a
  [[ -n "${TAT_SECRET_ID:-}" && -n "${TAT_SECRET_KEY:-}" \
     && -n "${TAT_REGION:-}"   && -n "${TAT_INSTANCE_ID:-}" ]] || return 1
}

deploy_via_tat_api() {
  echo "--- [API/TAT] 推送源码到服务器(走 SSH rsync,低频) ---"
  deploy_via_ssh_sync_app || echo "⚠️  源码同步失败,继续尝试仅触发远端命令"

  echo "--- [API/TAT] 触发远端命令(走 443 端口) ---"
  TAT_COMMAND_ID="$TAT_COMMAND_ID_API" tat_invoke
}

deploy_via_tat_web() {
  local MOBILE_DIST="${PROJECT}/apps/mobile-web/dist"
  local ADMIN_DIST="${PROJECT}/apps/admin-web/dist"

  echo "--- [Web:mobile] 本地 vite build ---"
  (cd "${PROJECT}/apps/mobile-web" && npx vite build 2>&1 | tail -5)
  echo "--- [Web:admin] 本地 vite build ---"
  (cd "${PROJECT}/apps/admin-web" && npx vite build 2>&1 | tail -5)

  echo "--- [Web/TAT] 上传 dist 到服务器 ---"
  deploy_via_ssh_upload_dist "${MOBILE_DIST}" "${ADMIN_DIST}" || echo "⚠️  dist 上传失败"

  echo "--- [Web/TAT] 触发远端命令(走 443 端口) ---"
  TAT_COMMAND_ID="$TAT_COMMAND_ID_WEB" tat_invoke
}

tat_invoke() {
  if ! command -v tccli >/dev/null 2>&1; then
    echo "❌ TAT 通道需要 tccli: brew install tencentcloud-cli" >&2
    echo "   或临时改回 SSH:  rm ${PROJECT}/deploy/tat.env  即可" >&2
    exit 2
  fi
  echo "TAT → ${TAT_REGION} cmd=${TAT_COMMAND_ID} inst=${TAT_INSTANCE_ID}"
  tccli tat InvokeCommand \
    --region "$TAT_REGION" \
    --CommandId "$TAT_COMMAND_ID" \
    --InstanceIds "[\"${TAT_INSTANCE_ID}\"]" \
    --Parameters '{}'
}

# ---------------------------------------------------------------------------
# SSH 回退:开发期用 ~/.ssh/aba_tencent,临时可用 SSH_PASSWORD 覆盖
# ---------------------------------------------------------------------------
ssh_cmd() {
  local key="${HOME}/.ssh/aba_tencent"
  if [[ -n "${SSH_PASSWORD:-}" ]]; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o IdentitiesOnly=yes \
      -i "$key" "${REMOTE_USER}@${REMOTE_HOST}" "$1"
  else
    ssh -o StrictHostKeyChecking=no -o IdentitiesOnly=yes \
      -i "$key" "${REMOTE_USER}@${REMOTE_HOST}" "$1"
  fi
}

rsync_ssh() {  # args: <local-glob...> <remote-dir>
  local key="${HOME}/.ssh/aba_tencent"
  local rsh=(ssh -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -i "$key")
  rsync -az -e "${rsh[*]}" "$@"
}

deploy_via_ssh_api() {
  echo "--- [API/SSH] 同步源码 ---"
  rsync_ssh apps/api/app/ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/apps/api/app/"

  echo "--- [API/SSH] 重建镜像并重启 ---"
  ssh_cmd "cd ${REMOTE_DIR} && docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml build api 2>&1 | tail -3 && docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml up -d api 2>&1 | tail -3"
  echo "[API] 完成"
}

deploy_via_ssh_web() {
  deploy_via_ssh_build_and_upload_dist
  rsync_ssh apps/mobile-web/nginx.conf "${REMOTE_USER}@${REMOTE_HOST}:/tmp/aba-nginx.conf"
  echo "--- [Web/SSH] 复制到容器 + reload nginx ---"
  ssh_cmd "
    cd ${REMOTE_DIR} &&
    if ! docker ps --format '{{.Names}}' | grep -q '^aba-modern-web-1$'; then
      docker compose --project-name aba-modern --env-file deploy/modern.env -f deploy/docker-compose.modern.yml up -d web 2>&1 | tail -3
      sleep 2
    fi
    docker cp /tmp/aba-web-dist/. aba-modern-web-1:/usr/share/nginx/html/
    docker cp /tmp/aba-admin-dist/. aba-modern-web-1:/usr/share/nginx/html/admin/
    docker cp /tmp/aba-nginx.conf aba-modern-web-1:/etc/nginx/conf.d/default.conf
    docker exec aba-modern-web-1 nginx -t
    docker exec aba-modern-web-1 nginx -s reload
    echo '容器内文件验证:'
    echo '  mobile:'; docker exec aba-modern-web-1 sh -c 'wc -c /usr/share/nginx/html/assets/*.js'
    echo '  admin:' ; docker exec aba-modern-web-1 sh -c 'wc -c /usr/share/nginx/html/admin/assets/*.js'
  "
  verify_public_assets
}

deploy_via_ssh_sync_app() {
  rsync_ssh apps/api/app/ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/apps/api/app/"
}

deploy_via_ssh_upload_dist() {  # args: <mobile-dist> <admin-dist>
  rsync_ssh "$1/" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/aba-web-dist/"
  rsync_ssh "$2/" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/aba-admin-dist/"
}

deploy_via_ssh_build_and_upload_dist() {
  local MOBILE_DIST="${PROJECT}/apps/mobile-web/dist"
  local ADMIN_DIST="${PROJECT}/apps/admin-web/dist"
  echo "--- [Web:mobile] 本地 vite build ---"
  (cd "${PROJECT}/apps/mobile-web" && npx vite build 2>&1 | tail -5)
  echo "--- [Web:admin] 本地 vite build ---"
  (cd "${PROJECT}/apps/admin-web"  && npx vite build 2>&1 | tail -5)
  echo "--- [Web] rsync dist 到服务器 ---"
  rsync_ssh "${MOBILE_DIST}/" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/aba-web-dist/"
  rsync_ssh "${ADMIN_DIST}/"  "${REMOTE_USER}@${REMOTE_HOST}:/tmp/aba-admin-dist/"
}

verify_public_assets() {
  local MOBILE_DIST="${PROJECT}/apps/mobile-web/dist"
  local ADMIN_DIST="${PROJECT}/apps/admin-web/dist"
  local JS_NAME SZ
  JS_NAME=$(ls "${MOBILE_DIST}/assets/"*.js | xargs basename)
  SZ=$(curl -sI "http://${REMOTE_HOST}:8080/assets/${JS_NAME}" | grep -i content-length | awk '{print $2}' | tr -d '\r')
  echo "[Web:mobile] 外部访问验证: assets/${JS_NAME} = ${SZ} bytes"
  local ADMIN_JS ASZ
  ADMIN_JS=$(ls "${ADMIN_DIST}/assets/"*.js 2>/dev/null | xargs basename 2>/dev/null || echo "")
  if [[ -n "$ADMIN_JS" ]]; then
    ASZ=$(curl -sI "http://${REMOTE_HOST}:8080/admin/assets/${ADMIN_JS}" | grep -i content-length | awk '{print $2}' | tr -d '\r')
    echo "[Web:admin] 外部访问验证: admin/assets/${ADMIN_JS} = ${ASZ} bytes"
  fi
  if [[ "${SZ:-0}" -gt 10000 ]]; then
    echo "[Web] 部署成功 ✓"
  else
    echo "[Web] ⚠️ 文件大小异常,可能未正确更新!"
  fi
}

# ---------------------------------------------------------------------------
# 入口调度
# ---------------------------------------------------------------------------
pick_channel() {
  if load_tat_env; then echo "tat"
  else echo "ssh"; fi
}

CHANNEL="$(pick_channel)"
echo "通道: $CHANNEL  目标: $TARGET"

case "$CHANNEL" in
  tat)
    case "$TARGET" in
      api) deploy_via_tat_api ;;
      web) deploy_via_tat_web ;;
      all) deploy_via_tat_api; deploy_via_tat_web ;;
      *) echo "用法: $0 [api|web|all]"; exit 1 ;;
    esac ;;
  ssh)
    case "$TARGET" in
      api) deploy_via_ssh_api ;;
      web) deploy_via_ssh_web ;;
      all) deploy_via_ssh_api; deploy_via_ssh_web ;;
      *) echo "用法: $0 [api|web|all]"; exit 1 ;;
    esac ;;
esac

echo "=== 全部完成 ==="
