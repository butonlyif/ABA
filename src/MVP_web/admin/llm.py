"""
后台的 LLM 客户端薄封装。

不复用 ai_report_generator.AIReportGenerator 的私有方法，单独维护一份是因为：
1. 主 app 的报告是家长向，prompt 风格不同，绑在一起会互相牵制
2. 后台未来要做"专家批注 + 沉淀"这条路径，需要独立演化
3. 这层只有 ~50 行，重复成本远小于耦合成本

支持 MiniMax / OpenAI 两家，按环境变量自动选择。
"""

import os
from typing import Optional


class LLMUnavailable(RuntimeError):
    """LLM 配置不完整或调用失败"""


class AdminLLM:
    """后台专用 LLM 客户端。"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.environ.get("ABA_ADMIN_LLM", "minimax")
        self._client = None
        self._model = None
        self._init()

    def _init(self):
        if self.provider == "minimax":
            api_key = os.environ.get("MINIMAX_API_KEY")
            if not api_key:
                return
            base_url = os.environ.get(
                "MINIMAX_BASE_URL",
                "https://api.minimaxi.com/v1",
            )
            # MiniMax 兼容 OpenAI 的 SDK 协议
            try:
                from openai import OpenAI
            except ImportError as e:
                raise LLMUnavailable(f"openai SDK 未安装: {e}")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            self._model = os.environ.get("MINIMAX_MODEL", "abab6.5s-chat")

        elif self.provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return
            try:
                from openai import OpenAI
            except ImportError as e:
                raise LLMUnavailable(f"openai SDK 未安装: {e}")
            self._client = OpenAI(api_key=api_key)
            self._model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        else:
            raise LLMUnavailable(f"未知 provider: {self.provider}")

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete(self, prompt: str, system: Optional[str] = None, temperature: float = 0.6) -> str:
        if not self.available:
            raise LLMUnavailable(
                f"LLM 客户端未初始化。请检查环境变量："
                f"provider={self.provider}，需要 "
                f"{'MINIMAX_API_KEY' if self.provider == 'minimax' else 'OPENAI_API_KEY'}"
            )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content
