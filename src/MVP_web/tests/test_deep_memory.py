"""
Deep Memory System 单元测试
"""
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import time

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDeepMemorySystem:
    """深度记忆系统测试"""

    def setup_method(self):
        """每个测试前初始化临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_path = Path(self.temp_dir) / "test_data"
        self.data_path.mkdir()

    def teardown_method(self):
        """清理临时文件"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directories(self):
        """测试初始化创建目录"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        assert self.data_path.exists()
        assert dms.db_path.exists()

    def test_user_registration(self):
        """测试用户注册"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))

        success, user_id = dms.register("testuser", "password123")
        assert success is True
        assert user_id is not None
        assert len(user_id) > 0

    def test_user_login(self):
        """测试用户登录"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))

        # 注册用户
        dms.register("testuser", "password123")

        # 登录
        success, user_id = dms.login("testuser", "password123")
        assert success is True
        assert dms.current_user_id is not None

    def test_user_login_wrong_password(self):
        """测试错误密码登录"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))

        # 注册用户
        dms.register("testuser", "password123")

        # 错误密码
        success, user_id = dms.login("testuser", "wrongpassword")
        assert success is False

    def test_save_conversation(self):
        """测试保存对话"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        dms.register("testuser", "password123")
        dms.login("testuser", "password123")

        conv_id = dms.save_conversation("user", "你好")
        assert conv_id is not None
        assert conv_id > 0

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        dms.register("testuser", "password123")
        dms.login("testuser", "password123")

        dms.save_conversation("user", "你好")
        dms.save_conversation("assistant", "你好呀")

        history = dms.get_conversation_history(limit=10)
        assert len(history) == 2
        assert history[0]["content"] == "你好"
        assert history[1]["content"] == "你好呀"

    def test_user_exists(self):
        """测试用户是否存在"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))

        # 不存在
        assert dms.user_exists("nonexistent") is False

        # 注册后存在
        dms.register("testuser", "password123")
        assert dms.user_exists("testuser") is True

    def test_update_user_info(self):
        """测试更新用户信息"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        dms.register("testuser", "password123")
        dms.login("testuser", "password123")

        new_info = {"child_name": "小明", "child_age": "3岁"}
        result = dms.update_user_info(new_info)
        assert result is True

        # 验证更新
        user_info = dms.get_user_info()
        assert user_info["child_name"] == "小明"

    def test_get_user_info_not_logged_in(self):
        """测试未登录时获取用户信息"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        user_info = dms.get_user_info()
        assert user_info is None


class TestSessionMemory:
    """会话记忆测试"""

    def test_session_memory_basic(self):
        """测试基本会话记忆"""
        from core.session_memory import SessionMemory

        memory = SessionMemory()
        memory.add_message("user", "你好")
        memory.add_message("assistant", "你好呀")

        history = memory.get_history()
        assert len(history) == 2

    def test_session_memory_limit(self):
        """测试会话记忆限制"""
        from core.session_memory import SessionMemory

        memory = SessionMemory(max_messages=3)

        for i in range(5):
            memory.add_message("user", f"消息{i}")

        history = memory.get_history()
        assert len(history) <= 3

    def test_session_memory_clear(self):
        """测试清空会话记忆"""
        from core.session_memory import SessionMemory

        memory = SessionMemory()
        memory.add_message("user", "你好")
        memory.clear()

        history = memory.get_history()
        assert len(history) == 0
