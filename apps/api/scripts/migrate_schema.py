"""数据库迁移：为 children/tasks/reports 表添加新列。PostgreSQL 版本。"""
from app.database import engine
from sqlalchemy import text


def _has_column(conn, table: str, column: str) -> bool:
    return bool(conn.execute(text(
        "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column}).first())


def main() -> None:
    with engine.begin() as conn:
        if not _has_column(conn, "children", "status_snapshot"):
            conn.execute(text("ALTER TABLE children ADD COLUMN status_snapshot JSON"))
            conn.execute(text("ALTER TABLE children ADD COLUMN last_report_at TIMESTAMP WITH TIME ZONE"))
            print("children: added status_snapshot, last_report_at")
        else:
            print("children: already has columns")
        if not _has_column(conn, "tasks", "is_daily"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN is_daily BOOLEAN DEFAULT FALSE"))
            print("tasks: added is_daily")
        else:
            print("tasks: already has is_daily")
        if not _has_column(conn, "reports", "trend"):
            conn.execute(text("ALTER TABLE reports ADD COLUMN trend VARCHAR(20)"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN trend_detail JSON"))
            print("reports: added trend, trend_detail")
        else:
            print("reports: already has columns")


if __name__ == "__main__":
    main()
