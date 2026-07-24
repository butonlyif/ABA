import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx

from ..config import get_settings

CRISIS_TERMS = ("自杀", "不想活", "伤害孩子", "杀了", "一起走", "伤害自己")


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


def crisis_response(message: str) -> str | None:
    if not any(term in message for term in CRISIS_TERMS):
        return None
    return (
        "你描述的情况可能涉及立即安全风险。请先与孩子和危险物品保持安全距离，"
        "马上联系身边可信赖的人和当地紧急服务，并尽快寻求专业人员现场帮助。"
    )


@lru_cache(maxsize=1)
def knowledge_documents() -> list[tuple[str, str]]:
    settings = get_settings()
    root = Path(settings.knowledge_path)
    if not root.is_absolute():
        root = (Path(__file__).resolve().parents[4] / root).resolve()
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
        return (
            "听起来你正在承担很多。我们先不要求自己立刻解决所有问题："
            "试着说出此刻最强烈的感受，再选择一件今天可以减轻 10% 的事情。"
            "如果愿意，也可以告诉我今天最消耗你的具体时刻。"
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


def generate(product: str, message: str, history: list[dict]) -> tuple[str, list[dict[str, str]], AiCall]:
    started = time.perf_counter()
    settings = get_settings()
    risk = crisis_response(message)
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
        else "你是基于ACT的家长成长陪伴者。温暖、不评判、不过度说教，不做医学诊断。"
    )
    context = "\n\n".join(item["content"] for item in sources)
    messages = [{"role": "system", "content": system + (f"\n参考资料：\n{context}" if context else "")}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})
    try:
        response = httpx.post(
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
