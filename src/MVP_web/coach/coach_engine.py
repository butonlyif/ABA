"""
====================================
人生教练模块 - 对话引擎
====================================

分层设计，优先级从高到低：
  1. 安全分流（safety triage）—— 任何回应之前先做风险识别。这是面向高压、
     易耗竭家长的心理类工具的底线（do no harm）。检测复用 safety.py 的
     SafetyChecker，并补充「家长语境」特有的高危信号（如扩大性自杀），
     危机文案则面向家长本人（区别于 safety.py 面向孩子的版本）。
  2. LLM 教练（ACT 人格）—— 若配置了任一模型 API Key，用大模型做真正的
     反映式倾听 + 苏格拉底式提问；否则自动降级。
  3. 脚本兜底 —— 无 Key 或调用失败时，回退到基于情绪策略库的脚本回应，
     保证产品在离线/无 Key 情况下仍可用。

依赖：coach_content（纯数据）、safety、config、agent 的 provider 约定。
本模块不依赖 streamlit。
"""

import os
import re
import hmac
import hashlib
from typing import Optional, List, Dict, Tuple

from core.safety import SafetyChecker
from core.config import AI_MODELS, DEFAULT_MODEL, SAFETY_LEVEL_HIGH, SAFETY_LEVEL_EMERGENCY
from coach.coach_content import (
    EMOTION_KEYWORDS,
    EMOTION_COACH_STRATEGIES,
    ISSUE_TYPE_KEYWORDS,
    KB_ARTICLES,
)

# ====================================
# 0. 单点登录（SSO）签名 —— 公开 8503 时防止凭用户名冒充
# ====================================

def coach_sso_token(username: str) -> Optional[str]:
    """用共享密钥 COACH_SSO_SECRET 为用户名签名，供主应用→人生教练免密跳转。

    未配置密钥时返回 None（此时人生教练应禁用自动登录，回退到账号密码登录）。
    """
    secret = os.getenv("COACH_SSO_SECRET", "")
    if not secret or not username:
        return None
    return hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def verify_coach_sso_token(username: str, token: str) -> bool:
    """恒定时间校验 SSO 令牌。"""
    expected = coach_sso_token(username)
    if not expected or not token:
        return False
    return hmac.compare_digest(expected, token)


# ====================================
# 1. 安全分流
# ====================================

_safety_checker = SafetyChecker()

# 家长语境特有的高危信号：safety.py 的关键词面向「孩子」，这里补充家长本人
# 的危机表达，尤其是「扩大性自杀 / 带孩子一起走」这类必须最高优先级拦截的情形。
PARENT_CRISIS_KEYWORDS = [
    "带孩子一起走", "带孩子一起死", "同归于尽", "一了百了",
    "不想撑了", "撑不下去了", "结束这一切", "结束生命",
    "活不下去", "没法活了", "想消失", "解脱",
]

# 心理援助热线（与 safety.EmergencyResources 一致，便于家长直接拨打）
CRISIS_HOTLINES = [
    ("全国心理援助热线", "400-161-9995"),
    ("北京心理危机研究与干预中心（24h）", "010-82951332"),
    ("希望24热线", "400-161-9995"),
]


def assess_risk(text: str) -> Dict:
    """对家长的输入做风险评估，返回 safety.py 风格的结果字典。

    在 SafetyChecker 基础上叠加家长语境关键词；命中则升到 EMERGENCY。
    """
    result = _safety_checker.check(text)
    hits = [kw for kw in PARENT_CRISIS_KEYWORDS if kw in text]
    if hits:
        return {
            "level": SAFETY_LEVEL_EMERGENCY,
            "keywords": result.get("keywords", []) + hits,
            "risk_type": "emergency",
            "message": "检测到家长自身的危机信号",
            "action": "provide_emergency_info",
        }
    return result


def _hotlines_block() -> str:
    lines = "\n".join(f"• **{name}**：{phone}" for name, phone in CRISIS_HOTLINES)
    return lines


