"""
ABA智能助手 - 跨平台启动入口

被打进 macOS / Windows 绿色包里，由平台启动器（.command / .bat / .app）调用。

职责：
1. 定位嵌入式 Python、应用目录、知识库、用户数据目录
2. 首次运行时复制 .env.example -> .env、创建 data/ 与 logs/
3. 用嵌入式 Python 启动 Streamlit（无窗口），自动打开浏览器
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


PORT = int(os.environ.get("ABA_PORT", "8501"))
COACH_PORT = int(os.environ.get("COACH_PORT", "8503"))


def package_root() -> Path:
    """返回打包目录（包含 runtime/ 与 app/ 的那个目录）"""
    here = Path(__file__).resolve().parent
    # 当本文件位于 runtime/ 时，root = runtime 的父目录
    if (here.parent / "app").is_dir():
        return here.parent
    # 否则按当前目录推断
    if (here / "app").is_dir():
        return here
    return here.parent


def find_embedded_python(root: Path) -> Path:
    """返回嵌入式 Python 可执行文件路径"""
    candidates = [
        root / "runtime" / "bin" / "python3.10",       # mac (python-build-standalone install_only)
        root / "runtime" / "bin" / "python3",
        root / "runtime" / "bin" / "python",
        root / "runtime" / "python.exe",               # win (python-build-standalone install_only) — strip-components=1 后
        root / "runtime" / "python" / "python.exe",    # 兜底（如果未来打包方式变了）
    ]
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError(f"未找到嵌入式 Python，已尝试：{[str(c) for c in candidates]}")


def ensure_first_run(root: Path) -> None:
    """首次运行准备：复制 env 模板、建数据目录"""
    env_file = root / ".env"
    # 优先使用可见模板 env.example.txt（不带点，普通用户能在 Finder/资源管理器看到）
    # 兼容旧 .env.example 命名
    templates = [root / "env.example.txt", root / ".env.example"]
    if not env_file.exists():
        for tpl in templates:
            if tpl.exists():
                shutil.copy(tpl, env_file)
                print(f"[首次启动] 已创建 {env_file}")
                print(f"[首次启动] 请用记事本/文本编辑器打开「{tpl.name}」编辑后，重命名为 .env；")
                print(f"           或直接编辑 .env（Mac: ⌘+Shift+. 显示隐藏文件；Win: 资源管理器「显示 → 隐藏的项目」）。\n")
                break

    (root / "data" / "users").mkdir(parents=True, exist_ok=True)
    (root / "data" / "chromadb").mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """轮询端口直到 Streamlit 监听上"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def main() -> int:
    root = package_root()
    app_dir = root / "app"
    entry = app_dir / "app_prototype.py"
    python = find_embedded_python(root)

    print("=" * 50)
    print(" ABA智能助手 v1.1.0  本地 Web 启动器")
    print("=" * 50)
    print(f" 包目录   : {root}")
    print(f" Python  : {python}")
    print(f" 入口    : {entry}")
    print(f" 端口    : {PORT}")
    print()

    if not entry.exists():
        print(f"[错误] 未找到主程序：{entry}")
        return 2

    ensure_first_run(root)

    # 关键依赖自检（chromadb 会把 onnxruntime 的 import 失败翻译成"未安装"，藏住真因）
    try:
        import onnxruntime  # noqa: F401
        print(f"[check] onnxruntime {onnxruntime.__version__} OK")
    except Exception as e:
        print()
        print("=" * 60)
        print("[ERROR] 加载 onnxruntime 失败：")
        print(f"  {type(e).__name__}: {e}")
        print()
        print("常见原因与修复：")
        print("  1) macOS Gatekeeper 隔离了 .dylib。在终端跑：")
        print(f'        xattr -cr "{root}"')
        print("     然后重新启动。")
        print("  2) 解压时文件不完整。删除整个包目录，重新解压 zip。")
        print("=" * 60)
        print()

    # 让 streamlit 能解析到应用代码
    env = os.environ.copy()
    pythonpath_extra = str(app_dir)
    env["PYTHONPATH"] = (
        pythonpath_extra + os.pathsep + env.get("PYTHONPATH", "")
    ).strip(os.pathsep)
    # 让用户数据 / 知识库相对路径解析到应用目录
    env["ABA_PACKAGE_ROOT"] = str(root)

    # 主应用与人生教练共享同一个 SSO 密钥，iframe 才能免密自动登录。
    # 单机绿色包通常没配 .env 密钥；这里临时生成一个注入两个子进程即可。
    if not env.get("COACH_SSO_SECRET"):
        import secrets
        env["COACH_SSO_SECRET"] = secrets.token_hex(32)

    def build_cmd(target, port):
        return [
            str(python), "-m", "streamlit", "run", str(target),
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
            "--browser.gatherUsageStats=false",
            "--global.developmentMode=false",
        ]

    print(f"[启动] 主应用 {entry} (:{PORT}) ...")
    proc = subprocess.Popen(build_cmd(entry, PORT), cwd=str(app_dir), env=env)

    # 同时拉起人生教练（8503），否则主应用里点「进入人生教练」会连不上
    coach_entry = app_dir / "life_coach_app.py"
    coach_proc = None
    if coach_entry.exists():
        print(f"[启动] 人生教练 {coach_entry} (:{COACH_PORT}) ...")
        coach_proc = subprocess.Popen(build_cmd(coach_entry, COACH_PORT), cwd=str(app_dir), env=env)
    else:
        print("[跳过] 未找到 life_coach_app.py，人生教练入口将不可用")

    def shutdown():
        for p in (coach_proc, proc):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()

    try:
        if wait_for_port("127.0.0.1", PORT, timeout=45):
            url = f"http://127.0.0.1:{PORT}"
            print(f"[就绪] 浏览器打开 {url}")
            try:
                webbrowser.open(url)
            except Exception:
                pass
        else:
            print("[警告] Streamlit 未在 45 秒内监听，请手动访问 http://127.0.0.1:%d" % PORT)
        rc = proc.wait()
        shutdown()
        return rc
    except KeyboardInterrupt:
        print("\n[退出] 收到 Ctrl+C，正在关闭…")
        shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())
