#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/MVP_web"
PACKAGE_NAME="ABA智能助手_v1.0.0"
DIST_DIR="$ROOT_DIR/dist"
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"

rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

copy_file() {
    cp "$APP_DIR/$1" "$PACKAGE_DIR/$1"
}

copy_file "app.py"
copy_file "agent.py"
copy_file "config.py"
copy_file "knowledge_base.py"
copy_file "safety.py"
copy_file "deep_memory.py"
copy_file "memory.py"
copy_file "requirements.txt"
copy_file "README.md"
copy_file ".env.example"
copy_file "start.sh"
copy_file "start.bat"

cp -R "$ROOT_DIR/知识库" "$PACKAGE_DIR/知识库"

mkdir -p "$PACKAGE_DIR/data/users"
mkdir -p "$PACKAGE_DIR/data/chromadb"
mkdir -p "$PACKAGE_DIR/logs"

find "$PACKAGE_DIR" -name ".DS_Store" -delete
find "$PACKAGE_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$PACKAGE_DIR" -name "*.pyc" -delete

chmod +x "$PACKAGE_DIR/start.sh"

(
    cd "$ROOT_DIR"
    python3 - <<PY
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

package_dir = Path("dist") / "$PACKAGE_NAME"
zip_path = Path("dist") / "$PACKAGE_NAME.zip"

with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(package_dir.rglob("*")):
        archive.write(path, path.relative_to("dist"))
PY
)

echo "客户安装包已生成：$DIST_DIR/$PACKAGE_NAME.zip"
echo "交付目录：$PACKAGE_DIR"
