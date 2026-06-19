"""
ABA 干预建议引擎
分析训练试次数据中的错误模式，输出具体操作建议。

试次符号（新版4级）：
  I  = Independent      独立正确（无辅助）
  V  = Verbal prompt    语言提示后正确
  M  = Model prompt     示范后正确
  P  = Physical assist  身体辅助后正确
  E  = Error            错误/无反应

正确率 = I次数 / 总试次（只算独立正确）
辅助依赖率 = (V+M+P) / 总试次
"""

from typing import List, Dict, Tuple


# ─── 干预程序库 ───────────────────────────────────────────────

PROCEDURES = {

    "four_step_error_correction": {
        "title": "4步纠错法",
        "when": "出现错误时立即使用",
        "steps": [
            "① **不理会错误**：孩子回答错误后，保持中立表情，不说「不对」或「错了」，停顿1-2秒。",
            "② **给出正确答案（示范）**：家长直接说出或指出正确答案，如「这是苹果」，同时指向图片。",
            "③**转移试次**：立刻给出一个孩子已经会的简单题（已掌握的技能），让孩子成功一次并给予强化。",
            "④ **返回原题**：重新呈现刚才出错的题目，观察孩子的反应，若正确立即强化。",
        ],
        "notes": "关键：步骤②不要带情绪，步骤③一定要做，它能帮助孩子在情绪上从错误中恢复。",
    },

    "errorless_learning": {
        "title": "无错误学习法",
        "when": "孩子连续3次以上出错，或对某个题目持续回避",
        "steps": [
            "① **降低难度**：暂时减少选项（如3选1变成2选1，或先只摆正确答案旁边放1个干扰项）。",
            "② **立即辅助**：在发出指令后0.5-1秒内就给予最高效的辅助（示范或身体辅助），不等孩子出错。",
            "③ **逐步增加难度**：孩子在辅助下连续3次正确后，开始减少辅助，观察是否能独立完成。",
            "④ **保持高成功率**：整个练习中错误率控制在20%以下，让孩子建立信心。",
        ],
        "notes": "核心原则：预防错误比纠正错误更有效，高成功率有助于维持孩子的学习动机。",
    },

    "prompt_fading": {
        "title": "辅助递减策略",
        "when": "孩子长期依赖辅助才能正确，独立完成率低",
        "steps": [
            "① **确认当前辅助级别**：你现在使用的是哪种辅助？（身体辅助 → 示范 → 语言提示 → 独立）",
            "② **向上退一级**：如果一直用身体辅助，改用示范辅助；一直用示范，改用语言提示。",
            "③ **时间延迟法**：给出指令后，等3-5秒再给辅助（而不是立即辅助），给孩子尝试独立的机会。",
            "④ **强化独立反应**：一旦孩子没有等辅助就主动完成，立刻给予更大的强化（最喜欢的奖励）。",
            "⑤ **记录独立率变化**：每次训练记录有多少次是独立完成的，以此判断递减速度是否合适。",
        ],
        "notes": "辅助递减太快会导致挫败感，太慢会形成辅助依赖。通常每3-5次连续独立正确后才退一级辅助。",
    },

    "motivation_check": {
        "title": "强化物和动机检查",
        "when": "孩子之前会的技能突然变差，或训练中出现回避/逃跑行为",
        "steps": [
            "① **偏好评估**：在训练前先做2分钟偏好评估——把5-6种食物或玩具放在桌上，观察孩子选哪个，用选择频率最高的作为强化物。",
            "② **换新强化物**：如果同一种奖励用了超过2周，孩子可能已经饱足，换一个孩子最近感兴趣的新奇物品。",
            "③ **减少练习时长**：如果孩子训练后期出错多，考虑缩短每组试次（从10次减到5次），提高强化密度。",
            "④ **检查饱足状态**：训练前不要让孩子吃太饱（食物强化物）或玩太多（玩具强化物）。",
            "⑤ **配对强化**：家长自己先和孩子玩一会儿喜欢的游戏，再开始训练，提升孩子对家长的配合意愿。",
        ],
        "notes": "如果以上调整后2-3次训练仍无改善，可能需要检查前备技能是否已掌握，或咨询专业人士。",
    },

    "prerequisite_review": {
        "title": "回顾前备技能",
        "when": "孩子在当前技能上长期（5次以上）正确率低于40%",
        "steps": [
            "① **识别前备技能**：当前训练项目需要哪些基础能力？（如：命名需要先会指认；分类需要先会配对）",
            "② **测试前备技能**：用10个试次快速测试前备技能，看是否已真正掌握。",
            "③ **暂停当前目标**：如果前备技能未掌握（正确率<80%），先返回训练前备技能。",
            "④ **制定过渡计划**：用1-2周巩固前备技能后，再重新引入当前目标，这次通常会快很多。",
        ],
        "notes": "ABA的技能是阶梯式的，跳过前备技能直接训练高难度项目往往事倍功半。",
    },

    "generalization": {
        "title": "泛化训练",
        "when": "孩子在练习材料上正确率高，但换了人或换了地方就不会了",
        "steps": [
            "① **换材料**：换不同图片（同一概念的不同图）、不同颜色的卡片、真实物品替代图片。",
            "② **换训练者**：让爸爸、爷爷奶奶、老师也来做同样的训练，扩大反应的泛化。",
            "③ **换地点**：从桌面搬到客厅、餐厅、户外，让技能在不同环境中都能出现。",
            "④ **嵌入日常**：在日常活动中随机测试技能（如逛超市时指认图片上的食物）。",
        ],
        "notes": "泛化是ABA中最容易被忽略但最重要的步骤，技能只有在自然环境中出现才算真正习得。",
    },
}


