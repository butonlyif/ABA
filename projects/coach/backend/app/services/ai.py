import logging
import re
import time
from dataclasses import dataclass

from platform_shared.config import get_settings
from platform_shared.safety import crisis_response
from platform_shared.services.http_client import outbound_http_client

logger = logging.getLogger(__name__)


@dataclass
class AiCall:
    provider: str
    model: str
    success: bool
    fallback: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    error_type: str | None = None


def fallback_answer(product: str, message: str, sources: list[dict[str, str]]) -> str:
    if product == "coach":
        return (
            "我在听。这里不用急着解释清楚，也不用马上解决它。"
            "可以先留意一下：当这个念头出现时，你的身体哪里最紧？"
            "试着把“事情一定会变糟”换成“我注意到，我正在担心事情会变糟”。"
            "只是拉开一点距离，不需要逼自己相信别的。"
        )
    if sources:
        excerpt = re.sub(r"^#+\s*", "", sources[0]["content"].splitlines()[0]).strip()
        return (
            f"可以先从“{excerpt[:35]}”这个方向观察。建议记录行为发生前的情境、"
            "孩子的具体行为和随后结果（ABC），一次只调整一个变量，并及时强化可替代的沟通行为。"
        )
    return (
        "建议先记录行为发生前的情境、具体行为和随后结果（ABC）。"
        "从一次只调整一个变量开始，并强化孩子可以替代问题行为的沟通方式。"
    )


def generate(product: str, message: str, history: list[dict], context: str | None = None) -> tuple[str, list[dict[str, str]], AiCall]:
    started = time.perf_counter()
    settings = get_settings()
    risk = crisis_response(message, product)
    if risk:
        return risk, [], AiCall("safety", "local-rules", True, False)
    sources = []
    if not settings.minimax_api_key:
        return fallback_answer(product, message, sources), sources, AiCall(
            "local", "fallback", True, True,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    system = (
        "你是温暖、专业的ABA家庭助手。只提供家庭支持和教育信息，不替代医生或治疗师。"
        if product == "aba"
        else (
            "你是面向家长本人的情绪陪伴者，采用ACT（接纳与承诺疗法）的表达方式。"
            "你的核心作用是让用户安全地说出来，觉察情绪和身体感受，并与令人焦虑的念头拉开一点距离，"
            "从紧绷回到更有空间、更松弛、可选择的状态。"
            "不要默认把话题引向孩子、自闭症、ABA、训练或养育方法；只有用户主动谈到这些内容时，"
            "才在当前话题所需的范围内回应，也不要把对话变成孩子问题分析。"
            "优先回应用户本人此刻的感受，先共情和澄清，再给一个很轻的解离或落地邀请。"
            "每次尽量简短自然，通常只做一次回应并提出至多一个温和问题；"
            "除非用户明确需要方案，否则不要列任务清单、说教、强行积极化或催促行动。"
            "不做医学诊断，不替代心理治疗。"
        )
    )
    # T8：注入用户上下文（孩子档案/训练摘要/情绪趋势等），让 AI 记得用户情况
    if context and product == "aba":
        system += (
            "\n\n以下是当前登录用户的真实档案数据，由系统提供，已在你的上下文中，"
            "请在回答中**直接引用并基于这些事实作答**。"
            "当用户问及孩子/自己的情况时，**不要声明'我没有数据'或'请你告诉我'**——"
            "这些数据你已掌握。可以补充邀请家长分享更多观察，但不要否认已知事实。\n"
            f"{context}"
        )
    elif context:
        system += (
            "\n\n以下是用户近期主动留下的个人情绪与反思，仅作为理解其状态的安静背景。"
            "不要主动复述、盘点或引用这些记录，也不要借此转换话题；"
            "只有它与用户当前表达直接相关时，才自然地体现连续性。\n"
            f"{context}"
        )
    ref_context = "\n\n".join(item["content"] for item in sources)
    messages = [{"role": "system", "content": system + (f"\n\n参考资料：\n{ref_context}" if ref_context else "")}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})
    try:
        response = outbound_http_client().post(
            f"{settings.minimax_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.minimax_api_key}"},
            json={"model": settings.minimax_model, "messages": messages, "temperature": 0.4},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"]
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()
        usage = payload.get("usage", {})
        fallback = not bool(answer)
        return answer or fallback_answer(product, message, sources), sources, AiCall(
            "minimax", settings.minimax_model, True, fallback,
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        return fallback_answer(product, message, sources), sources, AiCall(
            "minimax", settings.minimax_model, False, True,
            latency_ms=round((time.perf_counter() - started) * 1000),
            error_type=type(exc).__name__,
        )
