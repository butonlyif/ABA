import logging
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import get_settings
from .http_client import outbound_http_client

logger = logging.getLogger(__name__)

# ====================================
# 安全分级（T2）：四级风险 + 分级危机响应
# ====================================
# 级别参考旧平台 safety.py / coach_engine.py，并区分「家长本人危机」与「孩子相关风险」。

SAFETY_LEVEL_LOW = 1
SAFETY_LEVEL_MEDIUM = 2
SAFETY_LEVEL_HIGH = 3
SAFETY_LEVEL_EMERGENCY = 4

# 紧急（立即生命安全）：自杀/自伤/扩大性自杀/严重自残
_EMERGENCY_KEYWORDS = [
    "自杀", "自伤", "想死", "不想活", "不想活了", "活着没意思",
    "割腕", "跳楼", "上吊", "吃药自杀", "安眠药",
    "带孩子一起走", "带孩子一起死", "同归于尽", "一了百了",
    "结束这一切", "结束生命", "想消失", "解脱",
]

# 高风险：攻击/严重自伤/重度心理危机（未达紧急）
_HIGH_RISK_KEYWORDS = [
    "杀人", "弄死", "打死", "伤害孩子", "伤害自己",
    "撞头", "打自己", "咬自己",
    "崩溃", "绝望", "撑不下去", "撑不下去了", "活不下去", "没法活了",
    "绝食", "不吃饭", "不喝水", "拒绝吃喝",
]

# 中风险：行为/情绪问题，需要关注但不必立即介入
_MEDIUM_RISK_KEYWORDS = [
    "打人", "咬人", "攻击", "暴力",
    "焦虑", "抑郁", "脾气",
]

CRISIS_HOTLINES = [
    ("全国心理援助热线", "400-161-9995"),
    ("北京心理危机研究与干预中心（24h）", "010-82951332"),
    ("希望24热线", "400-161-9995"),
]


def _hotlines_block() -> str:
    return "\n".join(f"• **{name}**：{phone}" for name, phone in CRISIS_HOTLINES)


def assess_risk(message: str) -> dict:
    """对文本做四级风险评估。

    返回 {level, keywords, risk_type, action}。
    level 越高越紧急：1=低 2=中 3=高 4=紧急。
    """
    if any(kw in message for kw in _EMERGENCY_KEYWORDS):
        return {"level": SAFETY_LEVEL_EMERGENCY, "risk_type": "emergency", "action": "provide_emergency_info"}
    high_hits = [kw for kw in _HIGH_RISK_KEYWORDS if kw in message]
    if high_hits:
        return {"level": SAFETY_LEVEL_HIGH, "keywords": high_hits, "risk_type": "high", "action": "suggest_professional_help"}
    medium_hits = [kw for kw in _MEDIUM_RISK_KEYWORDS if kw in message]
    if medium_hits:
        return {"level": SAFETY_LEVEL_MEDIUM, "keywords": medium_hits, "risk_type": "medium", "action": "provide_supportive_response"}
    return {"level": SAFETY_LEVEL_LOW, "keywords": [], "risk_type": "low", "action": "normal_response"}


def crisis_response(message: str, product: str = "aba") -> str | None:
    """根据风险评估返回危机文案，无风险返回 None。

    product 区分语境：
    - "coach"：家长本人是高危主体（人生教练场景），文案聚焦家长安全 + 热线
    - "aba" 或其他：默认语境，文案兼顾孩子安全与家长应对
    - HIGH 级别也返回支持性文案（建议专业支持），不只拦截 EMERGENCY
    """
    risk = assess_risk(message)
    level = risk["level"]

    if level < SAFETY_LEVEL_HIGH:
        return None

    if product == "coach":
        # 家长本人危机（人生教练场景）
        if level >= SAFETY_LEVEL_EMERGENCY:
            return (
                "我读到你现在非常痛苦，谢谢你愿意把这些说出来。💚\n\n"
                "**你此刻的安全，比任何事情都重要。** 你不需要一个人扛过这一刻——"
                "请现在就联系能立刻帮到你的人：\n\n"
                f"{_hotlines_block()}\n\n"
                "• 如果你有立即伤害自己的冲动，请拨打 **120** 或前往最近医院急诊\n"
                "• 也可以联系一位此刻能赶到你身边的家人或朋友\n\n"
                "我是一个陪伴工具，没办法替代专业的危机援助。但我想让你知道："
                "你的痛苦是真实的，你值得被帮助，而且现在就有人能帮你。"
            )
        # HIGH
        return (
            "我听到你现在真的很不容易，这份沉重是真实的。💚\n\n"
            "当压力大到这个程度，专业的支持会很有帮助——这不是软弱，而是照顾好自己的方式：\n\n"
            f"{_hotlines_block()}\n\n"
            "你也可以考虑联系心理咨询师，或和一位信任的人聊聊。\n\n"
            "如果你愿意，我也在这里陪你慢慢说。此刻，你最需要的是什么？"
        )

    # ABA 家长助手语境：兼顾孩子安全 + 家长应对
    if level >= SAFETY_LEVEL_EMERGENCY:
        return (
            "⚠️ 你描述的情况可能涉及立即的安全风险，请先确保孩子和危险物品保持安全距离。\n\n"
            "**立刻联系：**\n"
            f"{_hotlines_block()}\n"
            "• 紧急情况请直接拨打 **120** 或 **110**\n"
            "• 也可以联系孩子的医生或就近医院急诊\n\n"
            "确保安全后，再寻求 ABA 专业人员的现场支持。"
        )
    # HIGH
    return (
        "你提到的状况让我有些担心。当行为或情绪激烈到这个程度，专业的现场支持会比自助更有效：\n\n"
        f"{_hotlines_block()}\n\n"
        "建议同时联系孩子的行为分析师或心理专业人员评估下一步。"
        "在此之前，可以先把环境调整到更安全、更少刺激的状态。"
    )


