#!/usr/bin/env bash
# ============================================================
# ABA 智能助手 - 一键同步代码 + 远程 rebuild
#
# 用法：
#   bash deploy/deploy.sh              # 默认：同步代码 + src/aba图片，重 build 所有 service
#   bash deploy/deploy.sh admin        # 只重 build aba-admin（主 app 不停机）
#   bash deploy/deploy.sh main         # 只重 build aba-assistant
#   bash deploy/deploy.sh images       # 只同步 src/aba图片（1.7GB，首次或图片更新时用）
#
# 环境变量（可选覆盖默认）：
#   SERVER_IP=xxx      默认 170.106.143.145
#   SERVER_USER=xxx    默认 ubuntu
#   REMOTE_DIR=xxx     默认 ~/AI_codex
#   SSH_KEY=/path/key  指定 SSH 私钥（默认用 ~/.ssh/ 下系统选择的）
#   SKIP_IMAGES=1      跳过 src/aba/图片 同步（图片未变时加速部署）
# ============================================================

# 故意不开 set -u：macOS 自带 bash 3.2 对空数组 "${arr[@]}" 不友好
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 敏感配置（SSH 密码 / 服务器 IP / SSO 密钥 / 公网地址）放在 deploy/deploy.env，
# 该文件不入库（见 .gitignore），由本脚本 source 并同步到服务器供 docker compose 插值。
# 首次使用：cp deploy/deploy.env.example deploy/deploy.env 并填入真实值。
DEPLOY_ENV="${SCRIPT_DIR}/deploy.env"
if [[ -f "$DEPLOY_ENV" ]]; then
    set -a; . "$DEPLOY_ENV"; set +a
fi

SERVER_IP="${SERVER_IP:-170.106.143.145}"
SERVER_USER="${SERVER_USER:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-~/AI_codex}"
SSH_KEY="${SSH_KEY:-}"
SSH_PASS="${SSH_PASS:-}"

if [[ -z "$SSH_PASS" && -z "$SSH_KEY" ]]; then
    echo "[错误] 未配置 SSH 凭证。请在 deploy/deploy.env 设置 SSH_PASS（或 SSH_KEY），"
    echo "       或临时用环境变量：SSH_PASS=xxx bash deploy/deploy.sh"
    echo "       参考模板：deploy/deploy.env.example"
    exit 1
fi

