#!/usr/bin/env bash
# ABA智能助手 - 一键构建 macOS + Windows 绿色包
# 在 macOS 终端中运行：bash release/build_release.sh
#
# 步骤：
#   1) 下载嵌入式 Python（mac arm64 + win x86_64）到 build_cache/
#   2) 用 dist/wheelhouse_* 离线安装 requirements.lock 到各自 runtime/
#   3) 拷贝 MVP_web/ 代码、知识库、模板到 build/<package>/app
#   4) 写启动器与说明
#   5) 压缩成 release/output/*.zip
#
# 选项：
#   VERSION=1.1.0  自定义版本号
#  SKIP_MAC=1
#   SKIP_WIN=1     只构 macOS

set -euo pipefail

# --- 路径 ---
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
APP_SRC="$ROOT/MVP_web"
KB_SRC="$ROOT/知识库"
CACHE="$HERE/build_cache"
BUILD="$HERE/build"
OUT="$HERE/output"

VERSION="${VERSION:-1.1.0}"
PYTHON_TAG="20260510"     # python-build-standalone release（如失效改为更新的 tag）
PYTHON_VER="3.10.20"      # 必须是 3.10.x，以匹配 wheelhouse 里的 cp310 平台轮

MAC_PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_TAG}/cpython-${PYTHON_VER}+${PYTHON_TAG}-aarch64-apple-darwin-install_only.tar.gz"
WIN_PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_TAG}/cpython-${PYTHON_VER}+${PYTHON_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz"

MAC_WHEELS="$ROOT/dist/wheelhouse_macos"
WIN_WHEELS="$ROOT/dist/wheelhouse_windows_full"

MAC_NAME="ABA智能助手_macOS_v${VERSION}"
WIN_NAME="ABA智能助手_Windows_v${VERSION}"

mkdir -p "$CACHE" "$BUILD" "$OUT"

log()   { printf "\033[1;34m[build]\033[0m %s\n" "$*"; }
warn()  { printf "\033[1;33m[warn ]\033[0m %s\n" "$*"; }
abort() { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

# --- 前置检查 ---
[ -d "$APP_SRC" ]    || abort "未找到应用源码: $APP_SRC"
[ -d "$KB_SRC" ]     || abort "未找到知识库: $KB_SRC"
[ -d "$MAC_WHEELS" ] || abort "未找到 macOS wheelhouse: $MAC_WHEELS"
[ -d "$WIN_WHEELS" ] || abort "未找到 Windows wheelhouse: $WIN_WHEELS"

command -v curl    >/dev/null || abort "需要 curl"
command -v tar     >/dev/null || abort "需要 tar"
command -v zip     >/dev/null || abort "需要 zip"
command -v python3 >/dev/null || abort "需要 python3（仅用于生成 requirements.lock）"

# --- 始终从 wheelhouse 实际文件名重新生成 lock，避免手写漂移 ---
log "从 wheelhouse 自动生成 requirements.lock"
python3 - <<PY > "$HERE/requirements.lock"
import os
def collect(d):
    s = set()
    for fn in os.listdir(d):
        if not fn.endswith(".whl"): continue
        base = fn[:-4]
        parts = base.split("-")
        if len(parts) >= 5:
            name = "-".join(parts[:-4]); ver = parts[-4]
        elif len(parts) == 4:
            name, ver = parts[0], parts[1]
        else:
            continue
        s.add((name, ver))
    return s

mac = collect("$MAC_WHEELS")
win = collect("$WIN_WHEELS")
print("# ABA智能助手 v$VERSION - 锁定依赖")
print("# 由 release/build_release.sh 在打包前自动从 wheelhouse 真实文件名生成。")
print("# 请勿手动编辑；如需升级依赖，请先更新 wheelhouse 再重新构建。")
print()
for n, v in sorted(mac & win): print(f"{n}=={v}")
for n, v in sorted(mac - win): print(f'{n}=={v}; sys_platform != "win32"')
for n, v in sorted(win - mac): print(f'{n}=={v}; sys_platform == "win32"')
PY
log "  lock 共 $(grep -cE '==' "$HERE/requirements.lock") 条"

# --- 下载缓存 ---
download() {
    local url="$1" out="$2"
    if [ -f "$out" ] && [ -s "$out" ]; then
        log "缓存命中：$(basename "$out")"
        return 0
    fi
    log "下载 $url"
    curl -fL --retry 3 --connect-timeout 30 -o "$out" "$url"
}

# --- 拷贝应用源码（白名单，避免误带 .env、__pycache__） ---
copy_app() {
    local dst="$1"
    mkdir -p "$dst"
    local files=(
        app_prototype.py
        agent.py
        config.py
        knowledge_base.py
        safety.py
        deep_memory.py
        deep_memory_extended.py
        report_generator.py
        ai_report_generator.py
        task_generator.py
        charts.py
        ui_styles.py
        budget_guard.py
        curriculum.py
        flashcards.py
        training_data.py
        assessment.py
        intervention.py
        life_coach_app.py
        coach_content.py
        coach_engine.py
        coach_styles.py
        requirements-full.txt
    )
    for f in "${files[@]}"; do
        if [ -f "$APP_SRC/$f" ]; then
            cp "$APP_SRC/$f" "$dst/$f"
        else
            warn "缺源文件: $f"
        fi
    done
    cp -R "$KB_SRC" "$dst/知识库"
    # 开放版权图标卡（OpenMoji，体积小，随包发；PDF 大图卡因体积单独分发）
    local img_cards="$ROOT/aba/图片卡_网络素材"
    if [ -d "$img_cards" ]; then
        mkdir -p "$dst/../aba"
        cp -R "$img_cards" "$dst/../aba/图片卡_网络素材"
    fi
    find "$dst" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -name "*.pyc" -delete 2>/dev/null || true
    find "$dst" -name ".DS_Store" -delete 2>/dev/null || true
}

# ================================================================
# macOS 包
# ================================================================
build_mac() {
    log "========== 构建 $MAC_NAME =========="
    local pkg="$BUILD/$MAC_NAME"
    rm -rf "$pkg"
    mkdir -p "$pkg/runtime" "$pkg/app" "$pkg/data/users" "$pkg/data/chromadb" "$pkg/logs"

    # 1) 解压嵌入式 Python
    local tar="$CACHE/cpython-${PYTHON_VER}-mac-arm64.tar.gz"
    download "$MAC_PY_URL" "$tar"
    log "解压 macOS Python 到 runtime/"
    tar -xzf "$tar" -C "$pkg/runtime" --strip-components=1
    local PY="$pkg/runtime/bin/python3.10"
    [ -x "$PY" ] || abort "嵌入 Python 解压后不可执行：$PY"

    # 2) 用嵌入 Python 离线安装依赖（注意：必须在 mac 上跑才能装平台轮）
    log "离线安装依赖到 runtime/"
    "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
    "$PY" -m pip install --upgrade --no-index --find-links "$MAC_WHEELS" pip setuptools wheel 2>/dev/null || \
        "$PY" -m pip install --upgrade pip setuptools wheel
    "$PY" -m pip install --no-index --find-links "$MAC_WHEELS" -r "$HERE/requirements.lock"

    # 3) 拷应用代码、知识库
    copy_app "$pkg/app"

    # 4) 启动器与模板
    cp "$HERE/runtime/bootstrap.py"            "$pkg/runtime/bootstrap.py"
    cp "$HERE/runtime/launcher_macos.command"  "$pkg/Start_ABA_Assistant.command"
    chmod +x "$pkg/Start_ABA_Assistant.command"
    cp "$HERE/templates/env.example.txt"       "$pkg/env.example.txt"
    cp "$HERE/templates/README_USER_macOS.md"  "$pkg/README.md"

    # 5) 压缩
    log "打包 zip…"
    (cd "$BUILD" && zip -qr "$OUT/${MAC_NAME}.zip" "$MAC_NAME")
    log "✅ macOS 包：$OUT/${MAC_NAME}.zip  ($(du -sh "$OUT/${MAC_NAME}.zip" | cut -f1))"
}

# ================================================================
# Windows 包  —— 在 mac 上"交叉构建"：用 host pip 把 win 平台轮装到 win 嵌入 Python 目录
# ================================================================
build_win() {
    log "========== 构建 $WIN_NAME =========="
    local pkg="$BUILD/$WIN_NAME"
    rm -rf "$pkg"
    mkdir -p "$pkg/runtime" "$pkg/app" "$pkg/data/users" "$pkg/data/chromadb" "$pkg/logs"

    # 1) 解压 Windows 嵌入 Python
    local tar="$CACHE/cpython-${PYTHON_VER}-win-x64.tar.gz"
    download "$WIN_PY_URL" "$tar"
    log "解压 Windows Python 到 runtime/"
    tar -xzf "$tar" -C "$pkg/runtime" --strip-components=1
    # python-build-standalone 在 windows 上的入口是 runtime/python.exe（不是 bin/）
    [ -f "$pkg/runtime/python.exe" ] || abort "Windows Python 解压目录异常"

    # 2) 把 wheel 直接 unzip 进 site-packages（跨平台稳）
    local SITE="$pkg/runtime/Lib/site-packages"
    mkdir -p "$SITE"
    log "把 Windows 平台 wheel 解到 site-packages/（共 $(ls "$WIN_WHEELS" | wc -l | tr -d ' ') 个）"
    local FAIL=0
    for whl in "$WIN_WHEELS"/*.whl; do
        # unzip 静默模式；wheel 实质就是 zip
        unzip -o -q "$whl" -d "$SITE" || FAIL=$((FAIL+1))
    done
    if [ "$FAIL" -gt 0 ]; then
        warn "$FAIL 个 wheel 解压时报错，建议构建后手动检查"
    fi
    # 写 .pth 让 pip 等命令能找到包
    echo "import site; site.addsitedir(r'./Lib/site-packages')" > "$pkg/runtime/usercustomize.py" || true

    # 3) 拷应用代码、知识库
    copy_app "$pkg/app"

    # 4) 启动器与模板
    cp "$HERE/runtime/bootstrap.py"             "$pkg/runtime/bootstrap.py"
    cp "$HERE/runtime/launcher_windows.bat"     "$pkg/Start_ABA_Assistant.bat"
    cp "$HERE/templates/env.example.txt"        "$pkg/env.example.txt"
    cp "$HERE/templates/README_USER_Windows.md" "$pkg/README.md"

    # Windows 要求 CRLF 行尾，否则部分老版本 cmd.exe 解析 .bat 出错
    # 不依赖 unix2dos，用 sed 就地转换
    sed -i '' -e 's/$/\r/' "$pkg/Start_ABA_Assistant.bat" 2>/dev/null || \
        sed -i -e 's/$/\r/' "$pkg/Start_ABA_Assistant.bat"

    # 5) 压缩
    log "打包 zip…"
    (cd "$BUILD" && zip -qr "$OUT/${WIN_NAME}.zip" "$WIN_NAME")
    log "✅ Windows 包：$OUT/${WIN_NAME}.zip  ($(du -sh "$OUT/${WIN_NAME}.zip" | cut -f1))"
}

main() {
    log "VERSION=$VERSION  PYTHON_VER=$PYTHON_VER  PYTHON_TAG=$PYTHON_TAG"
    [ "${SKIP_MAC:-}" = "1" ] || build_mac
    [ "${SKIP_WIN:-}" = "1" ] || build_win
    log ""
    log "全部完成。产物：$OUT"
    ls -lh "$OUT"
}

main "$@"
