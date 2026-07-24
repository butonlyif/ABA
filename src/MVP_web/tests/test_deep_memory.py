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

    def test_user_uniqueness(self):
        """测试用户名唯一性（注册重名用户应失败）"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))

        # 首次注册成功
        success, msg = dms.register("testuser", "password123")
        assert success is True

        # 重名注册应失败
        success2, msg2 = dms.register("testuser", "password123")
        assert success2 is False

    def test_save_user_profile(self):
        """测试保存用户资料"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        dms.register("testuser", "password123")

        new_info = {"child_name": "小明", "child_age": "3岁"}
        dms.save_user_profile(new_info)

        # 验证更新（重新登录后读取）
        dms.login("testuser", "password123")
        user_info = dms.get_user_info()
        assert user_info["user_info"]["child_name"] == "小明"

    def test_get_user_info_not_logged_in(self):
        """测试未登录时获取用户信息"""
        from core.deep_memory import DeepMemorySystem

        dms = DeepMemorySystem(str(self.data_path))
        user_info = dms.get_user_info()
        assert user_info is None


# 注：原 TestSessionMemory 测试的是不存在的 SessionMemory 类。
# 实际实现 core/session_memory.py 是 _SessionMemoryProxy，依赖 streamlit.session_state，
# 无法在纯单元测试环境（无 Streamlit 运行上下文）中实例化，故移除该测试类。
# 会话隔离逻辑由集成测试（运行 app）覆盖。
