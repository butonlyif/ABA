"""Fail CI when secrets or private runtime databases enter version control."""

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PRIVATE_PREFIXES = (
    "src/MVP_web/data/users/",
    "src/MVP_web/data/training/",
    "deploy/data/",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return result.stdout.splitlines()


def main() -> None:
    failures: list[str] = []
    for relative in tracked_files():
        if relative.startswith(PRIVATE_PREFIXES):
            failures.append(f"受保护的运行时数据仍被 Git 跟踪: {relative}")
            continue
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if path.name.endswith(".example"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            failures.append(f"疑似密钥内容: {relative}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("安全预检通过：未发现被跟踪的客户运行数据或常见密钥。")


if __name__ == "__main__":
    main()
