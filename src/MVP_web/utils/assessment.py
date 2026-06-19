"""
ABA 能力评估（v3 — 全覆盖版）
按领域递进式设计 40 道题，skill_id 群组从 curriculum.py 自动关联。
采用"是即推进、否即停止"的分阶段逻辑：
  - 答"是" → 该层级技能视为已掌握 → 下一题
  - 答"否" → 该层级所有技能加入推荐，该领域停止推进

结果可对全部 9 个领域生成完整训练任务清单。
"""

from typing import List, Dict
from collections import defaultdict

DOMAIN_NAMES = {
    "participation": "参与技能",
    "imitation":     "模仿技能",
    "visual":        "视觉空间技能",
    "language":      "语言技能",
    "play":          "游戏技能",
    "social":        "社交技能",
    "emotion":       "情绪调节技能",
    "preacademic":   "学业前技能",
    "selfcare":      "自理技能",
}

DOMAIN_PRIORITY = {
    "participation": 1,
    "imitation":     2,
    "language":      3,
    "play":          4,
    "social":        5,
    "visual":        6,
    "emotion":       7,
    "selfcare":      8,
    "preacademic":   9,
}

# ─── 题目定义 ──────────────────────────────────────────
# skill_ids 留空时由 _resolve_skills() 从 curriculum 自动按领域+等级群组注入

