#!/bin/bash
# ABA Assistant - macOS launcher
# Double-click to start. The Terminal window stays open as a log console.

set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PY="$HERE/runtime/bin/python3.10"
if [ ! -x "$PY" ]; then
    echo "[ERROR] Embedded Python not found: $PY"
    echo "Please re-extract the zip and try again."
    read -n1 -s -p "Press any key to exit..."
    exit 1
fi

# === Critical for unsigned bundles ===
# Strip Gatekeeper quarantine from EVERYTHING (recursive + per-file as backup)
# Without this, .dylib/.so loaded by Python will silently fail on first run.
if command -v xattr >/dev/null 2>&1; then
    echo "[setup] Clearing macOS quarantine attributes (first run can take ~10s)..."
    xattr -cr "$HERE" >/dev/null 2>&1 || true
    # Per-file fallback for stubborn cases (some macOS versions ignore -r on certain bundles)
    find "$HERE/runtime" -type f \( -name "*.dylib" -o -name "*.so" -o -perm -u+x \) \
        -exec xattr -d com.apple.quarantine {} >/dev/null 2>&1 \; || true
fi

"$PY" "$HERE/runtime/bootstrap.py"
RC=$?

if [ "$RC" -ne 0 ]; then
    echo ""
    echo "[Exit] code=$RC"
    read -n1 -s -p "Press any key to close..."
fi

exit "$RC"
