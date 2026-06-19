"""
====================================
ABA智能助手 - 任务生成模块
====================================

根据孩子的干预目标自动生成具体任务建议：
- 分析干预目标
- 生成可执行的具体活动
- 分类管理任务
"""

from typing import Dict, List, Optional


TASK_TEMPLATES = {
    "语言": [
        {
            "name": "命名练习",
            "description": "准备孩子喜欢的图片卡或实物，每次展示2-3张，问'这是什么？'，等待3秒后给予提示或辅助",
            "category": "语言训练",
            "frequency": "每天2-3次，每次10-15分钟"
        },
        {
            "name": "仿说训练",
            "description": "选择简单音节或单词（如：啊、喔、爸、妈），家长先说一遍，让孩子模仿发音，及时给予强化",
            "category": "语言训练",
            "frequency": "每天3-5分钟，可分散在多个时段"
        },
        {
            "name": "需求表达",
            "description": "将孩子喜欢的零食/玩具放在看得见但够不到的地方，等待孩子主动提需求后给予，增强沟通动机",
            "category": "语言训练",
            "frequency": "日常生活中随时进行"
        },
        {
            "name": "绘本阅读",
            "description": "选择简单图画书，指着图片问'这是什么？'，让孩子命名，适当给予提示和肯定",
            "category": "语言训练",
            "frequency": "每天1次，每次5-10分钟"
        }
    ],
    "社交": [
        {
            "name": "呼名反应",
            "description": "叫孩子的名字，观察是否有眼神接触或转头回应。如果没有，及时给予辅助并强化正确反应",
            "category": "社交训练",
            "frequency": "每天多次练习"
        },
        {
            "name": "目光接触",
            "description": "在孩子面前放置喜欢的零食，说'看我'，等待目光对视后立即给予强化，逐步延长目光接触时间",
            "category": "社交训练",
            "frequency": "每天5-10分钟练习"
        },
        {
            "name": "轮流游戏",
            "description": "选择简单的轮流游戏（如：推小车、搭积木），家长和孩子交替进行，培养等待和轮流意识",
            "category": "社交训练",
            "frequency": "每天2-3次，每次5-10分钟"
        },
        {
            "name": "分享游戏",
            "description": "准备两份相同的零食或玩具，教孩子'给我一个'并递过来，强化后说'谢谢你'并还给他一个",
            "category": "社交训练",
            "frequency": "每天练习2-3次"
        }
    ],
    "行为": [
        {
            "name": "桌面教学-指令服从",
            "description": "给出简单指令（如：坐下、拍手、摸头），孩子完成后立即给予强化物，逐步增加指令复杂度",
            "category": "行为训练",
            "frequency": "每天2-3次，每次10-15分钟"
        },
        {
            "name": "等待训练",
            "description": "孩子想要某样东西时，让他等待5-10秒，逐步延长等待时间，完成后给予强化",
            "category": "行为训练",
            "frequency": "日常生活中随时进行"
        },
        {
            "name": "情绪识别",
            "description": "展示不同情绪表情的图片（开心、生气、难过等），教孩子识别和命名'这是开心的表情'",
            "category": "行为训练",
            "frequency": "每天1-2次，每次5分钟"
        },
        {
            "name": "自我调节活动",
            "description": "感觉孩子情绪即将失控前，提供感官调节活动（如：挤压压力球、荡秋千、深呼吸）",
            "category": "行为训练",
            "frequency": "根据孩子状态随时进行"
        }
    ],
    "生活": [
        {
            "name": "如厕训练",
            "description": "建立规律的如厕时间表，定时带孩子上厕所，成功后给予口头表扬和小强化物",
            "category": "生活自理",
            "frequency": "每2-3小时一次"
        },
        {
            "name": "穿衣训练",
            "description": "分解穿衣服步骤，教孩子独立完成简单步骤（如：穿上衣），逐步增加任务复杂度",
            "category": "生活自理",
            "frequency": "每天早晚穿衣时练习"
        },
        {
            "name": "洗手步骤",
            "description": "用图片卡展示洗手步骤：开水龙头→湿手→搓泡泡→冲洗→擦干，教孩子按顺序完成",
            "category": "生活自理",
            "frequency": "每次如厕后练习"
        },
        {
            "name": "餐桌礼仪",
            "description": "进餐时教孩子正确使用餐具，鼓励'我要...''谢谢'等简单表达，培养良好用餐习惯",
            "category": "生活自理",
            "frequency": "每餐时练习"
        }
    ],
    "认知": [
        {
            "name": "配对练习",
            "description": "准备相同的图片卡或实物，让孩子进行完全匹配（一样的放一起），完成后给予强化",
            "category": "认知训练",
            "frequency": "每天1-2次，每次10分钟"
        },
        {
            "name": "分类练习",
            "description": "准备不同类别的物品或图片，教孩子按颜色、形状或类别进行分类（如：红色的放一起）",
            "category": "认知训练",
            "frequency": "每天1次，每次10分钟"
        },
        {
            "name": "数数训练",
            "description": "利用实物（糖果、积木）教孩子数数，从1-5开始，逐步增加数量概念",
            "category": "认知训练",
            "frequency": "每天1-2次，每次5-10分钟"
        },
        {
            "name": "简单拼图",
            "description": "选择2-4片的简单拼图，家长先示范如何拼，观察孩子独立完成情况并给予辅助",
            "category": "认知训练",
            "frequency": "每天1次，每次5-10分钟"
        }
    ],
    "感统": [
        {
            "name": "秋千活动",
            "description": "在安全情况下让孩子坐或趴在秋千上，轻轻晃动，促进前庭觉输入，帮助调节情绪",
            "category": "感统训练",
            "frequency": "每天2-3次，每次5分钟"
        },
        {
            "name": "跳床跳跃",
            "description": "在蹦床上跳跃，帮助孩子消耗多余能量，促进本体觉输入，有助于情绪调节",
            "category": "感统训练",
            "frequency": "每天1-2次，每次3-5分钟"
        },
        {
            "name": "沙盘/沙子游戏",
            "description": "提供沙子或大米等触觉材料，让孩子用手指或小工具玩耍，促进触觉发展",
            "category": "感统训练",
            "frequency": "每天1次，每次10分钟"
        },
        {
            "name": "推拉重物",
            "description": "让孩子推拉较重的玩具车、瑜伽球等，促进本体觉输入，帮助调节身体感觉",
            "category": "感统训练",
            "frequency": "每天1-2次，每次5分钟"
        }
    ]
}


