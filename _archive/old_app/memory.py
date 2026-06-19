"""
====================================
ABA智能助手 - 记忆模块
====================================

负责管理用户和孩子的信息
支持记忆存储和读取
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    from config import (
        USER_DATA_PATH,
        MEMORY_FILE,
        MAX_HISTORY_MESSAGES,
        DEFAULT_USER
    )
except ImportError:
    USER_DATA_PATH = "./data/users"
    MEMORY_FILE = "memory.json"
    MAX_HISTORY_MESSAGES = 50
    DEFAULT_USER = {}


class MemoryManager:
    """记忆管理器"""
    
    def __init__(
        self,
        user_data_path: str = "./data/users",
        memory_file: str = "memory.json"
    ):
        """
        初始化记忆管理器
        
        Args:
            user_data_path: 用户数据存储路径
            memory_file: 记忆文件名
        """
        self.user_data_path = Path(user_data_path)
        self.memory_file = memory_file
        
        # 确保目录存在
        self.user_data_path.mkdir(parents=True, exist_ok=True)
        
        # 当前用户数据
        self.current_user = {}
        
        # 加载已有记忆
        self._load_memory()
    
    def _load_memory(self):
        """加载记忆"""
        memory_path = self.user_data_path / self.memory_file
        
        if memory_path.exists():
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_user = data
            except Exception as e:
                print(f"⚠️ 加载记忆失败: {e}")
                self.current_user = {}
        else:
            self.current_user = {}
    
    def _save_memory(self):
        """保存记忆"""
        memory_path = self.user_data_path / self.memory_file
        
        try:
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.current_user,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"⚠️ 保存记忆失败: {e}")
    
    def save_user_info(self, user_info: Dict):
        """
        保存用户信息
        
        Args:
            user_info: 用户信息字典
        """
        self.current_user = {
            **self.current_user,
            **user_info,
            "updated_at": datetime.now().isoformat()
        }
        self._save_memory()
    
    def get_user_info(self) -> Dict:
        """获取用户信息"""
        return self.current_user.copy()
    
    def get_child_info(self) -> Dict:
        """获取孩子信息"""
        child_keys = [
            "child_name",
            "child_age",
            "child_diagnosis",
            "intervention_goals",
            "child_strengths",
            "child_challenges"
        ]
        
        child_info = {
            k: v for k, v in self.current_user.items()
            if k in child_keys
        }
        
        return child_info
    
    def add_conversation_turn(
        self,
        user_message: str,
        ai_message: str,
        metadata: Optional[Dict] = None
    ):
        """
        添加一轮对话到记忆
        
        Args:
            user_message: 用户消息
            ai_message: AI回复
            metadata: 额外元数据
        """
        if "conversation_history" not in self.current_user:
            self.current_user["conversation_history"] = []
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "ai": ai_message
        }
        
        if metadata:
            turn["metadata"] = metadata
        
        self.current_user["conversation_history"].append(turn)
        
        # 限制历史长度
        if len(self.current_user["conversation_history"]) > MAX_HISTORY_MESSAGES:
            self.current_user["conversation_history"] = \
                self.current_user["conversation_history"][-MAX_HISTORY_MESSAGES:]
        
        self._save_memory()
    
    def get_conversation_context(
        self,
        max_turns: int = 5
    ) -> str:
        """
        获取对话上下文（格式化字符串）
        
        Args:
            max_turns: 最大轮数
            
        Returns:
            格式化的上下文字符串
        """
        history = self.current_user.get("conversation_history", [])
        
        if not history:
            return ""
        
        # 取最近的对话
        recent = history[-max_turns:]
        
        context = "\n\n## 最近的对话：\n"
        for turn in recent:
            context += f"家长：{turn['user']}\n"
            context += f"AI：{turn['ai'][:100]}...\n\n"
        
        return context
    
    def get_conversation_history(
        self,
        max_turns: int = 10
    ) -> List[Dict]:
        """
        获取对话历史
        
        Args:
            max_turns: 最大轮数
            
        Returns:
            对话历史列表
        """
        history = self.current_user.get("conversation_history", [])
        return history[-max_turns:]
    
    def extract_and_save_info(self, text: str):
        """
        从对话中提取信息并保存
        
        Args:
            text: 用户输入的文本
        """
        text_lower = text.lower()
        
        # 提取孩子年龄
        import re
        age_patterns = [
            r'(\d+)岁',
            r'孩子.*?(\d+)岁',
            r'儿子|女儿|孩子.*?(\d+)岁',
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, text)
            if match:
                age = match.group(1)
                if "child_age" not in self.current_user:
                    self.current_user["child_age"] = f"{age}岁"
                    self._save_memory()
                    break
        
        # 提取孩子姓名
        name_patterns = [
            r'叫(.+?)[,，\.。]',
            r'我家.*?叫(.+?)[,，\.。]',
            r'孩子.*?叫(.+?)[,，\.。]',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if len(name) <= 10 and "child_name" not in self.current_user:
                    self.current_user["child_name"] = name
                    self._save_memory()
                    break
        
        # 提取诊断信息
        diagnosis_keywords = {
            "自闭症": "自闭症谱系障碍",
            "ASD": "自闭症谱系障碍",
            "发育迟缓": "发育迟缓",
            "疑似": "疑似自闭症"
        }
        
        for keyword, diagnosis in diagnosis_keywords.items():
            if keyword in text_lower:
                if "child_diagnosis" not in self.current_user:
                    self.current_user["child_diagnosis"] = diagnosis
                    self._save_memory()
                    break
    
    def get_memory_summary(self) -> str:
        """
        获取记忆摘要
        
        Returns:
            格式化的记忆摘要
        """
        if not self.current_user:
            return "（暂无记忆）"
        
        summary_parts = []
        
        if self.current_user.get("child_name"):
            summary_parts.append(f"孩子：{self.current_user['child_name']}")
        
        if self.current_user.get("child_age"):
            summary_parts.append(f"年龄：{self.current_user['child_age']}")
        
        if self.current_user.get("child_diagnosis"):
            summary_parts.append(f"诊断：{self.current_user['child_diagnosis']}")
        
        if self.current_user.get("intervention_goals"):
            summary_parts.append(f"目标：{self.current_user['intervention_goals']}")
        
        return " | ".join(summary_parts) if summary_parts else "（基础信息）"
    
    def clear_memory(self):
        """清空记忆"""
        self.current_user = {}
        self._save_memory()
    
    def export_memory(self, filepath: str):
        """
        导出记忆到文件
        
        Args:
            filepath: 导出文件路径
        """
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    self.current_user,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"⚠️ 导出记忆失败: {e}")


# ====================================
# 用户档案类
# ====================================

class UserProfile:
    """用户档案"""
    
    def __init__(self, user_id: str, data: Optional[Dict] = None):
        """
        初始化用户档案
        
        Args:
            user_id: 用户ID
            data: 用户数据
        """
        self.user_id = user_id
        self.data = data or {}
    
    def update(self, key: str, value: any):
        """更新字段"""
        self.data[key] = value
        self.data["updated_at"] = datetime.now().isoformat()
    
    def get(self, key: str, default: any = None) -> any:
        """获取字段"""
        return self.data.get(key, default)
    
    def to_dict(self) -> Dict:
        """转为字典"""
        return self.data.copy()
    
    @classmethod
    def from_dict(cls, user_id: str, data: Dict) -> "UserProfile":
        """从字典创建"""
        return cls(user_id, data)


# ====================================
# 测试代码
# ====================================

if __name__ == "__main__":
    print("=" * 50)
    print("记忆管理器测试")
    print("=" * 50)
    
    # 创建测试用的记忆管理器
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    manager = MemoryManager(
        user_data_path=temp_dir,
        memory_file="test_memory.json"
    )
    
    # 测试保存用户信息
    print("\n1. 保存用户信息...")
    manager.save_user_info({
        "child_name": "小明",
        "child_age": "5岁",
        "child_diagnosis": "自闭症谱系障碍",
        "intervention_goals": "练习表达需求"
    })
    print("✅ 保存成功")
    
    # 测试获取用户信息
    print("\n2. 获取用户信息...")
    info = manager.get_user_info()
    print(f"用户信息: {info}")
    
    # 测试对话历史
    print("\n3. 添加对话历史...")
    manager.add_conversation_turn(
        "孩子2岁还不会说话",
        "这是语言发展的问题..."
    )
    manager.add_conversation_turn(
        "怎么教他说话",
        "可以从提要求开始..."
    )
    print("✅ 添加成功")
    
    # 测试获取上下文
    print("\n4. 获取对话上下文...")
    context = manager.get_conversation_context()
    print(context)
    
    # 测试记忆摘要
    print("\n5. 获取记忆摘要...")
    summary = manager.get_memory_summary()
    print(f"摘要: {summary}")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ 所有测试通过！")
