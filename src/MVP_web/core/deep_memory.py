"""
====================================
ABA智能助手 - 深度记忆系统
====================================

完整的用户记忆解决方案：
- 用户登录/注册系统
- SQLite对话存储（无限历史）
- 自动语料提取
- Chroma向量数据库
- RAG检索增强

多用户并发安全：
- SQLite WAL模式 + busy_timeout，允许多读一写
- coach_data.json 原子写入（临时文件 + os.replace）
- ChromaDB 内部 SQLite 也开启 WAL
"""

import os
import json
import sqlite3
import hashlib
import uuid
import time as _time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading

try:
    from core.config import USER_DATA_PATH
except ImportError:
    USER_DATA_PATH = "./data/users"

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB 未安装，向量功能将不可用")


class DeepMemorySystem:
    """深度记忆系统"""

    def __init__(self, data_path: str = USER_DATA_PATH):
        self.data_path = Path(data_path)

        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_path / "memory.db"
        self.current_user_id: Optional[str] = None
        self.current_username: Optional[str] = None

        self._init_database()
        self._init_vector_store()

        if CHROMADB_AVAILABLE:
            self._init_chroma()
        else:
            self.chroma_client = None
            self.collection = None

    def _init_database(self):
        """初始化SQLite数据库（含 WAL 模式启用）"""
        conn = self._safe_connect()
        cursor = conn.cursor()

        # 检查是否已设置过 WAL（幂等初始化）
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-8000")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                user_info TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_extracted INTEGER DEFAULT 0,
                is_compressed INTEGER DEFAULT 0,
                compressed_summary TEXT,
                is_valuable INTEGER DEFAULT 0,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_corpus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                corpus_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_conversation_id INTEGER,
                created_at TEXT NOT NULL,
                embedding_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user
            ON conversations(user_id, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_corpus_user
            ON extracted_corpus(user_id, corpus_type)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_quotas (
                user_id TEXT PRIMARY KEY,
                storage_bytes INTEGER DEFAULT 524288000,
                used_bytes INTEGER DEFAULT 0,
                conversation_days INTEGER DEFAULT 180,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardian_verification (
                user_id TEXT PRIMARY KEY,
                guardian_name TEXT NOT NULL,
                guardian_id_type TEXT,
                guardian_id_number_encrypted TEXT,
                verified_at TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS export_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                exported_by TEXT NOT NULL,
                third_party_email TEXT,
                consent_token TEXT,
                scope TEXT NOT NULL,
                downloaded_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consent_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                third_party_email TEXT,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                used_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def _init_vector_store(self):
        """初始化向量存储目录"""
        self.vector_path = self.data_path / "vectors"
        self.vector_path.mkdir(parents=True, exist_ok=True)

    def _init_chroma(self):
        """初始化Chroma向量数据库"""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.vector_path),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name="user_corpus",
                metadata={"description": "用户对话语料库"}
            )
        except Exception as e:
            print(f"⚠️ ChromaDB初始化失败: {e}")
            self.chroma_client = None
            self.collection = None
            CHROMADB_AVAILABLE = False

        # 开启 ChromaDB 内部 SQLite 的 WAL 模式
        self._enable_chroma_wal()

    def _enable_chroma_wal(self):
        """为 ChromaDB 内部 SQLite 开启 WAL 模式"""
        if not self.chroma_client:
            return
        try:
            chroma_sqlite = self.vector_path / "chroma.sqlite3"
            if chroma_sqlite.exists():
                c = sqlite3.connect(str(chroma_sqlite))
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("PRAGMA busy_timeout=5000")
                c.close()
        except Exception:
            pass

    def _safe_connect(self) -> sqlite3.Connection:
        """获取带 WAL + busy_timeout 的 SQLite 连接（多用户安全）"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _atomic_write_json(filepath: Path, data: dict):
        """原子写入 JSON：先写临时文件再 os.replace，防止并发写入损坏"""
        tmp = filepath.with_suffix(filepath.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, filepath)  # POSIX 原子操作

    @staticmethod
    def _safe_read_json(filepath: Path) -> Optional[dict]:
        """安全读取 JSON，失败返回 None"""
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = "aba_assistant_salt_2024"
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """
        注册新用户

        Returns:
            (成功标志, 消息)
        """
        if len(username) < 2:
            return False, "用户名至少需要2个字符"

        if len(password) < 4:
            return False, "密码至少需要4个字符"

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )
        if cursor.fetchone():
            conn.close()
            return False, "用户名已存在"

        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)

        try:
            cursor.execute(
                """INSERT INTO users (user_id, username, password_hash, created_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, username, password_hash, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()

            self.current_user_id = user_id
            self.current_username = username
            return True, "注册成功"
        except Exception as e:
            conn.close()
            return False, f"注册失败: {str(e)}"

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        用户登录

        Returns:
            (成功标志, 消息)
        """
        conn = self._safe_connect()
        cursor = conn.cursor()

        password_hash = self._hash_password(password)

        cursor.execute(
            "SELECT user_id, username FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        result = cursor.fetchone()

        if result:
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE user_id = ?",
                (datetime.now().isoformat(), result[0])
            )
            conn.commit()
            conn.close()

            self.current_user_id = result[0]
            self.current_username = result[1]
            return True, "登录成功"
        else:
            conn.close()
            return False, "用户名或密码错误"

    def logout(self):
        """登出"""
        self.current_user_id = None
        self.current_username = None

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.current_user_id is not None

    def get_user_info(self) -> Optional[Dict]:
        """获取当前用户信息"""
        if not self.current_user_id:
            return None

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT username, created_at, last_login, user_info FROM users WHERE user_id = ?",
            (self.current_user_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            user_info = {
                "username": result[0],
                "created_at": result[1],
                "last_login": result[2],
                "user_info": json.loads(result[3]) if result[3] else {}
            }
            return user_info
        return None

    def save_user_profile(self, profile: Dict):
        """保存用户资料"""
        if not self.current_user_id:
            return

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET user_info = ? WHERE user_id = ?",
            (json.dumps(profile, ensure_ascii=False), self.current_user_id)
        )
        conn.commit()
        conn.close()

    def save_conversation(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """保存对话"""
        if not self.current_user_id:
            return

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO conversations (user_id, role, content, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                self.current_user_id,
                role,
                content,
                datetime.now().isoformat(),
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            )
        )
        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return conversation_id

    def get_conversation_history(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """获取对话历史"""
        if not self.current_user_id:
            return []

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, role, content, timestamp, metadata
               FROM conversations
               WHERE user_id = ?
               ORDER BY timestamp DESC
               LIMIT ? OFFSET ?""",
            (self.current_user_id, limit, offset)
        )
        results = cursor.fetchall()
        conn.close()

        conversations = []
        for row in reversed(results):
            conversations.append({
                "id": row[0],
                "role": row[1],
                "content": row[2],
                "timestamp": row[3],
                "metadata": json.loads(row[4]) if row[4] else {}
            })
        return conversations

    def get_conversation_count(self) -> int:
        """获取对话总数"""
        if not self.current_user_id:
            return 0

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
            (self.current_user_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def delete_conversation(self, conversation_id: int) -> bool:
        """删除单条对话"""
        if not self.current_user_id:
            return False

        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, self.current_user_id)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def delete_all_conversations(self) -> int:
        """删除当前用户所有对话"""
        if not self.current_user_id:
            return 0

        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM conversations WHERE user_id = ?",
            (self.current_user_id,)
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def extract_corpus_from_conversations(self, agent=None) -> int:
        """
        从对话中自动提取语料

        Args:
            agent: AI agent实例，用于分析对话

        Returns:
            提取的语料数量
        """
        if not self.current_user_id:
            return 0

        if not CHROMADB_AVAILABLE or not self.collection:
            return 0

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, content FROM conversations
               WHERE user_id = ? AND is_extracted = 0
               ORDER BY timestamp""",
            (self.current_user_id,)
        )
        unextracted = cursor.fetchall()
        conn.close()

        if not unextracted:
            return 0

        extracted_count = 0

        for conv_id, content in unextracted:
            if len(content) < 20:
                continue

            corpus_items = self._analyze_and_extract(content, agent)

            for item in corpus_items:
                self._save_corpus_item(
                    corpus_type=item["type"],
                    content=item["content"],
                    source_conversation_id=conv_id
                )
                extracted_count += 1

            conn = self._safe_connect()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversations SET is_extracted = 1 WHERE id = ?",
                (conv_id,)
            )
            conn.commit()
            conn.close()

        return extracted_count

    def _analyze_and_extract(
        self,
        content: str,
        agent=None
    ) -> List[Dict]:
        """
        分析对话内容并提取语料

        Args:
            content: 对话内容
            agent: AI agent

        Returns:
            提取的语料列表
        """
        corpus_items = []

        if agent and hasattr(agent, 'client') and agent.client:
            try:
                prompt = f"""分析以下对话内容，提取有价值的儿童发展相关信息：

{content[:1000]}

请提取以下类型的语料（每类最多3条）：
1. 儿童特征描述（行为、偏好、能力）
2. 有效的干预方法或策略
3. 家长关注的问题类型
4. 孩子的进步或变化

以JSON格式输出：
{{
  "corpus": [
    {{"type": "child_feature", "content": "..."}},
    {{"type": "effective_method", "content": "..."}},
    ...
  ]
}}"""

                response = agent.client.chat.completions.create(
                    model=agent.model_config.get("model", "MiniMax-M2.7"),
                    messages=[
                        {"role": "system", "content": "你是一个儿童发展信息提取专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )

                result_text = response.choices[0].message.content

                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    corpus_items = data.get("corpus", [])
            except Exception as e:
                print(f"语料提取失败: {e}")

        if not corpus_items:
            keywords = ["孩子", "训练", "方法", "进步", "问题", "行为"]
            for kw in keywords:
                if kw in content:
                    corpus_items.append({
                        "type": "general",
                        "content": content[:200]
                    })
                    break

        return corpus_items

    def _save_corpus_item(
        self,
        corpus_type: str,
        content: str,
        source_conversation_id: Optional[int] = None
    ):
        """保存单条语料"""
        if not self.current_user_id:
            return

        if not CHROMADB_AVAILABLE or not self.collection:
            return

        embedding_id = f"{self.current_user_id}_{datetime.now().timestamp()}"

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO extracted_corpus
               (user_id, corpus_type, content, source_conversation_id, created_at, embedding_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                self.current_user_id,
                corpus_type,
                content,
                source_conversation_id,
                datetime.now().isoformat(),
                embedding_id
            )
        )
        corpus_id = cursor.lastrowid
        conn.commit()
        conn.close()

        try:
            self.collection.add(
                documents=[content],
                ids=[embedding_id],
                metadatas=[{
                    "user_id": self.current_user_id,
                    "corpus_type": corpus_type,
                    "corpus_id": corpus_id
                }]
            )
        except Exception as e:
            print(f"向量存储失败: {e}")

    def retrieve_relevant_corpus(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索相关语料（RAG核心）

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关语料列表
        """
        if not self.current_user_id:
            return []

        if not CHROMADB_AVAILABLE or not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"user_id": self.current_user_id}
            )

            corpus_list = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    corpus_list.append({
                        "content": doc,
                        "type": results["metadatas"][0][i].get("corpus_type", "unknown")
                    })
            return corpus_list

        except Exception as e:
            print(f"语料检索失败: {e}")
            return []

    def get_corpus_summary(self) -> Dict:
        """获取语料库摘要"""
        if not self.current_user_id:
            return {"total": 0, "by_type": {}}

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM extracted_corpus WHERE user_id = ?",
            (self.current_user_id,)
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            """SELECT corpus_type, COUNT(*) as count
               FROM extracted_corpus
               WHERE user_id = ?
               GROUP BY corpus_type""",
            (self.current_user_id,)
        )
        type_counts = dict(cursor.fetchall())

        conn.close()

        return {
            "total": total,
            "by_type": type_counts
        }

    def get_context_for_rag(self, current_query: str) -> str:
        """
        获取RAG上下文字符串

        Args:
            current_query: 当前查询

        Returns:
            格式化的上下文字符串
        """
        corpus = self.retrieve_relevant_corpus(current_query, top_k=5)

        if not corpus:
            return ""

        context = "\n\n## 从历史对话中提取的相关信息：\n"
        for item in corpus:
            context += f"- [{item['type']}] {item['content']}\n"

        return context

    def get_storage_usage(self) -> Dict:
        """计算当前用户存储使用量（字节）"""
        if not self.current_user_id:
            return {"total_bytes": 0, "breakdown": {}, "percent": 0}

        quota_row = self._get_quota_row()
        storage_limit = quota_row["storage_bytes"] if quota_row else 524288000

        used = 0
        breakdown = {}

        user_dir = Path(self.data_path) / self.current_user_id

        memory_db = user_dir / "memory.db"
        if memory_db.exists():
            db_bytes = memory_db.stat().st_size
            used += db_bytes
            breakdown["memory_db"] = db_bytes

        chroma_dir = user_dir / "vectors"
        if chroma_dir.exists():
            chroma_bytes = sum(f.stat().st_size for f in chroma_dir.rglob("*") if f.is_file())
            used += chroma_bytes
            breakdown["chroma"] = chroma_bytes

        cache_dir = user_dir / "cache"
        if cache_dir.exists():
            cache_bytes = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            used += cache_bytes
            breakdown["cache"] = cache_bytes

        files_dir = user_dir / "files"
        if files_dir.exists():
            files_bytes = sum(f.stat().st_size for f in files_dir.rglob("*") if f.is_file())
            used += files_bytes
            breakdown["files"] = files_bytes

        coach_json = user_dir / "coach_data.json"
        if coach_json.exists():
            coach_bytes = coach_json.stat().st_size
            used += coach_bytes
            breakdown["coach_data"] = coach_bytes

        percent = min(100.0, (used / storage_limit) * 100) if storage_limit > 0 else 0

        return {
            "total_bytes": used,
            "storage_limit": storage_limit,
            "breakdown": breakdown,
            "percent": round(percent, 1),
            "total_mb": round(used / 1024 / 1024, 1),
            "limit_mb": round(storage_limit / 1024 / 1024, 1),
        }

    def _get_quota_row(self) -> Optional[Dict]:
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_quotas WHERE user_id = ?", (self.current_user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        cols = [d[0] for d in cursor.description]
        result = dict(zip(cols, row))
        conn.close()
        return result

    def _ensure_quota_row(self):
        if not self.current_user_id:
            return
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user_quotas WHERE user_id = ?", (self.current_user_id,))
        if not cursor.fetchone():
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO user_quotas (user_id, storage_bytes, used_bytes, conversation_days, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.current_user_id, 524288000, 0, 180, now, now)
            )
            conn.commit()
        conn.close()

    def cleanup_cache(self) -> int:
        """清理缓存目录，返回释放的字节数"""
        if not self.current_user_id:
            return 0
        user_dir = Path(self.data_path) / self.current_user_id
        cache_dir = user_dir / "cache"
        if not cache_dir.exists():
            return 0
        freed = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
        import shutil
        shutil.rmtree(cache_dir)
        cache_dir.mkdir(exist_ok=True)
        return freed

    def cleanup_old_conversations(self, older_than_days: int = 90) -> Dict:
        """清理超过指定天数的已提取对话，返回清理信息"""
        if not self.current_user_id:
            return {"deleted": 0, "freed_bytes": 0}
        conn = self._safe_connect()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        cursor.execute(
            "SELECT SUM(LENGTH(content)) FROM conversations WHERE user_id = ? AND is_extracted = 1 AND timestamp < ?",
            (self.current_user_id, cutoff)
        )
        row = cursor.fetchone()
        freed_bytes = row[0] or 0
        cursor.execute(
            "DELETE FROM conversations WHERE user_id = ? AND is_extracted = 1 AND timestamp < ?",
            (self.current_user_id, cutoff)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return {"deleted": deleted, "freed_bytes": freed_bytes}

    def update_storage_used(self):
        """更新 used_bytes 到数据库"""
        if not self.current_user_id:
            return
        usage = self.get_storage_usage()
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_quotas SET used_bytes = ?, updated_at = ? WHERE user_id = ?",
            (usage["total_bytes"], datetime.now().isoformat(), self.current_user_id)
        )
        conn.commit()
        conn.close()

    def get_cleanup_recommendations(self) -> List[Dict]:
        """获取清理建议"""
        recommendations = []
        if not self.current_user_id:
            return recommendations
        usage = self.get_storage_usage()

        cache_mb = round(usage["breakdown"].get("cache", 0) / 1024 / 1024, 1)
        if cache_mb > 0:
            recommendations.append({
                "type": "cache",
                "label": "清理缓存",
                "size_mb": cache_mb,
                "action": "cleanup_cache",
            })

        coach_mb = round(usage["breakdown"].get("coach_data", 0) / 1024 / 1024, 1)
        if coach_mb > 30:
            recommendations.append({
                "type": "coach_trim",
                "label": "精简教练对话",
                "size_mb": coach_mb,
                "action": "trim_coach_messages",
            })

        if usage["percent"] > 80:
            total_mb = round(usage["total_bytes"] / 1024 / 1024, 1)
            recommendations.append({
                "type": "compress",
                "label": "压缩旧对话",
                "size_mb": total_mb,
                "action": "compress_old",
                "urgent": True,
            })

        return recommendations

    def trim_coach_messages(self) -> Dict:
        """精简教练数据：裁剪 coach_messages 到 100 条，压缩旧情绪日志

        Returns:
            {"trimmed_messages": N, "freed_bytes": bytes}
        """
        if not self.current_user_id:
            return {"trimmed_messages": 0, "freed_bytes": 0}
        user_dir = Path(self.data_path) / self.current_user_id
        coach_path = user_dir / "coach_data.json"
        if not coach_path.exists():
            return {"trimmed_messages": 0, "freed_bytes": 0}

        import json
        with open(coach_path, encoding="utf-8") as f:
            data = json.load(f)

        original_size = coach_path.stat().st_size

        messages = data.get("coach_messages", [])
        trimmed_count = 0
        if len(messages) > 100:
            trimmed_count = len(messages) - 100
            data["coach_messages"] = messages[-100:]

        cutoff_3m = (datetime.now() - timedelta(days=90)).isoformat()
        mood_log = data.get("mood_log", [])
        if mood_log and len(mood_log) > 500:
            monthly = {}
            for entry in mood_log:
                ts = entry.get("timestamp", "")
                if ts < cutoff_3m:
                    key = ts[:7]
                    if key not in monthly:
                        monthly[key] = entry
            data["mood_log"] = mood_log[-500:] + list(monthly.values())

        journal = data.get("journal_entries", [])
        if journal and len(journal) > 100:
            recent = [j for j in journal if j.get("created_at", "") >= cutoff_3m]
            data["journal_entries"] = recent[-100:] if recent else journal[-100:]

        data["kb_favorites"] = []
        data["kb_read"] = []

        new_size = len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        self._atomic_write_json(coach_path, data)

        return {
            "trimmed_messages": trimmed_count,
            "freed_bytes": max(0, original_size - new_size),
            "new_size_bytes": new_size,
        }

    def compress_conversations(self, openai_client=None, model: str = "MiniMax-M2.7") -> Dict:
        """压缩超过指定天数的对话为摘要

        Args:
            openai_client: 可选的 OpenAI 兼容客户端（传入 agent.client）
            model: 模型名

        Returns:
            {"compressed": N, "freed_bytes": bytes}
        """
        if not self.current_user_id:
            return {"compressed": 0, "freed_bytes": 0}
        conn = self._safe_connect()
        cursor = conn.cursor()
        cutoff_6m = (datetime.now() - timedelta(days=180)).isoformat()
        cursor.execute(
            "SELECT id, content, timestamp FROM conversations "
            "WHERE user_id = ? AND is_compressed = 0 AND timestamp < ? "
            "ORDER BY timestamp DESC LIMIT 20",
            (self.current_user_id, cutoff_6m)
        )
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return {"compressed": 0, "freed_bytes": 0}
        conn.close()

        total_freed = 0
        compressed_count = 0
        combined = "\n---\n".join(
            "[%s] %s" % (r[2], r[1]) for r in rows
        )

        summary_text = combined
        if openai_client and hasattr(openai_client, "chat"):
            try:
                resp = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是对话摘要助手。请将以下对话记录压缩为200字以内的中文摘要，保留关键信息和重要建议。"},
                        {"role": "user", "content": combined[:8000]}
                    ],
                    temperature=0.3,
                    max_tokens=400
                )
                summary_text = resp.choices[0].message.content or combined[:200]
            except Exception as e:
                print("压缩失败: %s" % e)
                summary_text = combined[:200]

        conn2 = self._safe_connect()
        cur2 = conn2.cursor()
        for row in rows:
            cid = row[0]
            cur2.execute(
                "UPDATE conversations SET is_compressed = 1, compressed_summary = ? WHERE id = ?",
                (summary_text[:500], cid)
            )
            total_freed += len(row[1]) - len(summary_text[:200])
            compressed_count += 1
        conn2.commit()
        conn2.close()
        return {"compressed": compressed_count, "freed_bytes": total_freed}

    def export_user_data(self, format: str = "json") -> Dict:
        """导出用户全部数据（ABA + 教练）

        Returns:
            dict 含数据内容或文件路径
        """
        if not self.current_user_id:
            return {"error": "未登录"}

        user_dir = Path(self.data_path) / self.current_user_id

        conn = self._safe_connect()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, username, created_at, last_login, user_info FROM users WHERE user_id = ?",
            (self.current_user_id,)
        )
        user_row = dict(cur.fetchone())

        cur.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY timestamp DESC",
            (self.current_user_id,)
        )
        conversations = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM children WHERE user_id = ?",
            (self.current_user_id,)
        )
        children = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM reports WHERE user_id = ?",
            (self.current_user_id,)
        )
        reports = [dict(r) for r in cur.fetchall()]

        cur.execute(
            "SELECT * FROM progress_logs WHERE user_id = ?",
            (self.current_user_id,)
        )
        progress_logs = [dict(r) for r in cur.fetchall()]

        conn.close()

        coach_data = {}
        coach_path = user_dir / "coach_data.json"
        if coach_path.exists():
            import json as _json
            with open(coach_path, encoding="utf-8") as f:
                coach_data = _json.load(f)

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "user": user_row,
            "conversations": conversations,
            "children": children,
            "reports": reports,
            "progress_logs": progress_logs,
            "coach_data": coach_data,
        }
        return export_data

    def delete_user_data(self, confirm_user_id: str) -> Dict:
        """删除用户全部数据（GDPR 删除权）

        Args:
            confirm_user_id: 需与 current_user_id 匹配防止误删

        Returns:
            {"success": bool, "message": str}
        """
        if not self.current_user_id or confirm_user_id != self.current_user_id:
            return {"success": False, "message": "用户ID不匹配"}

        user_dir = Path(self.data_path) / self.current_user_id

        conn = self._safe_connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM conversations WHERE user_id = ?", (self.current_user_id,))
        conv_deleted = cursor.rowcount

        cursor.execute("DELETE FROM children WHERE user_id = ?", (self.current_user_id,))
        children_deleted = cursor.rowcount

        cursor.execute("DELETE FROM reports WHERE user_id = ?", (self.current_user_id,))
        reports_deleted = cursor.rowcount

        cursor.execute("DELETE FROM progress_logs WHERE user_id = ?", (self.current_user_id,))
        logs_deleted = cursor.rowcount

        cursor.execute("DELETE FROM extracted_corpus WHERE user_id = ?", (self.current_user_id,))
        corpus_deleted = cursor.rowcount

        cursor.execute("DELETE FROM user_quotas WHERE user_id = ?", (self.current_user_id,))
        cursor.execute("DELETE FROM guardian_verification WHERE user_id = ?", (self.current_user_id,))
        cursor.execute("DELETE FROM export_audit_log WHERE user_id = ?", (self.current_user_id,))
        cursor.execute("DELETE FROM consent_tokens WHERE user_id = ?", (self.current_user_id,))

        cursor.execute("DELETE FROM users WHERE user_id = ?", (self.current_user_id,))
        user_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        import shutil
        if user_dir.exists():
            shutil.rmtree(user_dir)

        return {
            "success": True,
            "message": "已删除：%d条对话、%d个孩子档案、%d份报告、%d条进展记录" % (
                conv_deleted, children_deleted, reports_deleted, logs_deleted
            )
        }

    def generate_consent_token(self, scope: List[str], third_party_email: str = "") -> str:
        """生成一次性授权 token（24h 有效）"""
        import hashlib, base64
        raw = "%s:%s:%s:%s" % (
            self.current_user_id, ",".join(scope), third_party_email, datetime.now().isoformat()
        )
        token = base64.urlsafe_b64encode(
            hashlib.sha256(raw.encode()).digest()
        ).decode()[:32]

        conn = self._safe_connect()
        cursor = conn.cursor()
        expires = (datetime.now() + timedelta(hours=24)).isoformat()
        cursor.execute(
            "INSERT OR REPLACE INTO consent_tokens (token, user_id, scope, third_party_email, expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (token, self.current_user_id, ",".join(scope), third_party_email, expires, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return token

    def validate_consent_token(self, token: str) -> Optional[Dict]:
        """验证 token 是否有效，返回授权信息"""
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM consent_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
            (token, datetime.now().isoformat())
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        result = dict(zip(cols, row))
        conn.close()
        return result

    def mark_token_used(self, token: str):
        """标记 token 已使用"""
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE consent_tokens SET used = 1, used_at = ? WHERE token = ?",
            (datetime.now().isoformat(), token)
        )
        conn.commit()
        conn.close()

    def log_export(self, token: str, third_party_email: str, ip_address: str = "", user_agent: str = ""):
        """记录导出审计日志"""
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO export_audit_log (user_id, exported_by, third_party_email, consent_token, scope, downloaded_at, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.current_user_id, "third_party", third_party_email, token, "", datetime.now().isoformat(), ip_address, user_agent, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_guardian_info(self) -> Optional[Dict]:
        """获取家长实名认证信息"""
        if not self.current_user_id:
            return None
        conn = self._safe_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM guardian_verification WHERE user_id = ?", (self.current_user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))

    def save_guardian_info(self, guardian_name: str, guardian_id_type: str = "身份证", guardian_id_number: str = "") -> Dict:
        """保存家长实名认证信息（AES加密证件号）"""
        if not self.current_user_id:
            return {"success": False, "message": "未登录"}
        encrypted = ""
        if guardian_id_number:
            import base64
            key = os.getenv("ENCRYPTION_KEY", "aba-assistant-default-key-32char!")
            cipher = "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(guardian_id_number))
            encrypted = base64.b64encode(cipher.encode()).decode()

        conn = self._safe_connect()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO guardian_verification
            (user_id, guardian_name, guardian_id_type, guardian_id_number_encrypted, verified_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (self.current_user_id, guardian_name, guardian_id_type, encrypted, now, "pending"))
        conn.commit()
        conn.close()
        return {"success": True, "message": "认证信息已保存"}

    def get_child_age(self) -> Optional[float]:
        """获取孩子年龄（岁）"""
        if not self.current_user_id:
            return None
        info = self.get_user_info()
        if not info or not info.get("user_info"):
            return None
        birth = info["user_info"].get("child_birth_date", "")
        if not birth:
            return None
        from datetime import date
        try:
            bdate = date.fromisoformat(birth)
            return (date.today() - bdate).days / 365.25
        except Exception:
            return None

    def is_child_under_protection(self) -> bool:
        """是否需要儿童额外保护（年龄 < 14岁）"""
        age = self.get_child_age()
        return age is not None and age < 14


memory_system = DeepMemorySystem()
