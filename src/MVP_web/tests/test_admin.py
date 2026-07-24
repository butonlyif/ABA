"""
Admin Data Access 单元测试
"""
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataAccess:
    """数据访问层测试"""

    def setup_method(self):
        """每个测试前创建临时数据库"""
        from admin import data_access
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # 创建测试数据库
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                user_info TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                age TEXT,
                diagnosis TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_extracted INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT,
                content TEXT,
                created_at TEXT
            )
        """)

        # 插入测试数据
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
            ("user1", "testuser", "hash123", "2024-01-01", "2024-01-02", '{"child_name": "小明"}')
        )
        conn.execute(
            "INSERT INTO children VALUES (?, ?, ?, ?, ?, ?)",
            (1, "user1", "小明", "3岁", "自闭症", "2024-01-01")
        )
        conn.execute(
            "INSERT INTO conversations (id, user_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (1, "user1", "user", "你好", "2024-01-01")
        )
        conn.commit()
        conn.close()

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_users(self):
        """测试用户列表"""
        from admin.data_access import list_users

        users = list_users(self.db_path)
        assert len(users) == 1
        assert users[0]["username"] == "testuser"

    def test_get_user(self):
        """测试获取单个用户"""
        from admin.data_access import get_user

        user = get_user(self.db_path, "user1")
        assert user is not None
        assert user["username"] == "testuser"
        assert user["user_info"]["child_name"] == "小明"

    def test_get_user_not_found(self):
        """测试获取不存在的用户"""
        from admin.data_access import get_user

        user = get_user(self.db_path, "nonexistent")
        assert user is None

    def test_get_children(self):
        """测试获取孩子列表"""
        from admin.data_access import get_children

        children = get_children(self.db_path, "user1")
        assert len(children) == 1
        assert children[0]["name"] == "小明"

    def test_get_conversations(self):
        """测试获取对话历史"""
        from admin.data_access import get_conversations

        convos = get_conversations(self.db_path, "user1")
        assert len(convos) == 1
        assert convos[0]["content"] == "你好"

    def test_parse_json_field(self):
        """测试 JSON 字段解析"""
        from admin.data_access import _parse_json_field

        result = _parse_json_field('{"key": "value"}')
        assert result == {"key": "value"}

        result = _parse_json_field(None)
        assert result is None

        result = _parse_json_field("invalid json")
        assert result is None


class TestExporter:
    """导出功能测试"""

    def test_build_markdown(self):
        """测试 Markdown 导出构建"""
        from admin.exporter import build_markdown

        bundle = {
            "user": {
                "username": "testuser",
                "created_at": "2024-01-01",
                "last_login": "2024-01-02",
                "user_info": {"child_name": "小明", "age": "3岁"},
            },
            "children": [],
            "conversations": [
                {"role": "user", "content": "你好", "timestamp": "2024-01-01 10:00"},
            ],
            "reports": [],
        }

        result = build_markdown(bundle)
        assert "小明" in result
        assert "3岁" in result
        assert "你好" in result

    def test_export_user_writes_files(self):
        """测试 export_user 写出 md + json 文件"""
        import tempfile
        from admin.exporter import export_user

        bundle = {
            "user": {"user_id": "u1", "username": "testuser",
                     "created_at": "2024-01-01", "last_login": "", "user_info": {}},
            "children": [],
            "conversations": [],
            "reports": [],
        }
        out_root = Path(tempfile.mkdtemp())
        md_path, json_path = export_user(bundle, out_root)
        assert md_path.exists() and json_path.exists()

        parsed = json.loads(json_path.read_text(encoding="utf-8"))
        assert parsed["user"]["username"] == "testuser"

        import shutil
        shutil.rmtree(out_root, ignore_errors=True)
