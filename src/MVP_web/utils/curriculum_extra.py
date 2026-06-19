"""
新增三本书（初级/中级/高级技能分步训练）的课程技能 —— 自动生成。

背景：这三本书的「课程指南」是扫描件，无法自动提取分步骤；但每个卡片类别名
本身就是一个训练项目名。这里据此为每个新类别生成一条可训练技能，接入任务清单/
训练记录/图片卡片三联动。领域用关键词归类，难度按书分级（初级=3/中级=4/高级=5），
描述用通用 DTT 模板。后续若 OCR 出分步骤，可在此基础上精修。

新增书本时：把卡片放进 src/aba/图片/，并更新 curriculum_extra_data.NEW_BOOK_CATEGORIES。
"""

import hashlib
from typing import List, Dict

from utils.curriculum_extra_data import NEW_BOOK_CATEGORIES

try:
    from utils.curriculum_steps_data import STEPS as _STEPS
except Exception:
    _STEPS = {}

BOOK_LABEL = {3: "初级", 4: "中级", 5: "高级"}

# 领域关键词规则（按顺序匹配，命中即停）。9 个领域与 curriculum.py 保持一致。
_DOMAIN_RULES = [
    ("学业前技能", ["阅读", "写作", "数学", "乘法", "加法", "减法", "故事题",
                  "字母", "发音", "数量", "数字"]),
    ("自理技能", ["急救", "健康食物", "吃健康", "购物", "自动售货机", "驾驶",
                "交通标志", "社区标志", "安全行为", "危险行为"]),
    ("情绪调节技能", ["情绪", "情感", "系统脱敏"]),
    ("视觉空间技能", ["配对", "分类", "排列", "排序", "序列", "视觉", "空间关系",
                  "部分与整体", "完形", "记忆", "相同和不同", "哪个不是同类",
                  "荒谬", "荒诞", "美术", "画画", "按故事情节", "按照",
                  "三维形状", "材料构成"]),
    ("社交技能", ["社交", "友善", "谈判", "妥协", "考虑他人", "考虑自己",
                "适当行为", "不当行为", "令人不快", "通过提问", "20个问题"]),
    ("语言技能", ["语言", "复数", "时态", "代词", "性别", "反义词", "属性",
                "名词", "描述", "命名", "问题", "是否", "哪一个", "谁", "什么",
                "句子", "钱", "天气", "真实与虚构", "最喜欢", "抽象概念",
                "常识", "推理", "习语", "明喻", "比喻", "根据描述", "房间",
                "功能", "类别", "辨别声音", "大问题与小问题"]),
]
_DEFAULT_DOMAIN = "语言技能"


def classify_domain(name: str) -> str:
    for domain, keywords in _DOMAIN_RULES:
        if any(kw in name for kw in keywords):
            return domain
    return _DEFAULT_DOMAIN


def _skill_id(name: str) -> str:
    return "ext_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


def build_extra_skills(existing_skills: List[Dict]) -> List[Dict]:
    """据卡片类别名生成技能；与已有技能按 名称/flashcard_category 去重。"""
    used_names = {s["name"] for s in existing_skills}
    used_cats = {s.get("flashcard_category") for s in existing_skills if s.get("flashcard_category")}
    used_ids = {s["skill_id"] for s in existing_skills}

    out: List[Dict] = []
    for level in sorted(NEW_BOOK_CATEGORIES):
        label = BOOK_LABEL.get(level, f"L{level}")
        for name in NEW_BOOK_CATEGORIES[level]:
            if name in used_names or name in used_cats:
                continue
            sid = _skill_id(name)
            if sid in used_ids:
                continue
            domain = classify_domain(name)
            steps = _STEPS.get(name) or []
            if steps:
                desc = (
                    f"（{label}）训练目标：{name}。共 {len(steps)} 个分步目标（见下方步骤，"
                    f"取自课程指南）。每步用回合式教学(DTT)：出示指令→等待反应→记录试次；"
                    f"连续 3 次独立正确率≥80% 进入下一步。"
                )
            else:
                desc = (
                    f"（{label}）训练目标：{name}。建议配合「图片卡片」里的同名卡片做"
                    f"回合式教学(DTT)：出示指令→等待反应→记录试次（独立/语言/示范/辅助/错误）；"
                    f"连续 3 次独立正确率≥80% 视为掌握。"
                )
            out.append({
                "skill_id": sid,
                "name": name,
                "domain": domain,
                "group": f"{label}技能",
                "level": level,
                "next": None,
                "description": desc,
                "steps": steps,
                "flashcard_category": name,
            })
            used_ids.add(sid)
            used_names.add(name)
            used_cats.add(name)
    return out
