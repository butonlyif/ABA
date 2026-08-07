from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from platform_shared.schemas import ORMModel, UserOut


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    diagnosis: str | None = None
    goals: str | None = None


class ChildOut(ChildIn, ORMModel):
    id: str
    is_current: bool
    status_snapshot: dict | None = None
    last_report_at: datetime | None = None
    avatar_url: str | None = None
    avatar_seed: str | None = None
    created_at: datetime


class BootstrapOut(BaseModel):
    user: UserOut
    children: list[ChildOut]


class ChildRecordFileOut(ORMModel):
    id: str
    child_id: str
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class AssessmentSubmit(BaseModel):
    child_id: str
    answers: dict[str, int]


class AssessmentOut(ORMModel):
    id: str
    child_id: str
    score: float
    stage: str
    submitted_at: datetime
    generated_task_ids: list[str] = []


class TaskIn(BaseModel):
    child_id: str
    name: str
    description: str | None = None
    category: str = "基础能力"
    is_daily: bool = False


class TaskOut(ORMModel):
    id: str
    child_id: str
    name: str
    description: str | None
    category: str
    status: str
    source: str
    sort_order: int = 0
    is_daily: bool = False
    created_at: datetime


class TaskPatch(BaseModel):
    status: Literal["pending", "active", "completed", "paused"] | None = None
    sort_order: int | None = None


class ReorderBody(BaseModel):
    child_id: str
    order: list[dict[str, int]]  # [{"id": "...", "sort_order": 0}, ...]


class SessionIn(BaseModel):
    child_id: str
    task_id: str | None = None
    skill_name: str


class TrialIn(BaseModel):
    result: Literal["I", "V", "M", "P", "E"]


class SessionOut(ORMModel):
    id: str
    child_id: str
    task_id: str | None
    skill_name: str
    status: str
    created_at: datetime
    finished_at: datetime | None
    trials: list[str]
    percentage: int


class ReportRequest(BaseModel):
    child_id: str


class ReportOut(ORMModel):
    id: str
    child_id: str
    status: str
    title: str
    summary: str
    content: dict[str, Any]
    trend: str | None = None
    trend_detail: dict[str, Any] | None = None
    file_url: str | None = None
    created_at: datetime
