import logging
import re
import time
from dataclasses import dataclass

from platform_shared.config import get_settings
from platform_shared.safety import crisis_response
from platform_shared.services.http_client import outbound_http_client

logger = logging.getLogger(__name__)

# ─── OSKAR 解决方案聚焦 提示词与检测 ───
_SOLUTION_KEYWORDS = [
    "怎么办", "该怎么", "怎么解决", "有什么办法", "教教我", "我想改变",
    "想解决", "想突破", "卡住了", "不知道怎么做", "不知道该怎么",
    "不知道怎么办", "怎么办才好", "有什么建议", "怎么做才好",
    "帮我出个主意", "指点", "方法", "出路", "怎么处理",
    "有什么方法", "步骤", "计划", "下一步", "出路在哪",
    "我想改变", "想改变自己", "帮我想想", "给我点建议",
    "我不知道", "束手无策", "一头雾水", "毫无头绪", "无从下手",
]
_NEGATION_SIGNALS = [
    "只想倾诉", "不用给建议", "先不用方法", "只要听就行",
    "不用怎么办", "不想听建议", "先陪陪我", "不用帮我想",
    "我就说说", "不用方案", "只是说说", "先不急着解决",
    "只想被听见",
]
_OSKAR_CLOSING_KEYWORDS = [
    "我知道了", "我明白了", "我知道该怎么做了", "我会试试",
    "好我试试", "我试试看", "我懂了", "我明白了", "清楚了",
    "谢谢你的引导", "有方向了", "不用再问了",
]

OSKAR_COACH_PROMPT = (
    "\n\n## 当家长需要往前走一步时，用「解决方案聚焦」（SF）的 OSKAR 五步引导\n"
    "你现在是 SF 教练，不是 ACT 陪伴者。你已经共情了对方，现在对方想突破了。\n\n"
    "核心原则：\n"
    "- 焦点在「想要的未来」而非「问题原因」\n"
    "- 每次只问一个问题，简短自然\n"
    "- 小步骤必须由对方自己说，你只问不指定\n"
    "- 永远先肯定已有资源，再问下一步\n\n"
    "五步顺序（每轮只推一步）：\n"
    "- O 成果：站到对方的位置上(platform)，再引出未来完美画面 '你希望这次聊完带走什么？假如一夜之间事情好转了一点，明天早上你会先注意到什么不同？'\n"
    "- S 量尺：让用户自评 '0-10你现在大概在几？是什么让你到了这个数而不是更低？'\n"
    "- K 资源：找已有的筹码 '这个理想状态什么时候已经发生过哪怕一点点？你做了什么让它发生的？'\n"
    "- A 行动：汇总肯定 → 邀请选一小步 '已经有很多在位了……你个人接下来的一小步是什么？'\n"
    "- R 回顾：下次开场问 '什么变好了？你做了什么带来这个改变？'\n\n"
    "重要：如果用户在 OSKAR 过程中回到强烈情绪，先共情再继续引导；如果用户说'我知道了/我明白了/我会试试'，"
    "就结束 OSKAR 回到 ACT 陪伴模式。")
_SOLUTION_FALLBACK = (
    "你说的情况听起来不容易。如果你想往前走一步，我们可以停下来想一想："
    "假如明天早上醒来感觉好了一点，你最想先注意到的一个变化是什么？"
    "不用想整个解决方案，就一个你能看见的小信号。")


def detect_solution_intent(message: str, history: list[dict] | None = None) -> bool:
    """判定用户是否在「想求方案/想往前走一步」的意图。"""
    if not message or not message.strip():
        return False
    text = message.strip().lower()
    # 否定信号优先排除
    for neg in _NEGATION_SIGNALS:
        if neg in text:
            return False
    # 检查求助关键词
    for kw in _SOLUTION_KEYWORDS:
        if kw in text:
            return True
    return False


def is_oskar_closing(message: str) -> bool:
    """判定用户是否在发出关闭 OSKAR 的信号。"""
    text = message.strip().lower()
    for kw in _OSKAR_CLOSING_KEYWORDS:
        if kw in text:
            return True
    return False


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
        if detect_solution_intent(message):
            return _SOLUTION_FALLBACK
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
