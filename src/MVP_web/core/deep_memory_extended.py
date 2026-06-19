"""
====================================
ABA智能助手 - 扩展记忆系统
====================================

在原有deep_memory基础上扩展：
- 孩子档案管理
- 进展记录
- 报告生成
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from core.deep_memory import DeepMemorySystem


class ChildProfileManager(DeepMemorySystem):
    """孩子档案管理器"""

    def __init__(self, data_path: str):
        super().__init__(data_path)
        self._init_tables()

    def _init_tables(self):
        """初始化扩展表"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS children (
                child_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                birth_date TEXT,
                diagnosis TEXT,
                diagnosis_date TEXT,
                intervention_goals TEXT,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                log_id TEXT PRIMARY KEY,
                child_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                log_date TEXT NOT NULL,
                category TEXT NOT NULL,
                metric_name TEXT,
                value TEXT,
                description TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (child_id) REFERENCES children(child_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                child_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                title TEXT,
                content TEXT,
                summary TEXT,
                period_start TEXT,
                period_end TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (child_id) REFERENCES children(child_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                child_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                task_description TEXT,
                category TEXT,
                is_auto_generated INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                feedback TEXT,
                feedback_date TEXT,
                feedback_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (child_id) REFERENCES children(child_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_children_user
            ON children(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_progress_child
            ON progress_logs(child_id, log_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_child
            ON reports(child_id, created_at)
        """)

        conn.commit()
        conn.close()

    def add_child(
        self,
        user_id: str,
        name: str,
        birth_date: Optional[str] = None,
        diagnosis: Optional[str] = None,
        diagnosis_date: Optional[str] = None,
        intervention_goals: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """添加孩子档案"""
        child_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = self._safe_connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO children
                   (child_id, user_id, name, birth_date, diagnosis, diagnosis_date,
                    intervention_goals, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (child_id, user_id, name, birth_date, diagnosis, diagnosis_date,
                 intervention_goals, notes, now, now)
            )
            conn.commit()
            conn.close()
            return True, "添加成功", child_id
        except Exception as e:
            conn.close()
            return False, f"添加失败: {str(e)}", None

    def update_child(
        self,
        child_id: str,
        user_id: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """更新孩子档案"""
        allowed_fields = [
            'name', 'birth_date', 'diagnosis', 'diagnosis_date',
            'intervention_goals', 'notes', 'status'
        ]

        update_fields = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                update_fields.append(f"{field} = ?")
                values.append(value)

        if not update_fields:
            return False, "没有需要更新的字段"

        update_fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(child_id)
        values.append(user_id)

        conn = self._safe_connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                f"""UPDATE children
                    SET {', '.join(update_fields)}
                    WHERE child_id = ? AND user_id = ?""",
                values
            )
            if cursor.rowcount == 0:
                conn.close()
                return False, "记录不存在或无权修改"
            conn.commit()
            conn.close()
            return True, "更新成功"
        except Exception as e:
            conn.close()
            return False, f"更新失败: {str(e)}"

    def get_children(self, user_id: str, status: str = 'active') -> List[Dict]:
        """获取用户的所有孩子档案"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT child_id, name, birth_date, diagnosis, diagnosis_date,
                    intervention_goals, notes, status, created_at, updated_at
               FROM children
               WHERE user_id = ? AND status = ?
               ORDER BY updated_at DESC""",
            (user_id, status)
        )

        rows = cursor.fetchall()
        conn.close()

        children = []
        for row in rows:
            children.append({
                "child_id": row[0],
                "name": row[1],
                "birth_date": row[2],
                "diagnosis": row[3],
                "diagnosis_date": row[4],
                "intervention_goals": row[5],
                "notes": row[6],
                "status": row[7],
                "created_at": row[8],
                "updated_at": row[9]
            })
        return children

    def get_child(self, child_id: str, user_id: str) -> Optional[Dict]:
        """获取单个孩子档案"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT child_id, name, birth_date, diagnosis, diagnosis_date,
                    intervention_goals, notes, status, created_at, updated_at
               FROM children
               WHERE child_id = ? AND user_id = ?""",
            (child_id, user_id)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "child_id": row[0],
                "name": row[1],
                "birth_date": row[2],
                "diagnosis": row[3],
                "diagnosis_date": row[4],
                "intervention_goals": row[5],
                "notes": row[6],
                "status": row[7],
                "created_at": row[8],
                "updated_at": row[9]
            }
        return None

    def delete_child(self, child_id: str, user_id: str) -> Tuple[bool, str]:
        """软删除孩子档案"""
        return self.update_child(child_id, user_id, status='deleted')

    def add_progress_log(
        self,
        child_id: str,
        user_id: str,
        log_date: str,
        category: str,
        metric_name: Optional[str] = None,
        value: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """添加进展记录"""
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = self._safe_connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO progress_logs
                   (log_id, child_id, user_id, log_date, category, metric_name,
                    value, description, tags, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, child_id, user_id, log_date, category, metric_name,
                 value, description, json.dumps(tags, ensure_ascii=False) if tags else None, now)
            )
            conn.commit()
            conn.close()
            return True, "添加成功", log_id
        except Exception as e:
            conn.close()
            return False, f"添加失败: {str(e)}", None

    def get_progress_logs(
        self,
        child_id: str,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取进展记录"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        query = """SELECT log_id, log_date, category, metric_name, value,
                          description, tags, created_at
                   FROM progress_logs
                   WHERE child_id = ? AND user_id = ?"""
        params = [child_id, user_id]

        if start_date:
            query += " AND log_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND log_date <= ?"
            params.append(end_date)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY log_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        logs = []
        for row in rows:
            logs.append({
                "log_id": row[0],
                "log_date": row[1],
                "category": row[2],
                "metric_name": row[3],
                "value": row[4],
                "description": row[5],
                "tags": json.loads(row[6]) if row[6] else [],
                "created_at": row[7]
            })
        return logs

    def delete_progress_log(self, log_id: str, user_id: str) -> Tuple[bool, str]:
        """删除进展记录"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT log_id FROM progress_logs WHERE log_id = ? AND user_id = ?",
            (log_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            return False, "记录不存在"

        cursor.execute(
            "DELETE FROM progress_logs WHERE log_id = ? AND user_id = ?",
            (log_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "删除成功"

    def get_progress_summary(
        self,
        child_id: str,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取进展摘要"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        query = """SELECT category, COUNT(*) as count FROM progress_logs
                   WHERE child_id = ? AND user_id = ?"""
        params = [child_id, user_id]

        if start_date:
            query += " AND log_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND log_date <= ?"
            params.append(end_date)

        query += " GROUP BY category"

        cursor.execute(query, params)
        category_counts = dict(cursor.fetchall())

        cursor.execute(
            """SELECT COUNT(*) FROM progress_logs
               WHERE child_id = ? AND user_id = ?""",
            (child_id, user_id)
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            """SELECT log_date FROM progress_logs
               WHERE child_id = ? AND user_id = ?
               ORDER BY log_date DESC LIMIT 1""",
            (child_id, user_id)
        )
        last_log = cursor.fetchone()
        last_log_date = last_log[0] if last_log else None

        conn.close()

        return {
            "total_logs": total,
            "by_category": category_counts,
            "last_log_date": last_log_date
        }

    def save_report(
        self,
        child_id: str,
        user_id: str,
        report_type: str,
        title: str,
        content: str,
        summary: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """保存报告"""
        report_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = self._safe_connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO reports
                   (report_id, child_id, user_id, report_type, title, content,
                    summary, period_start, period_end, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (report_id, child_id, user_id, report_type, title, content,
                 summary, period_start, period_end, now)
            )
            conn.commit()
            conn.close()
            return True, "保存成功", report_id
        except Exception as e:
            conn.close()
            return False, f"保存失败: {str(e)}", None

    def get_reports(
        self,
        child_id: str,
        user_id: str,
        report_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取报告列表"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        query = """SELECT report_id, report_type, title, summary, period_start,
                          period_end, created_at
                   FROM reports
                   WHERE child_id = ? AND user_id = ?"""
        params = [child_id, user_id]

        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        reports = []
        for row in rows:
            reports.append({
                "report_id": row[0],
                "report_type": row[1],
                "title": row[2],
                "summary": row[3],
                "period_start": row[4],
                "period_end": row[5],
                "created_at": row[6]
            })
        return reports

    def get_report_content(self, report_id: str, user_id: str) -> Optional[Dict]:
        """获取报告详情"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT report_id, child_id, report_type, title, content, summary,
                    period_start, period_end, created_at
               FROM reports
               WHERE report_id = ? AND user_id = ?""",
            (report_id, user_id)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "report_id": row[0],
                "child_id": row[1],
                "report_type": row[2],
                "title": row[3],
                "content": row[4],
                "summary": row[5],
                "period_start": row[6],
                "period_end": row[7],
                "created_at": row[8]
            }
        return None

    def delete_report(self, report_id: str, user_id: str) -> Tuple[bool, str]:
        """删除报告"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT report_id FROM reports WHERE report_id = ? AND user_id = ?",
            (report_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            return False, "报告不存在"

        cursor.execute(
            "DELETE FROM reports WHERE report_id = ? AND user_id = ?",
            (report_id, user_id)
        )
        conn.commit()
        conn.close()
        return True, "删除成功"

    def add_task(
        self,
        child_id: str,
        user_id: str,
        task_name: str,
        task_description: Optional[str] = None,
        category: Optional[str] = None,
        is_auto_generated: bool = False
    ) -> Tuple[bool, str, Optional[str]]:
        """添加任务"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = self._safe_connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO tasks (task_id, child_id, user_id, task_name, task_description,
                                  category, is_auto_generated, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (task_id, child_id, user_id, task_name, task_description,
                  category, 1 if is_auto_generated else 0, now, now))
            conn.commit()
            conn.close()
            return True, "任务添加成功", task_id
        except Exception as e:
            conn.close()
            return False, str(e), None

    def get_tasks(
        self,
        child_id: str,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取任务列表"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        query = """SELECT task_id, task_name, task_description, category, is_auto_generated,
                          status, feedback, feedback_date, feedback_note, created_at, updated_at
                   FROM tasks WHERE child_id = ? AND user_id = ?"""
        params = [child_id, user_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row[0],
                "task_name": row[1],
                "task_description": row[2],
                "category": row[3],
                "is_auto_generated": bool(row[4]),
                "status": row[5],
                "feedback": row[6],
                "feedback_date": row[7],
                "feedback_note": row[8],
                "created_at": row[9],
                "updated_at": row[10]
            })
        return tasks

    def update_task_feedback(
        self,
        task_id: str,
        user_id: str,
        status: str,
        feedback: Optional[str] = None,
        feedback_note: Optional[str] = None
    ) -> Tuple[bool, str]:
        """更新任务反馈"""
        now = datetime.now().isoformat()

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT task_id FROM tasks WHERE task_id = ? AND user_id = ?",
            (task_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            return False, "任务不存在"

        cursor.execute("""
            UPDATE tasks
            SET status = ?, feedback = ?, feedback_date = ?, feedback_note = ?, updated_at = ?
            WHERE task_id = ? AND user_id = ?
        """, (status, feedback, now, feedback_note, now, task_id, user_id))

        conn.commit()
        conn.close()
        return True, "反馈已更新"

    def delete_task(self, task_id: str, user_id: str) -> Tuple[bool, str]:
        """删除任务"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT task_id FROM tasks WHERE task_id = ? AND user_id = ?",
            (task_id, user_id)
        )
        if not cursor.fetchone():
            conn.close()
            return False, "任务不存在"

        cursor.execute("DELETE FROM tasks WHERE task_id = ? AND user_id = ?",
                      (task_id, user_id))
        conn.commit()
        conn.close()
        return True, "删除成功"

    def get_conversation_stats(
        self,
        child_id: str,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取对话统计（按孩子）"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        query = """SELECT
                      COUNT(*) as total,
                      SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_msgs,
                      SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_msgs
                   FROM conversations c
                   WHERE c.user_id = ?
                   AND EXISTS (SELECT 1 FROM children ch WHERE ch.child_id = ? AND ch.user_id = c.user_id)"""
        params = [user_id, child_id]

        if start_date:
            query += " AND c.timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND c.timestamp <= ?"
            params.append(end_date)

        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        return {
            "total": row[0] or 0,
            "user_messages": row[1] or 0,
            "assistant_messages": row[2] or 0
        }