# SSH 免密码：通过 sshpass 自动输入密码，部署过程无需手动输入
CTRL_DIR="${HOME}/.ssh/control"
rm -rf "$CTRL_DIR"/* 2>/dev/null || true
mkdir -p "$CTRL_DIR" && chmod 700 "$CTRL_DIR"
MUX_OPTS=(-o "ControlMaster=auto" -o "ControlPath=${CTRL_DIR}/%r@%h:%p" -o "ControlPersist=10m")

SSH_OPTS=("${MUX_OPTS[@]}" -o "StrictHostKeyChecking=no")
RSYNC_SSH=("ssh" "${MUX_OPTS[@]}" -o "StrictHostKeyChecking=no")
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS+=("-i" "$SSH_KEY")
    RSYNC_SSH+=("-i" "$SSH_KEY")
fi

export SSHPASS="$SSH_PASS"

# 检查 sshpass 是否可用
if ! command -v sshpass &>/dev/null; then
    echo "[错误] 缺少 sshpass，请先安装：brew install sshpass"
    exit 1
fi

TARGET="${1:-all}"

echo ""
echo "==> 项目根: $PROJECT_ROOT"
echo "==> 目标服务器: ${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}"
echo "==> 重建目标: $TARGET"
echo ""

# ---------- 1. 同步代码 ----------
# 重要：
# - admin 后面不加斜杠（rsync 语义：拷贝目录本身而非内容）
# - 排除 __pycache__ / .DS_Store / data 等
# - 不同步 .env（避免本地空 .env 覆盖服务器的真实 key）

echo "==> [1/3] rsync src/MVP_web 代码（整个目录，含主 app + admin）..."
# 注意：source 后面的斜杠很关键——表示同步内容，而不是嵌套一层
# 不用 --delete：宁愿留点孤儿文件，也不要误删服务器上你手工放的东西
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
echo "==> 同步 src/tools（Dockerfile 构建时用 ingest_kb.py 预建 RAG 索引）..."
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "mkdir -p ${REMOTE_DIR}/src/tools"
sshpass -e rsync -av \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/src/tools/" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/src/tools/"

echo ""
echo "==> 同步开放版权图标卡（OpenMoji，体积小，始终同步）..."
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "mkdir -p ${REMOTE_DIR}/src/aba/图片卡_网络素材"
sshpass -e rsync -av \
    --exclude '.DS_Store' \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/src/aba/图片卡_网络素材/" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/src/aba/图片卡_网络素材/"

echo ""
echo "==> [2/4] rsync deploy 配置 + 知识库..."
# 注意：deploy.env 含密钥，仅通过 SSH 直传服务器，不入库。compose 用它做变量插值。
sshpass -e rsync -av \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/deploy/docker-compose.yml" \
    "$PROJECT_ROOT/deploy/Dockerfile" \
    "$DEPLOY_ENV" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/deploy/"

# .dockerignore 必须放在「构建上下文根」= REMOTE_DIR（compose 里 context: ..），不是 deploy/
sshpass -e rsync -av \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/.dockerignore" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/.dockerignore"

# 知识库源文件：Dockerfile 构建时 COPY 它并预建向量索引（含本地模型），故必须同步到构建上下文。
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "mkdir -p ${REMOTE_DIR}/docs/知识库"
sshpass -e rsync -av --delete \
    --exclude '.DS_Store' \
    -e "${RSYNC_SSH[*]}" \
    "$PROJECT_ROOT/docs/知识库/" \
    "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/docs/知识库/"

echo ""
# ---------- ABA 图片卡同步（可跳过）----------
# 首次部署或图片更新时必须跑；日常代码更新可 SKIP_IMAGES=1 跳过（省时间）
if [[ "${TARGET}" == "images" ]]; then
    echo "==> [3/4] rsync src/aba/图片（仅同步模式，不 rebuild）..."
    # 先确保远端目录存在且权限正确（中文路径 rsync 不会自动 mkdir）
    sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
        "mkdir -p ${REMOTE_DIR}/src/aba/图片"
    sshpass -e rsync -av --progress \
        --exclude '.DS_Store' \
        -e "${RSYNC_SSH[*]}" \
        "$PROJECT_ROOT/src/aba/图片/" \
        "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/src/aba/图片/"
    echo "==> 图片同步完成，退出。"
    exit 0
fi

if [[ "${SKIP_IMAGES:-0}" != "1" ]]; then
    echo "==> [3/4] rsync src/aba/图片（1.7GB，--checksum 跳过未变文件，首次较慢）..."
    echo "    如需跳过：SKIP_IMAGES=1 bash deploy/deploy.sh"
    # 先确保远端目录存在且权限正确（中文路径 rsync 不会自动 mkdir）
    sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
        "mkdir -p ${REMOTE_DIR}/src/aba/图片"
    sshpass -e rsync -a --checksum --progress \
        --exclude '.DS_Store' \
        -e "${RSYNC_SSH[*]}" \
        "$PROJECT_ROOT/src/aba/图片/" \
        "${SERVER_USER}@${SERVER_IP}:${REMOTE_DIR}/src/aba/图片/"
else
    echo "==> [3/4] 跳过 src/aba/图片 同步（SKIP_IMAGES=1）"
fi

echo ""
echo "==> [4/4] 远程 build + 启动..."

# compose 文件里用了 ${VAR:?} 插值，所有 compose 调用都要带 --env-file 读 deploy.env
COMPOSE="docker compose --env-file deploy/deploy.env -f deploy/docker-compose.yml"

# NO_CACHE=1 时强制无缓存重建镜像 + 强制重建容器（代码改了却没生效时用）
# 注意：admin/life-coach 复用 aba-assistant 镜像，所以镜像构建只针对 aba-assistant
case "$TARGET" in
    admin)  SVC="aba-admin" ;;
    main)   SVC="aba-assistant" ;;
    all|*)  SVC="" ;;
esac

if [[ "${NO_CACHE:-0}" == "1" ]]; then
    echo "==> NO_CACHE=1：无缓存重建镜像（aba-assistant）+ 强制重建容器..."
    REMOTE_CMD="cd ${REMOTE_DIR} && ${COMPOSE} build --no-cache aba-assistant && ${COMPOSE} up -d --force-recreate ${SVC}"
else
    REMOTE_CMD="cd ${REMOTE_DIR} && ${COMPOSE} up -d --build ${SVC}"
fi

sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" "$REMOTE_CMD"

echo ""
echo "==> 完成。容器状态："
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "cd ${REMOTE_DIR} && ${COMPOSE} ps"

# ---------- 三方校验：本地源码 / 服务器源码 / 容器内代码 ----------
# 精确定位“改了没生效”卡在哪一环：rsync 没送达，还是 Docker 构建缓存
echo ""
echo "==> 三方校验 app_prototype.py（本地 / 服务器源码 / 容器内）..."
LOCAL_MD5="$(md5 -q "$PROJECT_ROOT/src/MVP_web/app_prototype.py" 2>/dev/null \
    || md5sum "$PROJECT_ROOT/src/MVP_web/app_prototype.py" 2>/dev/null | awk '{print $1}')"
SRV_MD5="$(sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "md5sum ${REMOTE_DIR}/src/MVP_web/app_prototype.py 2>/dev/null | awk '{print \$1}'")"
CTR_MD5="$(sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "docker exec aba-assistant md5sum /app/src/MVP_web/app_prototype.py 2>/dev/null | awk '{print \$1}'")"
echo "    本地源码:   ${LOCAL_MD5:-?}"
echo "    服务器源码: ${SRV_MD5:-?}"
echo "    容器内代码: ${CTR_MD5:-?}"
if [[ -n "$LOCAL_MD5" && "$LOCAL_MD5" == "$SRV_MD5" && "$SRV_MD5" == "$CTR_MD5" ]]; then
    echo "    ✓ 三方一致：新代码已生效。浏览器硬刷新即可。"
elif [[ "$LOCAL_MD5" != "$SRV_MD5" ]]; then
    echo "    ✗ 本地≠服务器：rsync 未送达。检查 deploy.sh 第 [1/3] 步 rsync 是否报错/被排除。"
elif [[ "$SRV_MD5" != "$CTR_MD5" ]]; then
    echo "    ✗ 服务器源码已更新，但容器内仍是旧的：Docker 构建缓存。请无缓存重建："
    echo "        NO_CACHE=1 bash deploy/deploy.sh ${TARGET}"
fi

echo ""
echo "==> 清理旧 PNG 缓存（格式已改为 WebP，旧 .png 不再被读取，留着只占盘）..."
# 缓存文件由容器内 root 写入，宿主机 ubuntu 用户无权删除，必须在容器内删
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "docker exec aba-assistant sh -c 'find /app/src/MVP_web/data/flashcard_cache -name \"*.png\" -delete' 2>/dev/null || true"

echo "==> 预渲染图片卡缓存（PDF→WebP，dpi=150 渲染后压缩，单张约 1MB→30KB；已缓存的自动跳过）..."
# 缓存写入共享 data volume，主 app 与 admin 都能读到；只渲染未缓存的页
sshpass -e ssh "${SSH_OPTS[@]}" "${SERVER_USER}@${SERVER_IP}" \
    "cd ${REMOTE_DIR}/src/MVP_web && docker exec aba-assistant python utils/prerender_flashcards.py" || \
    echo "    （预渲染未成功，可稍后手动跑：docker exec aba-assistant python utils/prerender_flashcards.py）"

echo ""
echo "==> 后台访问：开 SSH 隧道后浏览器打开 http://127.0.0.1:8502"
echo "   bash deploy/tunnel.sh"