class TaskGenerator:
    """任务生成器"""

    def __init__(self):
        self.templates = TASK_TEMPLATES

    def generate_initial_tasks(
        self,
        intervention_goals: str,
        diagnosis: Optional[str] = None
    ) -> List[Dict]:
        """根据干预目标生成初始任务"""

        if not intervention_goals:
            return self._get_default_tasks()

        goals_lower = intervention_goals.lower()

        selected_tasks = []
        task_names = set()

        if any(kw in goals_lower for kw in ["语言", "说话", "表达", "沟通", "词汇", "发音", "仿说"]):
            tasks = self._get_tasks_by_category("语言")
            for t in tasks[:3]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if any(kw in goals_lower for kw in ["社交", "互动", "目光", "轮流", "分享", "朋友"]):
            tasks = self._get_tasks_by_category("社交")
            for t in tasks[:3]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if any(kw in goals_lower for kw in ["行为", "情绪", "问题行为", "自我", "调节", "服从"]):
            tasks = self._get_tasks_by_category("行为")
            for t in tasks[:2]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if any(kw in goals_lower for kw in ["生活", "自理", "如厕", "穿衣", "吃饭", "睡眠"]):
            tasks = self._get_tasks_by_category("生活")
            for t in tasks[:2]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if any(kw in goals_lower for kw in ["认知", "学习", "理解", "智力", "配对", "分类", "数数"]):
            tasks = self._get_tasks_by_category("认知")
            for t in tasks[:2]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if any(kw in goals_lower for kw in ["感统", "感觉", "本体", "前庭", "触觉", "运动"]):
            tasks = self._get_tasks_by_category("感统")
            for t in tasks[:2]:
                if t["name"] not in task_names:
                    selected_tasks.append(t)
                    task_names.add(t["name"])

        if not selected_tasks:
            return self._get_default_tasks()

        return selected_tasks

    def _get_tasks_by_category(self, category: str) -> List[Dict]:
        """获取指定类别的任务"""
        return self.templates.get(category, [])

    def _get_default_tasks(self) -> List[Dict]:
        """获取默认任务（没有明确目标时）"""
        default_tasks = []
        for category in ["语言", "社交", "行为", "认知"]:
            tasks = self._get_tasks_by_category(category)
            if tasks:
                default_tasks.append(tasks[0])
        return default_tasks

    def get_all_task_templates(self) -> Dict[str, List[Dict]]:
        """获取所有任务模板"""
        return self.templates

    def generate_task_suggestions(
        self,
        category: str,
        limit: int = 3
    ) -> List[Dict]:
        """获取指定类别的任务建议"""
        tasks = self.templates.get(category, [])
        return tasks[:limit]

    def generate_from_training_data(self, sessions: List[Dict]) -> List[Dict]:
        """
        根据近期训练记录生成任务建议。
        sessions: training_data.get_sessions() 返回的列表（已含统计）

        逻辑：
        - 按技能名称聚合，取最近 N 次的正确率
        - 连续 3 次 ≥ 80%  → 已掌握，建议推进下一步
        - 平均正确率 < 50% 且有 ≥ 3 次记录 → 卡住，建议调整策略
        - 其余 → 进行中，建议继续练习
        """
        from collections import defaultdict

        # 按技能聚合（只取 finished sessions）
        skill_map: Dict[str, List[int]] = defaultdict(list)
        for s in sessions:
            if not s.get("finished"):
                continue
            if s["total"] > 0:
                skill_map[s["skill_name"]].append(s["percentage"])

        tasks = []
        seen = set()

        for skill, pcts in skill_map.items():
            if skill in seen:
                continue
            seen.add(skill)

            recent = pcts[-5:]  # 最近5次
            last3 = pcts[-3:]

            # 已掌握
            if len(last3) >= 3 and all(p >= 80 for p in last3):
                tasks.append({
                    "name": f"推进：{skill}",
                    "description": (
                        f"「{skill}」已连续3次达到80%掌握标准（最近正确率：{last3[-1]}%）。"
                        "建议：提高难度、换新刺激材料，或进入下一个目标技能。"
                    ),
                    "category": "认知训练",
                    "source": "training",
                    "skill_name": skill,
                    "status": "mastered",
                    "latest_pct": last3[-1],
                })
            # 卡住了
            elif len(recent) >= 3 and sum(recent) / len(recent) < 50:
                avg = round(sum(recent) / len(recent))
                tasks.append({
                    "name": f"调整策略：{skill}",
                    "description": (
                        f"「{skill}」近{len(recent)}次平均正确率仅 {avg}%。"
                        "建议：降低任务难度、增加辅助、换更有动机的强化物，或暂时休息后再尝试。"
                    ),
                    "category": "认知训练",
                    "source": "training",
                    "skill_name": skill,
                    "status": "struggling",
                    "latest_pct": pcts[-1],
                })
            # 进行中
            else:
                tasks.append({
                    "name": f"继续练习：{skill}",
                    "description": (
                        f"「{skill}」目前正确率 {pcts[-1]}%，正在进步中。"
                        "建议今天继续安排一轮训练，保持数据连续性。"
                    ),
                    "category": "认知训练",
                    "source": "training",
                    "skill_name": skill,
                    "status": "in_progress",
                    "latest_pct": pcts[-1],
                })

        # 掌握的排前面，卡住的其次，进行中最后
        order = {"mastered": 0, "struggling": 1, "in_progress": 2}
        tasks.sort(key=lambda t: order.get(t.get("status", "in_progress"), 2))
        return tasks
