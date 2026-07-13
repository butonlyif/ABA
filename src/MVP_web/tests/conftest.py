"""
pytest 配置和共享 fixtures
"""
import sys
from pathlib import Path

# 确保 core 模块可以被导入
sys.path.insert(0, str(Path(__file__).parent.parent))
