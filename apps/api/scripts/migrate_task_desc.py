"""一次性迁移：把无意义描述替换为真实 skill description。

用法（容器内）：python3 -m scripts.migrate_task_desc
"""
import sys
from pathlib import Path

# 加载 legacy 模块
for candidate in [Path("/app/legacy")]:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from utils import curriculum  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Task  # noqa: E402
from sqlalchemy import select  # noqa: E402


def main() -> None:
    skill_map = {item["name"]: item for item in curriculum.SKILLS}
    db = SessionLocal()
    try:
        tasks = db.scalars(select(Task).where(Task.source == "assessment")).all()
        updated = 0
        for task in tasks:
            skill = skill_map.get(task.name)
            if not skill:
                continue
            real_desc = skill.get("description") or ""
            # 只替换"从XXX的基础步骤开始练习。"这种模板字符串
            if task.description and real_desc and "的基础步骤开始练习" in task.description:
                task.description = real_desc
                updated += 1
        db.commit()
        print(f"迁移完成：{updated}/{len(tasks)} 个任务的描述已更新")
    finally:
        db.close()


if __name__ == "__main__":
    main()
