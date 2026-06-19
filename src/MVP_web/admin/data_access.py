"""
后台数据访问层（只读）

ABA 数据来源：memory.db（SQLite）
人生教练数据来源：data/users/{user_id}/coach_data.json
"""

import json
import os
import sqlite3
import traceback
from pathlib import Path
from typing import Dict, List, Optional


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict:
    return {k: row[k] for k in row.keys()}


def _parse_json_field(value: Optional[str]) -> Optional[Dict]:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


# ====================================
# ABA 数据（SQLite）
# ====================================

def list_users(db_path: Path) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                u.user_id, u.username, u.created_at, u.last_login, u.user_info,
                (SELECT COUNT(*) FROM conversations c WHERE c.user_id = u.user_id) AS conversation_count,
                (SELECT COUNT(*) FROM children ch WHERE ch.user_id = u.user_id) AS child_count,
                (SELECT COUNT(*) FROM reports r WHERE r.user_id = u.user_id) AS report_count
            FROM users u
            ORDER BY COALESCE(u.last_login, '') DESC
            """
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            """
            SELECT
                u.user_id, u.username, u.created_at, u.last_login, u.user_info,
                (SELECT COUNT(*) FROM conversations c WHERE c.user_id = u.user_id) AS conversation_count,
                (SELECT COUNT(*) FROM children ch WHERE ch.user_id = u.user_id) AS child_count,
                (SELECT COUNT(*) FROM reports r WHERE r.user_id = u.user_id) AS report_count
            FROM users u
            ORDER BY COALESCE(u.last_login, '') DESC
            """
        ).fetchall()
    finally:
        conn.close()

    result = []
    for row in rows:
        d = _row_to_dict(row)
        d["user_info"] = _parse_json_field(d.get("user_info"))
        result.append(d)
    return result


def get_user(db_path: Path, user_id: str) -> Optional[Dict]:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT user_id, username, created_at, last_login, user_info FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    d = _row_to_dict(row)
    d["user_info"] = _parse_json_field(d.get("user_info"))
    return d


def get_children(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM children WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_conversations(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, role, content, timestamp, is_extracted, metadata "
            "FROM conversations WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        d = _row_to_dict(r)
        d["metadata"] = _parse_json_field(d.get("metadata"))
        result.append(d)
    return result


def get_tasks(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_progress_logs(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM progress_logs WHERE user_id = ? ORDER BY log_date",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_reports(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_extracted_corpus(db_path: Path, user_id: str) -> List[Dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, corpus_type, content, source_conversation_id, created_at "
            "FROM extracted_corpus WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


# ====================================
# 人生教练数据（coach_data.json）
# ====================================

def _get_data_dir(db_path: Path) -> Path:
    return db_path.parent


def _load_coach_json(data_dir: Path, user_id: str) -> Optional[Dict]:
    path = data_dir / user_id / "coach_data.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
            d["_tasks_done_root"] = d.get("tasks_done", [])
            d["_emotion_done_root"] = d.get("emotion_tasks_done", [])
            for proj in d.get("growth_projects", []):
                proj["tasks_done"] = d.get("tasks_done", [])
            return d
    except Exception:
        return None


def get_coach_data(db_path: Path, user_id: str) -> Optional[Dict]:
    try:
        return _load_coach_json(_get_data_dir(db_path), user_id)
    except Exception:
        return None


def get_coach_summary(db_path: Path) -> Dict[str, Dict]:
    """返回所有用户的人生教练数据摘要，出错时返回空字典。"""
    try:
        data_dir = _get_data_dir(db_path)
        if not data_dir.exists():
            return {}
        summary = {}
        for uid_dir in data_dir.iterdir():
            if not uid_dir.is_dir():
                continue
            uid = uid_dir.name
            coach = _load_coach_json(data_dir, uid)
            if coach:
                summary[uid] = {
                    "mood_count": len(coach.get("mood_log", [])),
                    "records_count": len(coach.get("personal_records", [])),
                    "projects_count": len(coach.get("growth_projects", [])),
                    "journal_count": len(coach.get("journal_entries", [])),
                    "messages_count": len(coach.get("coach_messages", [])),
                }
        return summary
    except Exception:
        return {}


def collect_user_bundle(db_path: Path, user_id: str) -> Dict:
    user = get_user(db_path, user_id)
    if not user:
        raise ValueError(f"用户不存在: {user_id}")
    return {
        "user": user,
        "children": get_children(db_path, user_id),
        "conversations": get_conversations(db_path, user_id),
        "tasks": get_tasks(db_path, user_id),
        "progress_logs": get_progress_logs(db_path, user_id),
        "reports": get_reports(db_path, user_id),
        "extracted_corpus": get_extracted_corpus(db_path, user_id),
        "coach": get_coach_data(db_path, user_id),
    }


# ====================================
# 管理员删除用户
# ====================================

def delete_user_by_admin(db_path: Path, user_id: str) -> Dict:
    """管理员删除指定用户及其全部数据（含文件、向量索引）。

    Returns:
        {"success": bool, "message": str, "deleted": dict}
    """
    import shutil

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 先查用户是否存在
    row = cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": f"用户 {user_id} 不存在"}

    username = row[0]
    deleted = {}

    # 删除所有含 user_id 的表
    table_del_order = [
        ("conversations", "对话"),
        ("extracted_corpus", "提取语料"),
        ("children", "孩子档案"),
        ("progress_logs", "进展记录"),
        ("reports", "报告"),
        ("tasks", "训练任务"),
        ("user_quotas", "存储配额"),
        ("guardian_verification", "实名认证"),
        ("export_audit_log", "导出日志"),
        ("consent_tokens", "授权Token"),
    ]

    for table, label in table_del_order:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            deleted[label] = cursor.rowcount
        except sqlite3.OperationalError:
            deleted[label] = 0  # 表不存在则跳过

    # 最后删除用户记录
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    deleted["用户账户"] = cursor.rowcount

    conn.commit()
    conn.close()

    # 删除用户文件目录（coach_data.json、上传文件、向量索引等）
    data_dir = db_path.parent
    user_dir = data_dir / user_id
    dir_removed = False
    if user_dir.exists():
        try:
            shutil.rmtree(user_dir)
            dir_removed = True
        except Exception:
            pass

    total = sum(v for k, v in deleted.items() if k != "用户账户")

    return {
        "success": True,
        "message": f"已删除用户「{username}」({user_id[:8]}…)：共清理 {total} 条数据记录",
        "deleted": deleted,
        "dir_removed": dir_removed,
    }
