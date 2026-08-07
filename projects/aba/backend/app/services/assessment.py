import sys
from pathlib import Path
from typing import Any


def _load_legacy_modules():
    candidates = [
        Path("/app/legacy"),
    ]
    parents = Path(__file__).resolve().parents
    if len(parents) > 4:
        candidates.append(parents[4] / "src" / "MVP_web")
    for candidate in candidates:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    from utils import assessment as legacy_assessment
    from utils import curriculum
    return legacy_assessment, curriculum


def questions() -> list[dict[str, Any]]:
    assessment, _ = _load_legacy_modules()
    return [
        {
            "id": item["id"],
            "domain": item["domain"],
            "domain_name": assessment.DOMAIN_NAMES[item["domain"]],
            "level": item["level"],
            "stage": item["stage"],
            "text": item["question"],
        }
        for item in assessment.QUESTIONS
    ]


def score_and_tasks(answers: dict[str, int]) -> tuple[dict, list[dict]]:
    assessment, curriculum = _load_legacy_modules()
    boolean_answers = {key: value >= 2 for key, value in answers.items()}
    result = assessment.score_assessment(boolean_answers)
    skill_map = {item["skill_id"]: item for item in curriculum.SKILLS}
    tasks = []
    for skill_id in result["recommended_skill_ids"][:12]:
        skill = skill_map.get(skill_id)
        if not skill:
            continue
        description = skill.get("description") or ""
        if not description:
            steps = skill.get("steps") or skill.get("procedure") or []
            description = "；".join(steps[:2]) if isinstance(steps, list) and steps else f"从{skill['name']}的基础步骤开始练习。"
        tasks.append({
            "name": skill["name"],
            "category": skill["domain"],
            "description": description,
            "skill_id": skill_id,
        })
    return result, tasks


def skill_catalog() -> list[dict[str, Any]]:
    """返回全部训练技能模板，按领域分组，供"添加训练"指引使用。"""
    assessment, curriculum = _load_legacy_modules()
    domain_names = assessment.DOMAIN_NAMES
    groups: dict[str, list[dict]] = {}
    for skill in curriculum.SKILLS:
        domain = skill.get("domain", "其他")
        domain_label = domain_names.get(domain, domain)
        groups.setdefault(domain_label, []).append({
            "name": skill["name"],
            "category": domain_label,
            "description": skill.get("description") or "",
            "level": skill.get("level", 1),
            "group": skill.get("group", ""),
            "flashcard_category": skill.get("flashcard_category"),
        })
    return [
        {"domain": domain, "count": len(items), "skills": items}
        for domain, items in sorted(groups.items())
    ]