# ─── 模式分析 ────────────────────────────────────────────────

def analyze_trials(trials: List[str]) -> Dict:
    """
    分析一个 session 的试次序列，返回统计和模式标记。
    trials: ["I","V","E","M","I", ...]
    """
    if not trials:
        return {}

    total = len(trials)
    counts = {k: trials.count(k) for k in ("I", "V", "M", "P", "E")}
    independent = counts["I"]
    prompted = counts["V"] + counts["M"] + counts["P"]
    errors = counts["E"]

    indep_rate = round(independent / total * 100)
    prompt_rate = round(prompted / total * 100)
    error_rate = round(errors / total * 100)

    # 连续错误最长串
    max_consec_errors = 0
    cur = 0
    for t in trials:
        if t == "E":
            cur += 1
            max_consec_errors = max(max_consec_errors, cur)
        else:
            cur = 0

    # 主要辅助类型
    prompt_breakdown = {k: counts[k] for k in ("V", "M", "P") if counts[k] > 0}
    dominant_prompt = max(prompt_breakdown, key=prompt_breakdown.get) if prompt_breakdown else None

    return {
        "total": total,
        "independent": independent,
        "prompted": prompted,
        "errors": errors,
        "indep_rate": indep_rate,
        "prompt_rate": prompt_rate,
        "error_rate": error_rate,
        "max_consec_errors": max_consec_errors,
        "dominant_prompt": dominant_prompt,
        "counts": counts,
    }


def get_intervention_suggestions(
    trials: List[str],
    history_pcts: List[int] = None,
) -> List[Dict]:
    """
    根据当前 session 的试次和历史正确率，返回有序的干预建议列表。
    每条建议包含：priority(优先级1-3), procedure(程序key), reason(触发原因说明)
    """
    stats = analyze_trials(trials)
    if not stats:
        return []

    suggestions = []
    history = history_pcts or []

    # ── 规则1：连续3次以上错误 → 4步纠错法（最高优先级）
    if stats["max_consec_errors"] >= 3:
        suggestions.append({
            "priority": 1,
            "procedure": "four_step_error_correction",
            "reason": f"检测到连续 {stats['max_consec_errors']} 次错误，需要立即使用4步纠错法打断错误链。",
        })

    # ── 规则2：错误率>50% 且历史也低 → 无错误学习
    if stats["error_rate"] >= 50:
        if len(history) < 2 or (history and sum(history[-3:]) / len(history[-3:]) < 50):
            suggestions.append({
                "priority": 1,
                "procedure": "errorless_learning",
                "reason": f"本次错误率达 {stats['error_rate']}%，难度可能超出当前水平，建议切换到无错误学习法。",
            })

    # ── 规则3：辅助率>60% → 辅助递减
    if stats["prompt_rate"] >= 60 and stats["total"] >= 5:
        dominant = stats.get("dominant_prompt")
        prompt_name = {"V": "语言提示", "M": "示范辅助", "P": "身体辅助"}.get(dominant, "辅助")
        suggestions.append({
            "priority": 2,
            "procedure": "prompt_fading",
            "reason": f"本次 {stats['prompt_rate']}% 的试次依赖{prompt_name}，独立正确率仅 {stats['indep_rate']}%。建议启动辅助递减计划。",
        })

    # ── 规则4：历史波动大（曾经好过，最近下滑）→ 动机检查
    if len(history) >= 3:
        peak = max(history)
        recent_avg = sum(history[-2:]) / 2
        if peak >= 70 and recent_avg < peak - 30:
            suggestions.append({
                "priority": 2,
                "procedure": "motivation_check",
                "reason": f"该技能历史最高正确率达 {peak}%，但最近下滑至 {round(recent_avg)}%，可能是强化物饱足或情绪状态变化。",
            })

    # ── 规则5：历史5次以上平均<40% → 检查前备技能
    if len(history) >= 5 and sum(history) / len(history) < 40:
        suggestions.append({
            "priority": 3,
            "procedure": "prerequisite_review",
            "reason": f"该技能已训练 {len(history)} 次，平均正确率 {round(sum(history)/len(history))}%，长期无进展，建议检查前备技能是否已掌握。",
        })

    # ── 规则6：独立率>80% 但辅助率有记录（说明在泛化阶段）→ 泛化
    if stats["indep_rate"] >= 80 and len(history) >= 3 and all(p >= 80 for p in history[-3:]):
        suggestions.append({
            "priority": 3,
            "procedure": "generalization",
            "reason": f"连续多次独立正确率≥80%，已达掌握标准！下一步重点是泛化到不同材料和环境。",
        })

    # 去重（同一procedure只保留最高priority的）
    seen = {}
    for s in sorted(suggestions, key=lambda x: x["priority"]):
        if s["procedure"] not in seen:
            seen[s["procedure"]] = s
    return list(seen.values())


def get_procedure(key: str) -> Dict:
    return PROCEDURES.get(key, {})


def format_suggestion_for_display(suggestion: Dict) -> Dict:
    """将建议和完整程序合并，供UI显示"""
    proc = get_procedure(suggestion["procedure"])
    return {
        **suggestion,
        "title": proc.get("title", ""),
        "when": proc.get("when", ""),
        "steps": proc.get("steps", []),
        "notes": proc.get("notes", ""),
    }