RAW_QUESTIONS: List[Dict] = [
    # ══════════════════════════════════════════════════════
    # 参与技能（Level 1→2→3）
    # ══════════════════════════════════════════════════════
    {
        "id": "par_1", "domain": "participation", "level": 1,
        "question": "孩子能在椅子上安坐至少10秒并配合简单互动（呼名有眼神回应）？",
        "stage": 1,
    },
    {
        "id": "par_2", "domain": "participation", "level": 2,
        "question": "孩子能安坐1-3分钟参与桌面活动，且活动中呼名有回应，能执行1-2步指令？",
        "stage": 2,
    },
    {
        "id": "par_3", "domain": "participation", "level": 3,
        "question": "孩子能听从三步指令，并在小组中安坐、轮流等待？",
        "stage": 3,
    },

    # ══════════════════════════════════════════════════════
    # 模仿技能（Level 1→2→3）
    # ══════════════════════════════════════════════════════
    {
        "id": "imi_1", "domain": "imitation", "level": 1,
        "question": "大人做举手/鼓掌等简单动作或用玩具做动作时，孩子能模仿？（粗大动作 + 物品 + 口腔动作模仿）",
        "stage": 1,
    },
    {
        "id": "imi_2", "domain": "imitation", "level": 2,
        "question": "孩子能模仿精细动作（摸鼻/弯手指）、单音声音、2步动作序列？",
        "stage": 2,
    },
    {
        "id": "imi_3", "domain": "imitation", "level": 3,
        "question": "孩子能仿说单词并模仿3步动作序列？",
        "stage": 3,
    },

    # ══════════════════════════════════════════════════════
    # 视觉空间技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "vis_1", "domain": "visual", "level": 1,
        "question": "孩子能将相同物品/图片配对（颜色等），能完成4块拼图？",
        "stage": 1,
    },
    {
        "id": "vis_2", "domain": "visual", "level": 2,
        "question": "孩子能配对形状/数字/字母，按颜色/大小分类，能完成6块拼图？",
        "stage": 2,
    },
    {
        "id": "vis_3", "domain": "visual", "level": 3,
        "question": "孩子能配对同类不同图片，按类别分类，做3-4步排序，描线/形状/字母，做简单的视觉记忆？",
        "stage": 3,
    },
    {
        "id": "vis_4", "domain": "visual", "level": 4,
        "question": "孩子能识别荒谬处、按情节排序、美术涂色、10块拼图？",
        "stage": 4,
    },
    {
        "id": "vis_5", "domain": "visual", "level": 5,
        "question": "孩子掌握空间关系概念、视觉完形、大容量视觉记忆、精细视觉辨别？",
        "stage": 5,
    },

    # ══════════════════════════════════════════════════════
    # 语言技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "lan_1", "domain": "language", "level": 1,
        "question": "孩子能指认常见动物/食物/水果/蔬菜/日常物品，能用伸手或单词提要求，能说出物品名称？",
        "stage": 1,
    },
    {
        "id": "lan_2", "domain": "language", "level": 2,
        "question": "孩子能指认身体部位/动作/颜色/天气/场所/情绪，命名日常物品，用简单句表述，根据功能/类别指认？",
        "stage": 2,
    },
    {
        "id": "lan_3", "domain": "language", "level": 3,
        "question": "孩子能指认/命名形容词/角色/介词，回答Wh问题，理解否定/都/代词，命名功能/类别/特征，做对话问答？",
        "stage": 3,
    },
    {
        "id": "lan_4", "domain": "language", "level": 4,
        "question": "孩子能描述名词特征、区分大小问题、使用将来时态、理解抽象概念，根据描述猜物品/识别地点？",
        "stage": 4,
    },
    {
        "id": "lan_5", "domain": "language", "level": 5,
        "question": "孩子能掌握比喻性语言（习语/明喻）、不规则动词过去时态和复数？",
        "stage": 5,
    },

    # ══════════════════════════════════════════════════════
    # 游戏技能（Level 1→2→3）
    # ══════════════════════════════════════════════════════
    {
        "id": "pla_1", "domain": "play", "level": 1,
        "question": "孩子会探索玩具并用正确方式玩（如推车、叠积木），而非无目的地摆弄？",
        "stage": 1,
    },
    {
        "id": "pla_2", "domain": "play", "level": 2,
        "question": "孩子能独自玩耍5分钟以上？会做简单的假装动作？能和其他孩子在同一空间各自玩耍（平行游戏）？",
        "stage": 2,
    },
    {
        "id": "pla_3", "domain": "play", "level": 3,
        "question": "孩子能独自玩耍15分钟？能做假装游戏的情景序列？能与同伴做合作/轮流游戏和桌游？",
        "stage": 3,
    },

    # ══════════════════════════════════════════════════════
    # 社交技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "soc_1", "domain": "social", "level": 1,
        "question": "孩子会跟随他人指点看向物品？会主动问好并维持眼神交流？会用指点来提要求？",
        "stage": 1,
    },
    {
        "id": "soc_2", "domain": "social", "level": 2,
        "question": "孩子会分享性指点/展示物品？会叫同伴名字？会邀请并回应同伴一起玩吗？",
        "stage": 2,
    },
    {
        "id": "soc_3", "domain": "social", "level": 3,
        "question": "孩子会主动分享物品给他人？看到别人难过会去安慰？",
        "stage": 3,
    },
    {
        "id": "soc_4", "domain": "social", "level": 4,
        "question": "孩子能考虑他人感受？能区分适当和不当行为？会有目的地提问获取信息？",
        "stage": 4,
    },
    {
        "id": "soc_5", "domain": "social", "level": 5,
        "question": "孩子能玩20个问题游戏？能谈判/妥协？能识别社交中的友善/不友善行为？能理解社交语境中的语言含义？",
        "stage": 5,
    },

    # ══════════════════════════════════════════════════════
    # 情绪调节技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "emo_1", "domain": "emotion", "level": 1,
        "question": "孩子能从表情图片中分辨开心/难过？能被要求'等一下'时等待5秒？",
        "stage": 1,
    },
    {
        "id": "emo_2", "domain": "emotion", "level": 2,
        "question": "孩子能在真实情境中识别情绪并说自己的感受？能等待1分钟？被说'不行'时能接受不过度哭闹？",
        "stage": 2,
    },
    {
        "id": "emo_3", "domain": "emotion", "level": 3,
        "question": "孩子能说出情绪的原因、用简单应对策略安抚自己、理解'情感'相关的接受/表达语言？",
        "stage": 3,
    },
    {
        "id": "emo_4", "domain": "emotion", "level": 4,
        "question": "孩子能辨别和命名复杂情绪（如嫉妒、自豪、内疚等）？",
        "stage": 4,
    },
    {
        "id": "emo_5", "domain": "emotion", "level": 5,
        "question": "孩子已完成系统脱敏训练——能接受关灯睡觉/独自待房间/穿带纽扣衣物？",
        "stage": 5,
    },

    # ══════════════════════════════════════════════════════
    # 学业前技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "pre_1", "domain": "preacademic", "level": 1,
        "question": "孩子能说出4种以上颜色和至少3种形状名称，能口头数1-5？",
        "stage": 1,
    },
    {
        "id": "pre_2", "domain": "preacademic", "level": 2,
        "question": "孩子能数1-10，点数实物1-5，认识数字1-5，认识字母A-E？",
        "stage": 2,
    },
    {
        "id": "pre_3", "domain": "preacademic", "level": 3,
        "question": "孩子认识数字1-10、全部大写字母、能写自己名字、有数量概念、配对大小写字母、将文字与图片配对？",
        "stage": 3,
    },
    {
        "id": "pre_4", "domain": "preacademic", "level": 4,
        "question": "孩子能为图片配对简单的短语和句子？",
        "stage": 4,
    },
    {
        "id": "pre_5", "domain": "preacademic", "level": 5,
        "question": "孩子能写作流畅/写句子，做加减乘除和故事题，识别简单句子，识钟表？",
        "stage": 5,
    },

    # ══════════════════════════════════════════════════════
    # 自理技能（Level 1→2→3→4→5）
    # ══════════════════════════════════════════════════════
    {
        "id": "slf_1", "domain": "selfcare", "level": 1,
        "question": "孩子能独立完成洗手全流程？能配合刷牙和穿脱衣物？会用勺子等餐具进食？会主动表示如厕需求？",
        "stage": 1,
    },
    {
        "id": "slf_2", "domain": "selfcare", "level": 2,
        "question": "孩子能独立刷牙？独立穿脱简单衣物？接受多样食物？独立完成如厕全流程？",
        "stage": 2,
    },
    {
        "id": "slf_3", "domain": "selfcare", "level": 3,
        "question": "孩子能独立穿脱全套衣物（含拉链、纽扣、鞋带等）？",
        "stage": 3,
    },
    {
        "id": "slf_4", "domain": "selfcare", "level": 4,
        "question": "孩子能区分安全行为和危险行为？",
        "stage": 4,
    },
    {
        "id": "slf_5", "domain": "selfcare", "level": 5,
        "question": "孩子知道哪些食物健康？认识社区标志？知道什么时候需要急救？会采购/辨别交通标志？",
        "stage": 5,
    },
]


