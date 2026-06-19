"""
====================================
ABA智能助手 - Agent模块
====================================

负责AI对话和响应生成
支持多种AI模型和工具调用
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

try:
    from core.config import (
        SYSTEM_PROMPT, AI_MODELS, RETRIEVAL_TOP_K, RETRIEVAL_CANDIDATE_K,
        SAFETY_LEVEL_LOW, SAFETY_LEVEL_EMERGENCY, SAFETY_LEVEL_HIGH,
        ENABLE_LLM_RERANK, RETRIEVAL_SCORE_THRESHOLD, EMERGENCY_PROMPT
    )
except ImportError:
    SYSTEM_PROMPT = ""
    AI_MODELS = {}
    RETRIEVAL_TOP_K = 5
    RETRIEVAL_CANDIDATE_K = 16
    ENABLE_LLM_RERANK = True
    RETRIEVAL_SCORE_THRESHOLD = 0.5

# 部署到公网时启用的每日总调用预算兜底（防 API Key 被刷爆）。
# 本地运行不受影响：只在到达阈值时抛错。
try:
    from utils.budget_guard import check_and_increment, BudgetExceededError
except ImportError:
    def check_and_increment():  # type: ignore
        pass
    class BudgetExceededError(RuntimeError):  # type: ignore
        pass


def search_web(query: str) -> str:
    """
    搜索网络获取信息
    优先使用Google，Google不可用时使用Bing

    Args:
        query: 搜索关键词

    Returns:
        搜索结果的摘要文本
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 首先尝试 Google
    google_result = _google_search(query, headers)
    if google_result:
        return google_result

    # Google 不可用时使用 Bing
    print("Google 不可用，使用 Bing 搜索...")
    return _bing_search(query, headers)


def _google_search(query: str, headers: dict) -> str:
    """使用 Google 搜索"""
    try:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=8)

        if response.status_code != 200:
            return ""

        content = response.text

        # Google 搜索结果解析
        title_pattern = r'<h3[^>]*class="[^"]*"[^>]*>([^<]+)</h3>'
        titles = re.findall(title_pattern, content)

        link_pattern = r'<h3[^>]*class="[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>'
        links = re.findall(link_pattern, content, re.DOTALL)

        if titles and len(titles) > 0:
            result_text = f"## 搜索结果：{query}\n\n"
            for i, (title, link) in enumerate(zip(titles[:5], links[:5])):
                clean_title = re.sub(r'<[^>]+>', '', title)
                clean_link = link.split('&')[0] if link else ''
                if clean_title and len(clean_title) > 5:
                    result_text += f"**{i+1}. {clean_title}**\n"
                    result_text += f"来源：{clean_link}\n\n"
            result_text += "\n---\n*搜索结果来源：Google*\n"
            return result_text[:1500]

        return None

    except Exception as e:
        print(f"Google 搜索失败: {e}")
        return None


def _bing_search(query: str, headers: dict) -> str:
    """使用 Bing 搜索"""
    try:
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return ""

        content = response.text

        titles = re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL)

        if titles:
            result_text = f"## 网络搜索结果：{query}\n\n"
            count = 0
            for title in titles:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                clean_title = re.sub(r'&amp;', '&', clean_title)
                clean_title = re.sub(r'&lt;', '<', clean_title)
                clean_title = re.sub(r'&gt;', '>', clean_title)
                clean_title = re.sub(r'&quot;', '"', clean_title)
                clean_title = re.sub(r'&#\d+;', '', clean_title)
                if clean_title and len(clean_title) > 5 and 'Next' not in clean_title and 'Feedback' not in clean_title:
                    count += 1
                    result_text += f"{count}. {clean_title}\n"
                    if count >= 8:
                        break
            if count > 0:
                result_text += "\n---\n*搜索结果来源：Bing*\n"
                return result_text[:2000]

        snippet_pattern = r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>'
        snippets = re.findall(snippet_pattern, content, re.DOTALL)
        if snippets:
            result_text = f"## 网络搜索结果：{query}\n\n"
            for i, s in enumerate(snippets[:5]):
                clean = re.sub(r'<[^>]+>', '', s).strip()[:300]
                if clean:
                    result_text += f"{i+1}. {clean}\n\n"
            result_text += "\n---\n*搜索结果来源：Bing*\n"
            return result_text[:2000]

        return ""

    except Exception as e:
        print(f"Bing 搜索失败: {e}")
        return ""


# 可用的工具定义
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "全网信息检索功能。当用户询问的问题超出知识库范围，或需要最新信息时使用此工具搜索相关网页内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，应该是简洁的搜索查询"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


