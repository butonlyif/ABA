"""
====================================
ABA智能助手 - API 预算兜底
====================================

防止 API Key 被刷爆的简单防御层：
- 按"自然日"计数所有 LLM 调用
- 超过阈值时抛出 BudgetExceededError，agent 层捕获并提示用户
- 计数文件落盘 data/api_counter.json，容器重启不丢

不做用户级配额（按需扩展），不做按 token 计费精确测量（按调用次数估算）。
阈值通过环境变量 DAILY_API_LIMIT 配置；未设置时默认 500。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

_LOCK = Lock()
# 本模块在 utils/ 子目录：data/ 在 MVP_web/ 根（上一级），故用 parent.parent。
_COUNTER_PATH = Path(__file__).parent.parent / "data" / "api_counter.json"


class BudgetExceededError(RuntimeError):
    """每日 API 调用预算已用尽。"""


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _load() -> dict:
    if not _COUNTER_PATH.exists():
        return {"date": _today(), "count": 0}
    try:
        with _COUNTER_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # 跨日自动归零
        if data.get("date") != _today():
            return {"date": _today(), "count": 0}
        return data
    except (json.JSONDecodeError, OSError):
        return {"date": _today(), "count": 0}


def _save(data: dict) -> None:
    _COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _COUNTER_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    tmp.replace(_COUNTER_PATH)


def daily_limit() -> int:
    try:
        return int(os.getenv("DAILY_API_LIMIT", "500"))
    except ValueError:
        return 500


def check_and_increment() -> None:
    """
    在每次 LLM 调用前调用。超额时抛 BudgetExceededError。
    """
    limit = daily_limit()
    with _LOCK:
        data = _load()
        if data["count"] >= limit:
            raise BudgetExceededError(
                f"今日 AI 调用次数已达上限（{limit} 次）。为保护服务稳定，请明日再试。"
            )
        data["count"] += 1
        _save(data)


def current_usage() -> dict:
    """供运维查看：今天用了多少。"""
    return _load()
