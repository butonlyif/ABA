"""
训练数据记录模块 - ABA按试次数据记录
支持每次试次 +（正确）/ -（错误）/ P（辅助）记录
自动计算正确率，存储历史供图表展示
"""

import json
import os
import uuid
from datetime import datetime, date
from typing import List, Dict, Optional


# 默认存储路径（相对于src/MVP_web目录）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_DATA_DIR = os.path.join(_BASE_DIR, "data", "training")


def _user_file(user_id: str) -> str:
    os.makedirs(TRAINING_DATA_DIR, exist_ok=True)
    return os.path.join(TRAINING_DATA_DIR, f"{user_id}.json")


def _load(user_id: str) -> dict:
    path = _user_file(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": []}


def _save(user_id: str, data: dict):
    with open(_user_file(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── 公开 API ────────────────────────────────────────────────

def create_session(user_id: str, child_id: str, child_name: str,
                   skill_name: str, session_date: str = None,
                   task_id: str = None, skill_id: str = None) -> str:
    """新建一个训练 session，返回 session_id"""
    data = _load(user_id)
    session_id = str(uuid.uuid4())[:8]
    data["sessions"].append({
        "session_id": session_id,
        "child_id": child_id,
        "child_name": child_name,
        "skill_name": skill_name,
        "skill_id": skill_id,   # 课程技能id（可选）
        "task_id": task_id,     # 关联的任务id（可选）
        "date": session_date or date.today().isoformat(),
        "trials": [],           # 每个元素: "+" / "-" / "P"
        "created_at": datetime.now().isoformat(),
    })
    _save(user_id, data)
    return session_id


_VALID_TRIALS = ("+", "-", "P", "I", "V", "M", "E")

def _normalize(result: str) -> str:
    """兼容旧格式 (+/-/P) 和新格式 (I/V/M/P/E)"""
    mapping = {"+": "I", "-": "E"}
    return mapping.get(result, result)

def add_trial(user_id: str, session_id: str, result: str) -> dict:
    """添加一次试次结果，返回更新后的 session。
    新格式: I=独立正确, V=语言提示, M=示范, P=身体辅助, E=错误
    旧格式兼容: +=I, -=E, P=P"""
    result = _normalize(result)
    assert result in ("I", "V", "M", "P", "E"), f"无效结果: {result}"
    data = _load(user_id)
    for s in data["sessions"]:
        if s["session_id"] == session_id:
            s["trials"].append(result)
            _save(user_id, data)
            return _session_stats(s)
    raise ValueError(f"session {session_id} 不存在")


def delete_trial(user_id: str, session_id: str) -> dict:
    """撤销最后一次试次"""
    data = _load(user_id)
    for s in data["sessions"]:
        if s["session_id"] == session_id:
            if s["trials"]:
                s["trials"].pop()
            _save(user_id, data)
            return _session_stats(s)
    raise ValueError(f"session {session_id} 不存在")


def finish_session(user_id: str, session_id: str, notes: str = "") -> dict:
    """结束训练，保存备注，返回最终统计"""
    data = _load(user_id)
    for s in data["sessions"]:
        if s["session_id"] == session_id:
            s["notes"] = notes
            s["finished"] = True
            _save(user_id, data)
            return _session_stats(s)
    raise ValueError(f"session {session_id} 不存在")


def get_sessions(user_id: str, child_id: str = None,
                 skill_name: str = None, limit: int = 50) -> List[dict]:
    """获取历史 sessions（带统计），按时间倒序"""
    data = _load(user_id)
    sessions = data["sessions"]
    if child_id:
        sessions = [s for s in sessions if s.get("child_id") == child_id]
    if skill_name:
        sessions = [s for s in sessions if s.get("skill_name") == skill_name]
    sessions = sorted(sessions, key=lambda s: s.get("created_at", ""), reverse=True)
    return [_session_stats(s) for s in sessions[:limit]]


def get_skill_history(user_id: str, child_id: str, skill_name: str) -> List[dict]:
    """获取某技能的历史正确率序列，用于画趋势图"""
    sessions = get_sessions(user_id, child_id=child_id, skill_name=skill_name, limit=200)
    # 按日期正序
    sessions = sorted(sessions, key=lambda s: s.get("date", ""))
    return [
        {
            "date": s["date"],
            "percentage": s["percentage"],
            "total": s["total"],
            "session_id": s["session_id"],
        }
        for s in sessions
        if s["total"] > 0
    ]


def trained_today(user_id: str, child_id: str, skill_name: str) -> bool:
    """今天是否已有该技能的训练记录（含未完成的）"""
    today = date.today().isoformat()
    sessions = get_sessions(user_id, child_id=child_id, skill_name=skill_name, limit=20)
    return any(s["date"] == today for s in sessions)


def mastery_status(user_id: str, child_id: str, skill_name: str) -> dict:
    """
    返回该技能的掌握状态：
      mastered: 是否已达掌握（连续3次≥80%）
      streak:   当前连续达标次数（0-3）
      sessions_count: 总训练次数
    """
    history = get_skill_history(user_id, child_id, skill_name)
    if not history:
        return {"mastered": False, "streak": 0, "sessions_count": 0}
    pcts = [h["percentage"] for h in history]
    # 从最后往前数连续≥80%的次数
    streak = 0
    for p in reversed(pcts):
        if p >= 80:
            streak += 1
        else:
            break
    return {
        "mastered": streak >= 3,
        "streak": min(streak, 3),
        "sessions_count": len(pcts),
        "latest_pct": pcts[-1],
    }


def delete_session(user_id: str, session_id: str):
    data = _load(user_id)
    data["sessions"] = [s for s in data["sessions"] if s["session_id"] != session_id]
    _save(user_id, data)


# ─── 内部工具 ────────────────────────────────────────────────

def _session_stats(s: dict) -> dict:
    raw = s.get("trials", [])
    # 兼容旧格式
    trials = [_normalize(t) for t in raw]
    independent = trials.count("I")
    verbal = trials.count("V")
    model = trials.count("M")
    physical = trials.count("P")
    errors = trials.count("E")
    prompted = verbal + model + physical
    total = len(trials)
    # ABA正确率：只算独立正确
    pct = round(independent / total * 100) if total > 0 else 0
    return {
        **s,
        "trials": trials,          # 返回标准化后的序列
        "independent": independent,
        "verbal": verbal,
        "model": model,
        "physical": physical,
        "errors": errors,
        "correct": independent,    # 兼容旧字段
        "incorrect": errors,
        "prompted": prompted,
        "total": total,
        "percentage": pct,
    }