class ABAAgent:
    """ABA智能助手Agent"""

    def __init__(
        self,
        knowledge_base=None,
        model_name: str = "minimax"
    ):
        """
        初始化Agent

        Args:
            knowledge_base: 知识库实例
            model_name: 使用的模型名称
        """
        self.knowledge_base = knowledge_base
        self.model_name = model_name
        self.model_config = AI_MODELS.get(model_name, AI_MODELS.get("minimax"))
        self.conversation_history = []

        # 工具函数映射
        self.tool_functions = {
            "search_web": search_web
        }

        # 初始化AI客户端
        self._init_client()

    def _init_client(self):
        """初始化AI客户端"""
        self.client = None

        provider = self.model_config.get("provider", "")

        try:
            if provider == "openai":
                api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY")
                if api_key:
                    from openai import OpenAI
                    base_url = self.model_config.get("base_url", "https://api.minimaxi.com/v1")
                    self.client = OpenAI(api_key=api_key, base_url=base_url)
                    self._use_openai_compatible = True

            elif provider == "anthropic":
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.client = Anthropic(api_key=api_key)

            elif provider == "volcengine":
                api_key = os.getenv("DOUBAO_API_KEY")
                if api_key:
                    from openai import OpenAI
                    self.client = OpenAI(
                        api_key=api_key,
                        base_url=self.model_config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
                    )
                    self._use_openai_compatible = True

            else:
                print(f"⚠️ 不支持的AI提供商: {provider}")

        except Exception as e:
            print(f"⚠️ AI客户端初始化失败: {e}")

    def generate_response(
        self,
        user_input: str,
        context: Dict,
        safety_level: int = SAFETY_LEVEL_LOW
    ) -> str:
        """
        生成AI响应

        Args:
            user_input: 用户输入
            context: 上下文信息（用户信息、对话历史等）
            safety_level: 安全级别

        Returns:
            AI生成的响应
        """
        # 构建提示词
        prompt = self._build_prompt(user_input, context)

        # 如果有知识库，添加相关知识
        web_search_done = False
        web_result = ""
        if self.knowledge_base and hasattr(self.knowledge_base, 'search'):
            search_results = self.knowledge_base.search(user_input, top_k=RETRIEVAL_CANDIDATE_K)
            search_results = [r for r in search_results if r.get("score", 0) >= RETRIEVAL_SCORE_THRESHOLD]
            if search_results:
                search_results = self._rerank_knowledge(user_input, search_results, RETRIEVAL_TOP_K)
                knowledge_context = self.knowledge_base.format_context(search_results)
                prompt = prompt.replace(
                    "[知识库内容]",
                    f"\n\n## 参考知识库内容：\n{knowledge_context}\n\n如果知识库内容与问题相关，请优先参考上述内容。\n"
                )
            else:
                prompt = prompt.replace(
                    "[知识库内容]",
                    "\n\n## 网络搜索结果：\n正在搜索中...\n"
                )
                web_result = ""
                try:
                    web_result = search_web(user_input)
                    web_search_done = True
                except Exception as e:
                    print(f"网络搜索失败: {e}")
                if web_result:
                    prompt = prompt.replace(
                        "## 网络搜索结果：\n正在搜索中...\n",
                        f"## 网络搜索结果：\n{web_result}\n\n请基于以上网络搜索结果回答用户问题，引用搜索到的信息来源。\n"
                    )
                else:
                    prompt = prompt.replace(
                        "## 网络搜索结果：\n正在搜索中...\n",
                        "\n\n## 参考知识库内容：\n（知识库和网络搜索均未获取到相关信息。请坦诚告知用户，并建议咨询专业机构。）\n"
                    )
        else:
            prompt = prompt.replace(
                "[知识库内容]",
                "\n\n## 参考知识库内容：\n（知识库未加载，请根据你的知识诚实回答。不确定的信息请明确说明。）\n"
            )
            web_result = ""
            try:
                web_result = search_web(user_input)
                web_search_done = True
            except Exception as e:
                print(f"网络搜索失败: {e}")
            if web_result:
                prompt = prompt.replace(
                    "参考知识库内容：\n（知识库未加载",
                    f"网络搜索结果：\n（知识库未加载，以下为网络搜索结果）\n{web_result}\n\n请基于以上网络搜索结果回答用户问题。"
                )

        if context.get("rag_context"):
            prompt += f"\n\n{context['rag_context']}\n"

        # 调用AI（带工具支持）
        try:
            check_and_increment()  # 每日总调用预算兜底
            response = self._call_ai_with_tools(prompt)
            return response
        except BudgetExceededError as e:
            return f"⚠️ {e}"
        except Exception as e:
            print(f"AI 调用失败: {e}")
            if web_search_done and web_result:
                return f"## 🔍 网络搜索结果\n\n{web_result}\n\n---\n\n⚠️ AI 引擎暂时不可用，以上为直接搜索结果，仅供参考。"
            return self._generate_fallback_response(prompt)

    def _rerank_knowledge(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """Use the current LLM to rerank semantic retrieval candidates."""
        if not candidates:
            return []

        if not ENABLE_LLM_RERANK or not self.client:
            return candidates[:top_k]

        provider = self.model_config.get("provider", "")
        if provider not in ("openai", "volcengine"):
            return candidates[:top_k]

        if len(candidates) > RETRIEVAL_CANDIDATE_K:
            shortlist = []
            batch_size = RETRIEVAL_CANDIDATE_K
            for start in range(0, len(candidates), batch_size):
                batch = candidates[start:start + batch_size]
                shortlist.extend(self._rerank_knowledge_batch(query, batch, max(2, top_k // 2)))
            return self._rerank_knowledge_batch(query, shortlist, top_k)

        return self._rerank_knowledge_batch(query, candidates, top_k)

    def _rerank_knowledge_batch(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """Rerank one manageable batch of candidate chunks."""
        if not candidates:
            return []

        compact_items = []
        for idx, item in enumerate(candidates, 1):
            content = item.get("content", "").replace("\n", " ")
            compact_items.append({
                "id": idx,
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "content": content[:700]
            })

        prompt = f"""你是ABA知识库检索重排器。请根据用户问题，从候选知识片段中选出最相关、最能支持回答的片段。

用户问题：
{query}

候选片段：
{json.dumps(compact_items, ensure_ascii=False)}

要求：
1. 优先选择能直接回答问题、提供可操作步骤、包含安全边界的片段。
2. 不要选择只是碰巧出现相同词但语义无关的片段。
3. 最多返回 {top_k} 个片段 id。
4. 只输出JSON，不要解释。

输出格式：
{{"ids": [1, 3, 5]}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_config.get("model", ""),
                messages=[
                    {"role": "system", "content": "你只负责知识库语义重排，必须输出合法JSON。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200
            )
            text = response.choices[0].message.content or ""
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                return candidates[:top_k]

            data = json.loads(match.group())
            ids = data.get("ids", [])
            selected = []
            seen = set()
            for item_id in ids:
                try:
                    index = int(item_id) - 1
                except (TypeError, ValueError):
                    continue
                if 0 <= index < len(candidates) and index not in seen:
                    selected.append(candidates[index])
                    seen.add(index)
                if len(selected) >= top_k:
                    break

            return selected or candidates[:top_k]
        except Exception as e:
            print(f"知识库重排失败: {e}")
            return candidates[:top_k]

    def _build_prompt(self, user_input: str, context: Dict) -> str:
        """构建提示词"""

        # 构建用户信息上下文
        user_context = ""
        if context.get("child_name"):
            user_context += f"- 孩子姓名：{context['child_name']}\n"
        if context.get("child_age"):
            user_context += f"- 孩子年龄：{context['child_age']}\n"
        # 兼容两种键名：调用方传的是 "diagnosis"，旧代码用 "child_diagnosis"
        _diag = context.get("child_diagnosis") or context.get("diagnosis")
        if _diag:
            user_context += f"- 诊断情况：{_diag}\n"
        if context.get("intervention_goals"):
            user_context += f"- 当前干预目标：{context['intervention_goals']}\n"

        # 构建对话历史
        history_context = ""
        if context.get("conversation_history"):
            history_context = "\n\n## 对话历史：\n"
            for msg in context["conversation_history"][-5:]:
                role = "家长" if msg["role"] == "user" else "AI助手"
                history_context += f"- {role}：{msg['content'][:100]}...\n"

        # 组装完整提示词
        prompt = f"""{SYSTEM_PROMPT}

## 当前用户信息：
{user_context if user_context else "（暂无详细信息）"}

## 用户当前问题：
{user_input}

{history_context}

## 相关知识库内容：
[知识库内容]

请根据以上信息，就事论事地给出专业、清晰、有帮助的回答。默认提问者情绪正常、只是想了解信息，除非对方明确表达情绪，否则不必做情绪安抚，也不要把孩子当作"有问题"来对待。
"""

        return prompt

    def _call_ai_with_tools(self, prompt: str) -> str:
        """
        调用AI生成响应（网络搜索已在 generate_response 中主动执行）

        Args:
            prompt: 提示词

        Returns:
            AI最终响应
        """
        if not self.client:
            return self._generate_fallback_response(prompt)

        provider = self.model_config.get("provider", "")
        model = self.model_config.get("model", "")

        messages = [
            {"role": "system", "content": "你是一位专业、平实、就事论事的ABA智能助手，帮助家长了解孩子的行为与干预方法。默认提问者情绪正常、只是想了解信息，只在对方明确表达情绪时才回应情绪；把孩子当作普通孩子看待，不预设孩子有问题。请用中文回答。"},
            {"role": "user", "content": prompt}
        ]

        try:
            if provider in ("openai", "volcengine"):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content or "抱歉，我没有找到相关信息。"

            elif provider == "anthropic":
                response = self.client.messages.create(
                    model=model,
                    max_tokens=2000,
                    messages=messages
                )
                return response.content[0].text

            return self._generate_fallback_response(prompt)

        except Exception as e:
            print(f"AI调用失败: {e}")
            return self._generate_fallback_response(prompt)

    def _generate_fallback_response(self, prompt: str) -> str:
        """生成后备响应（当AI不可用时）"""
        return """⚠️ **服务暂时不可用**

AI 引擎当前无法响应，可能是 API 余额不足或网络问题。

**你可以尝试：**
• 稍后再试
• 在页面左侧切换其他 AI 引擎（如有配置）
• 联系管理员检查 API Key 余额

抱歉给你带来不便！"""

