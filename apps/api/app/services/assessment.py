import sys
from pathlib import Path
from typing import Any


def _load_legacy_modules():
    candidates = [
        Path(__file__).resolve().parents[4] / "src" / "MVP_web",
        Path("/app/legacy"),
    ]
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
        steps = skill.get("steps") or skill.get("procedure") or []
        description = "；".join(steps[:2]) if isinstance(steps, list) else str(steps)
        tasks.append({
            "name": skill["name"],
            "category": skill["domain"],
            "description": description or f"从{skill['name']}的基础步骤开始练习。",
            "skill_id": skill_id,
        })
    return result, tasks

