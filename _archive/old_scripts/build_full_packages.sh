#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/MVP_web"
DIST_DIR="$ROOT_DIR/dist"
MAC_NAME="ABA智能助手_macOS完整版_v1.0.0"
WIN_NAME="ABA智能助手_Windows完整版_v1.0.0"

make_base_package() {
    local package_dir="$1"

    rm -rf "$package_dir"
    mkdir -p "$package_dir/data/users" "$package_dir/data/chromadb" "$package_dir/logs"

    cp "$APP_DIR/app.py" "$package_dir/"
    cp "$APP_DIR/agent.py" "$package_dir/"
    cp "$APP_DIR/config.py" "$package_dir/"
    cp "$APP_DIR/knowledge_base.py" "$package_dir/"
    cp "$APP_DIR/safety.py" "$package_dir/"
    cp "$APP_DIR/deep_memory.py" "$package_dir/"
    cp "$APP_DIR/memory.py" "$package_dir/"
    cp "$APP_DIR/requirements.txt" "$package_dir/"
    cp "$APP_DIR/requirements-full.txt" "$package_dir/"
    cp "$APP_DIR/.env.example" "$package_dir/"
    cp "$APP_DIR/.env" "$package_dir/"
    cp "$APP_DIR/README.md" "$package_dir/README_轻量版说明.md"
    cp "$APP_DIR/README_FULL.md" "$package_dir/README.md"
    cp -R "$ROOT_DIR/知识库" "$package_dir/知识库"
}

zip_package() {
    local name="$1"
    (
        cd "$ROOT_DIR"
        python3 - <<PY
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

package_dir = Path("dist") / "$name"
zip_path = Path("dist") / "$name.zip"

with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(package_dir.rglob("*")):
        archive.write(path, path.relative_to("dist"))
PY
    )
}

mkdir -p "$DIST_DIR"

MAC_DIR="$DIST_DIR/$MAC_NAME"
make_base_package "$MAC_DIR"
cp "$APP_DIR/install_macos.sh" "$MAC_DIR/"
cp "$APP_DIR/start_macos.sh" "$MAC_DIR/"
cp -R "$DIST_DIR/wheelhouse_macos" "$MAC_DIR/wheelhouse"
chmod +x "$MAC_DIR/install_macos.sh" "$MAC_DIR/start_macos.sh"
find "$MAC_DIR" -name ".DS_Store" -delete
find "$MAC_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$MAC_DIR" -name "*.pyc" -delete
zip_package "$MAC_NAME"

WIN_DIR="$DIST_DIR/$WIN_NAME"
make_base_package "$WIN_DIR"
cp "$APP_DIR/install_windows.bat" "$WIN_DIR/"
cp "$APP_DIR/start_windows.bat" "$WIN_DIR/"
cp -R "$DIST_DIR/wheelhouse_windows_full" "$WIN_DIR/wheelhouse"
find "$WIN_DIR" -name ".DS_Store" -delete
find "$WIN_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$WIN_DIR" -name "*.pyc" -delete
zip_package "$WIN_NAME"

echo "已生成："
echo "$DIST_DIR/$MAC_NAME.zip"
echo "$DIST_DIR/$WIN_NAME.zip"
