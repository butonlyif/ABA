"""四级风险评估 + 分级危机响应，ABA 与 Coach 共享。"""

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
        "在此之前，可以先把环境调整到更安全、刺激更少的状态。"
    )