# ====================================
# OSKAR 方案聚焦意图检测（coach 专用）
# ====================================
# 当用户主动求助/要方法时，在 ACT 情绪陪伴之上衔接 SF 方案引导。
# 安全分流已拦截 HIGH/EMERGENCY，此处只处理低中风险。

_SOLUTION_SEEKING_KEYWORDS = [
    "怎么办", "该怎么办", "我该怎么做", "怎么处理",
    "有什么办法", "有没有办法", "有什么方法", "有什么好办法",
    "教教我", "告诉我怎么做", "告诉我怎么",
    "我想改变", "想改变", "想解决", "想突破",
    "有什么建议", "给个建议", "给点建议", "帮我出出主意", "求支招",
    "不知道怎么办", "不知道该怎么办", "不知道怎么",
    "怎么才能", "怎样才能", "怎样能",
    "怎么破", "怎么搞定", "怎么做",
]

# 否定信号：用户明确只想倾诉、不要方案，或已经得到答案
_VENTING_ONLY_KEYWORDS = [
    "不用给建议", "不用建议", "不用你帮", "不用帮我",
    "只是想说说", "只想说说", "只是想倾诉", "只想倾诉",
    "听着就好", "你听就好", "不用解决", "不需要建议",
    "我知道该怎么做了", "我知道怎么做了", "我知道该怎么做",
    "已经知道了", "已经解决了", "没问题了", "搞定了",
]


def detect_solution_intent(message: str) -> bool:
    """检测用户是否在主动寻求解决方案/方法（而非单纯倾诉情绪）。"""
    if not message:
        return False
    if any(kw in message for kw in _VENTING_ONLY_KEYWORDS):
        return False
    return any(kw in message for kw in _SOLUTION_SEEKING_KEYWORDS)


# OSKAR 关闭信号：用户明确表示已得到答案、流程可以结束
_OSKAR_CLOSING_KEYWORDS = [
    "我知道该怎么做了", "我知道怎么做了", "我知道该怎么做",
    "已经知道了", "已经解决了", "没问题了", "搞定了",
]


def is_oskar_closing(message: str) -> bool:
    """检测用户是否明确表示 OSKAR 流程可以结束。"""
    if not message:
        return False
    return any(kw in message for kw in _OSKAR_CLOSING_KEYWORDS)


# OSKAR 方案聚焦 prompt 段（用户主动求方案时，追加到 ACT system prompt 之后）
OSKAR_COACH_PROMPT = (

    "\n\n当用户主动寻求方法、想往前走一步时，切换到「解决方案聚焦（Solutions Focus）」模式，"
    "用 OSKAR 框架一步步引导（源自 The Solutions Focus）：\n"
    "O — Outcome（成果）：用户想要什么？假如一夜之间事情变好了，明天早上会先注意到什么不同？\n"
    "S — Scaling（量尺）：0–10，现在大概在几？是什么让你到了这个数，而不是 0？\n"
    "K — Know-how（资源）：这个理想状态，什么时候已经发生过，哪怕一点点？那一次你做了什么？\n"
    "A — Affirm & Action（肯定与行动）：先肯定已有资源，再邀请用户选「上升一分」的最小一步。\n"
    "R — Review（回顾）：什么变好了？你做了什么带来这个改变？\n\n"
    "OSKAR 模式的关键规则：\n"
    "- 根据对话历史判断用户当前处在 OSKAR 的哪一步，每次只推进一个字母、只问一个问题。\n"
    "- 永远先肯定已有资源（哪怕很小），再问下一步。\n"
    "- 「下一步/小行动」必须由用户自己说，你不替他决定、不列任务清单。\n"
    "- 核心追问永远是「什么变好了？」，哪怕是偶然的进步也要抓住放大。\n"
    "- 如果用户回到强烈情绪，先回到共情陪伴，OSKAR 进度自然暂停、不丢失。"
)


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