def crisis_response(level: int) -> str:
    """面向家长本人的危机回应（区别于 safety.py 面向孩子的模板）。"""
    if level >= SAFETY_LEVEL_EMERGENCY:
        return (
            "我读到你现在非常痛苦，谢谢你愿意把这些说出来。💚\n\n"
            "**你此刻的安全，比任何事情都重要。** 你不需要一个人扛过这一刻——"
            "请现在就联系能立刻帮到你的人：\n\n"
            f"{_hotlines_block()}\n\n"
            "• 如果你有立即伤害自己的冲动，请拨打 **120** 或前往最近医院急诊\n"
            "• 也可以联系一位此刻能赶到你身边的家人或朋友\n\n"
            "我是一个陪伴工具，没办法替代专业的危机援助。但我想让你知道："
            "你的痛苦是真实的，你值得被帮助，而且现在就有人能帮你。你愿意先拨通上面任意一个电话吗？"
        )
    # SAFETY_LEVEL_HIGH：强烈情绪/耗竭，但未达紧急
    return (
        "我听到你现在真的很不容易，这份沉重是真实的。💚\n\n"
        "当压力大到这个程度，专业的支持会很有帮助——这不是软弱，而是照顾好自己的方式：\n\n"
        f"{_hotlines_block()}\n\n"
        "你也可以考虑联系心理咨询师，或和一位信任的人聊聊。\n\n"
        "如果你愿意，我也在这里陪你慢慢说。此刻，你最需要的是什么？"
    )


# ====================================
# 情绪 / 议题检测（含轻量否定处理）
# ====================================

_NEGATIONS = "不没无别莫勿"


def _count_keyword(text: str, kw: str) -> int:
    """统计 kw 出现次数，跳过紧邻否定词（如「不焦虑」「没那么累」）的情形。"""
    cnt, start = 0, 0
    while True:
        i = text.find(kw, start)
        if i < 0:
            break
        prev = text[i - 1] if i > 0 else ""
        if prev not in _NEGATIONS:
            cnt += 1
        start = i + len(kw)
    return cnt


def detect_emotion(text: str) -> Tuple[Optional[str], int]:
    """检测主要情绪，返回 (emotion_type, confidence) 或 (None, 0)。"""
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        count = sum(_count_keyword(text, kw) for kw in keywords)
        if count > 0:
            scores[emotion] = count
    if not scores:
        return None, 0
    top_emotion = max(scores, key=scores.get)
    return top_emotion, scores[top_emotion]


def detect_issue_type(issue_text: str) -> str:
    """根据议题文本检测最匹配的情绪/议题类型。"""
    scores = {}
    for issue_type, keywords in ISSUE_TYPE_KEYWORDS.items():
        score = sum(_count_keyword(issue_text, kw) for kw in keywords)
        if score > 0:
            scores[issue_type] = score
    if scores:
        return max(scores, key=scores.get)
    return "default"


# ====================================
# 2. LLM 教练（ACT 人格）
# ====================================

ACT_COACH_SYSTEM_PROMPT = """你是一位温暖、专业的「人生教练」，服务对象是自闭症孩子的家长。你的理论基础是 ACT（接纳与承诺疗法）、正念与积极心理学。

你的角色与方法：
- 你陪伴的是「家长本人」，关注他们的情绪与自我照顾，而不是给孩子做 ABA 干预。
- 用「反映式倾听 + 苏格拉底式提问」帮助对方自己看清、自己找到方向，而不是直接给结论或大段说教。
- 善用 ACT 的过程：接纳情绪、与消极想法解离、回到当下、看见完整的自我、澄清价值观、迈出小的承诺行动。
- 语气温暖、平等、不评判。把家长当作有能力的人，而不是需要被修理的问题。

严格的边界（必须遵守）：
- 你不是医生或心理治疗师，**不做诊断、不评估病情、不建议任何药物或剂量**。
- 不替代专业治疗。当对方的痛苦超出自我照顾的范围时，温和地鼓励寻求专业帮助。
- 不对孩子的医疗、用药、康复方案给出指令性建议。

回应风格：
- 简短，通常 2–5 句话。不要长篇大论，不要一次给一堆任务。
- 先共情、再提问。每次回应尽量以「一个开放式问题」或「一个很小的、此刻就能做的行动」收尾。
- 用中文，自然口语，避免术语堆砌。可以偶尔使用一个温暖的 emoji（💚🌱），但不滥用。"""