# ─── 从 curriculum 自动解析 skill_ids ─────────────────────

def _resolve_skills():
    """为每道题按 domain+level 自动注入 skill_ids。防止手写 skill_id 与课程不同步。"""
    import utils.curriculum as cur
    domain_map = {v: k for k, v in DOMAIN_NAMES.items()}
    for q in RAW_QUESTIONS:
        domain_cn = DOMAIN_NAMES[q["domain"]]
        level = q["level"]
        ids = []
        for s in cur.SKILLS:
            if s["domain"] == domain_cn and s["level"] == level:
                ids.append(s["skill_id"])
        q["skill_ids"] = ids

_resolve_skills()

QUESTIONS = RAW_QUESTIONS


# ─── 公开 API ─────────────────────────────────────────────

def get_questions_by_domain(domain_key: str) -> List[Dict]:
    qs = [q for q in QUESTIONS if q["domain"] == domain_key]
    return sorted(qs, key=lambda q: q["level"])


def get_stage_questions(stage: int) -> List[Dict]:
    return [q for q in QUESTIONS if q.get("stage") == stage]


def score_assessment(answers: Dict[str, bool]) -> Dict:
    """
    递进评分：每领域从低级到高级逐步推进。
    答"是"=掌握，答"否"=该 level 及以上的所有技能加入推荐。
    """
    domain_stats: Dict[str, Dict] = {}
    approved: set = set()
    recommended: set = set()

    for domain_key in DOMAIN_NAMES:
        qs = get_questions_by_domain(domain_key)
        passed_level = 0
        answered = 0
        yes_count = 0
        stop = False

        for q in qs:
            qid = q["id"]
            if qid not in answers:
                continue
            answered += 1
            if stop:
                for sid in q.get("skill_ids", []):
                    if sid: recommended.add(sid)
                continue
            if answers.get(qid, False):
                yes_count += 1
                passed_level = q["level"]
                for sid in q.get("skill_ids", []):
                    if sid: approved.add(sid)
            else:
                stop = True
                for sid in q.get("skill_ids", []):
                    if sid: recommended.add(sid)

        domain_stats[domain_key] = {
            "answered": answered,
            "yes_count": yes_count,
            "total_questions": len(qs),
            "passed_level": passed_level,
        }

    recommended -= approved

    levels = [v["passed_level"] for v in domain_stats.values() if v["answered"] > 0]
    overall_level = round(sum(levels) / len(levels)) if levels else 1
    overall_level = max(1, min(5, overall_level))

    domain_pct = {}
    for d, v in domain_stats.items():
        domain_pct[d] = round(v["yes_count"] / v["answered"] * 100) if v["answered"] > 0 else 0

    import utils.curriculum as cur
    skill_map = {s["skill_id"]: s for s in cur.SKILLS}

    ordered = []
    for domain_key in sorted(DOMAIN_NAMES.keys(),
                             key=lambda d: DOMAIN_PRIORITY.get(d, 99)):
        domain_cn = DOMAIN_NAMES[domain_key]
        for sid in recommended:
            if sid in skill_map and skill_map[sid]["domain"] == domain_cn:
                ordered.append(sid)

    return {
        "domain_scores": domain_pct,
        "domain_stats": domain_stats,
        "domain_levels": {d: v["passed_level"] for d, v in domain_stats.items()},
        "overall_level": overall_level,
        "recommended_skill_ids": ordered,
        "approved_skill_ids": list(approved),
        "answers": answers,
    }


def get_level_description(level: int) -> str:
    return {
        0: "待评估 — 建议从最基础的参与和模仿技能开始",
        1: "基础阶段 — 具备初步配合能力，适合开始系统训练",
        2: "中级阶段 — 已掌握基本技能，可推进语言、游戏和社交训练",
        3: "进阶阶段 — 建议聚焦对话、合作游戏、情绪调节和学业前技能",
        4: "高级阶段 — 可挑战复杂社交、抽象语言和学前准备",
        5: "专家阶段 — 对标典型发育同龄水平，可精炼高阶技能",
    }.get(level, "")


def get_domain_advice(domain_key: str, pct: int) -> str:
    name = DOMAIN_NAMES.get(domain_key, domain_key)
    if pct >= 75:
        return f"✅ {name}基础已掌握，可推进进阶技能"
    elif pct >= 40:
        return f"🔄 {name}部分掌握，建议巩固并向上推进"
    else:
        return f"🎯 {name}建议作为优先训练领域"