# ====================================
# 知识库检索：关键词匹配（ABA 术语高度结构化，无需向量索引）
# ====================================

@lru_cache(maxsize=1)
def knowledge_documents() -> list[tuple[str, str]]:
    settings = get_settings()
    root = Path(settings.knowledge_path)
    if not root.is_absolute():
        candidates = [Path("/app/legacy/knowledge")]
        # 本地开发：从 services/ai.py 往上找项目根
        p = Path(__file__).resolve().parent
        for _ in range(5):
            p = p.parent
            candidates.append(p / settings.knowledge_path)
        root = next((c for c in candidates if c.exists()), root)
    documents: list[tuple[str, str]] = []
    if not root.exists():
        return documents
    for path in root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for index, chunk in enumerate(re.split(r"\n(?=#{1,3}\s)", text)):
            if len(chunk.strip()) >= 80:
                documents.append((f"{path.name}#{index + 1}", chunk.strip()[:2400]))
    return documents


def retrieve(message: str, limit: int = 3) -> list[dict[str, str]]:
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", message.lower()))
    ranked = []
    for title, content in knowledge_documents():
        score = sum(2 if term in title.lower() else 1 for term in terms if term in content.lower() or term in title.lower())
        if score:
            ranked.append((score, title, content))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"title": title, "content": content} for _, title, content in ranked[:limit]]


def fallback_answer(product: str, message: str, sources: list[dict[str, str]]) -> str:
    if product == "coach":
        if detect_solution_intent(message):
            return (
                "我听到你想往前走一步。我们慢慢来——先想一个画面："
                "假如一夜之间这件事变好了，明天早上你会先注意到什么不同？"
                "不用想得很完美，哪怕一个小细节也好。"
            )
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


def analyze_medical_record(text: str) -> tuple[dict | None, str]:
    """分析病例文本，返回 (status_snapshot, summary)。

    status_snapshot 格式: {domains: {域: 0-100}, overall_level: 1-5, source: "record"}
    """
    import json
    settings = get_settings()
    if not settings.minimax_api_key:
        return None, "未配置 AI 服务，无法分析病例。"
    system = (
        "你是专业的 ABA 评估分析师。根据家长提供的病例/评估报告文本，"
        "推断孩子在以下能力域的当前水平（0-100 分）："
        "参与技能、模仿技能、语言理解、语言表达、社交技能、情绪调节、自理技能、游戏技能、学业前技能。"
        "同时给出总体发展等级(1=起步,5=接近典型)。只返回 JSON，格式："
        '{"domains":{"参与技能":分数,...},"overall_level":1-5,"summary":"一句话总结"}'
    )
    try:
        response = outbound_http_client().post(
            f"{settings.minimax_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.minimax_api_key}"},
            json={"model": settings.minimax_model, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"病例内容：\n{text[:3000]}"},
            ], "temperature": 0.2},
            timeout=40,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
        # 提取 JSON
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            return None, "AI 返回格式异常，无法解析。"
        data = json.loads(match.group())
        data["source"] = "record"
        data["updated_at"] = ""
        summary = data.pop("summary", "病例分析完成")
        return data, summary
    except Exception as exc:
        return None, f"病例分析失败：{type(exc).__name__}"


def generate(product: str, message: str, history: list[dict], context: str | None = None, oskar_active: bool = False) -> tuple[str, list[dict[str, str]], AiCall]:
    started = time.perf_counter()
    settings = get_settings()
    risk = crisis_response(message, product)
    if risk:
        return risk, [], AiCall("safety", "local-rules", True, False)
    sources = retrieve(message) if product == "aba" else []
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
    # OSKAR 方案聚焦：用户主动求方案或已在 OSKAR 流程中时，追加 SF 引导段
    if product == "coach" and (oskar_active or detect_solution_intent(message)):
        system += OSKAR_COACH_PROMPT
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