def _resolve_client(model_name: str):
    """按 provider 初始化一个最小可用的聊天客户端，复用 agent.py 的约定。

    返回 (client, provider, model_id) ；若无可用 Key 则返回 (None, ...)。
    """
    cfg = AI_MODELS.get(model_name) or AI_MODELS.get(DEFAULT_MODEL) or {}
    provider = cfg.get("provider", "")
    model_id = cfg.get("model", "")
    try:
        if provider in ("openai", "volcengine"):
            if provider == "volcengine":
                api_key = os.getenv("DOUBAO_API_KEY")
                base_url = cfg.get("base_url", "https://ark.cn-beijing.volces.com/api/v3")
            else:
                api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY")
                base_url = cfg.get("base_url", "https://api.minimaxi.com/v1")
            if not api_key:
                return None, provider, model_id
            from openai import OpenAI
            return OpenAI(api_key=api_key, base_url=base_url), provider, model_id
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return None, provider, model_id
            from anthropic import Anthropic
            return Anthropic(api_key=api_key), provider, model_id
    except Exception:
        return None, provider, model_id
    return None, provider, model_id


def _strip_reasoning(text: str) -> str:
    """剥离推理模型（如 MiniMax-M2.7）输出里的 <think>…</think> 思考块。"""
    if not text:
        return text
    text = re.sub(r"(?is)<think>.*?</think>", "", text)
    # 兜底：只有起始标签没有结束标签时，丢弃到最后一个换行后的正文
    if "<think>" in text:
        text = text.split("<think>")[0]
    return text.strip()


def _history_to_messages(messages_history: List[Dict], max_turns: int = 8) -> List[Dict]:
    """把会话历史转为 provider 的 messages 格式，并清除内部标记。"""
    msgs = []
    for m in (messages_history or [])[-max_turns:]:
        role = m.get("role")
        content = m.get("content", "")
        if role not in ("user", "assistant") or not content:
            continue
        if "__KB_REFS__:" in content:  # 去掉渲染用的内部标记
            content = content.split("__KB_REFS__:")[0].strip()
        msgs.append({"role": role, "content": content})
    return msgs


def llm_coach_reply(
    user_input: str,
    messages_history: List[Dict],
    model_name: Optional[str] = None,
    emotion: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> Optional[str]:
    """用 LLM 生成 ACT 风格的教练回应。无 Key / 调用失败时返回 None（由调用方降级）。

    extra_context：可选的参考材料（如用户正在阅读的文章正文），注入 system 供
    模型参考，但不出现在可见的对话里。
    """
    client, provider, model_id = _resolve_client(model_name or DEFAULT_MODEL)
    if client is None:
        return None

    system = ACT_COACH_SYSTEM_PROMPT
    if emotion:
        approach = EMOTION_COACH_STRATEGIES.get(emotion, {}).get("approach")
        hint = f"\n\n（参考：用户当前的主要情绪可能是「{emotion}」"
        hint += f"，可考虑的方向：{approach}）" if approach else "）"
        system += hint
    if extra_context:
        system += (
            "\n\n用户正在阅读下面这篇知识库文章，请结合它来回应（用自然的口吻，"
            "不要照搬原文）：\n---\n" + extra_context.strip()[:1800] + "\n---"
        )

    history = _history_to_messages(messages_history)
    # 历史里若已含本轮 user 输入则不重复添加
    if not (history and history[-1]["role"] == "user" and history[-1]["content"] == user_input):
        history.append({"role": "user", "content": user_input})

    try:
        if provider == "anthropic":
            resp = client.messages.create(
                model=model_id,
                system=system,
                messages=history,
                max_tokens=600,
                temperature=0.7,
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        else:  # openai-compatible
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system}] + history,
                max_tokens=600,
                temperature=0.7,
            )
            text = resp.choices[0].message.content
        text = _strip_reasoning(text or "")
        return text or None
    except Exception:
        return None


# ====================================
# 3. 脚本兜底 + 编排
# ====================================

def _emotion_turn(emotion: Optional[str], recent_context: List[Dict]) -> int:
    """估算同一情绪主题已连续对话的轮数（沿用原 v2 逻辑）。"""
    turn = 0
    if not emotion:
        return 0
    for msg in reversed(recent_context):
        if msg["role"] == "assistant":
            idx = recent_context.index(msg)
            prev_emotion, _ = detect_emotion(recent_context[idx - 1]["content"] if idx > 0 else "")
            if prev_emotion == emotion:
                turn += 1
            else:
                break
    return turn


def _augment(response: str, emotion: Optional[str], emotion_turn: int) -> str:
    """为回应附加知识库推荐（首轮）与教练小任务（后续轮），脚本/LLM 路径统一使用。"""
    if not emotion or emotion not in EMOTION_COACH_STRATEGIES:
        return response
    strategy = EMOTION_COACH_STRATEGIES[emotion]

    kb_refs = strategy.get("knowledge_refs", [])
    if kb_refs and emotion_turn == 0:
        valid = [r for r in kb_refs[:2] if KB_ARTICLES.get(r)]
        kb_links = [f"📚「{KB_ARTICLES[r]['title']}」" for r in valid]
        if kb_links:
            response += f"\n\n💡 你可能也会想看看：{' | '.join(kb_links)}"
            response += f"\n\n__KB_REFS__:{','.join(valid)}"

    tasks = strategy.get("tasks", [])
    if tasks and emotion_turn >= 1 and emotion_turn % 2 == 1:
        task = tasks[min(emotion_turn // 2, len(tasks) - 1)]
        response += f"\n\n🌱 教练小任务：{task['text']}（约{task['duration']}）"
    return response


def _scripted_base(emotion: Optional[str], emotion_turn: int, recent_context: List[Dict]) -> str:
    """脚本兜底：根据情绪策略库给出 opening / follow_up / 通用回应。"""
    if emotion and emotion in EMOTION_COACH_STRATEGIES:
        strategy = EMOTION_COACH_STRATEGIES[emotion]
        if emotion_turn == 0:
            return strategy["opening"]
        follow_ups = strategy["follow_ups"]
        return follow_ups[emotion_turn % len(follow_ups)]

    if recent_context:
        last_assistant = next(
            (m["content"] for m in reversed(recent_context) if m["role"] == "assistant"), None
        )
        if last_assistant and ("告诉我" in last_assistant or "?" in last_assistant or "？" in last_assistant):
            return ("谢谢你愿意继续和我聊 💚\n\n"
                    "你说的很有价值。很多时候，当我们把脑中的想法说出来，事情就会变得更清晰。\n\n"
                    "继续说吧，不急着做什么。我在这里倾听你。")

    return ("谢谢你告诉我 💚\n\n"
            "每一种感受都值得被看见。如果你愿意，可以和我多聊聊——\n"
            "- 此刻你最大的感受是什么？（焦虑？悲伤？困惑？还是别的？）\n"
            "- 有什么特别的事情触发了这个感受？\n"
            "- 你现在最需要的是什么？\n\n"
            "按照你自己的节奏来就好。我在这里，不评判，不催促。")


def generate_coach_response_v2(
    user_input: str,
    messages_history: List[Dict],
    extra_context: Optional[str] = None,
) -> str:
    """教练对话编排：安全分流 → LLM(ACT) → 脚本兜底，统一附加 KB/任务推荐。

    extra_context：可选参考材料（如正在阅读的文章），仅供 LLM 参考、不入对话。
    """
    # 1. 安全分流（最高优先级）
    risk = assess_risk(user_input)
    if risk.get("level", 0) >= SAFETY_LEVEL_HIGH:
        return crisis_response(risk["level"])

    # 2. 情绪与轮次
    emotion, _ = detect_emotion(user_input)
    recent_context = messages_history[-6:] if messages_history else []
    emotion_turn = _emotion_turn(emotion, recent_context)

    # 3. 优先 LLM，失败/无 Key 则脚本兜底
    base = llm_coach_reply(user_input, messages_history, emotion=emotion, extra_context=extra_context)
    if not base:
        base = _scripted_base(emotion, emotion_turn, recent_context)

    # 4. 统一附加知识库推荐与小任务
    return _augment(base, emotion, emotion_turn)
