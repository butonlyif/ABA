from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(ORMModel):
    id: str
    username: str
    role: str


class AdminUserCreate(Credentials):
    role: Literal["user", "expert", "admin"] = "user"


class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    diagnosis: str | None = None
    goals: str | None = None


class ChildOut(ChildIn, ORMModel):
    id: str
    is_current: bool
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


class TaskOut(ORMModel):
    id: str
    child_id: str
    name: str
    description: str | None
    category: str
    status: str
    source: str
    created_at: datetime


class TaskPatch(BaseModel):
    status: Literal["pending", "active", "completed", "paused"]


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
    file_url: str | None = None
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    child_id: str | None = None


class ChatOut(ORMModel):
    id: str
    product: str
    role: str
    content: str
    sources: list
    created_at: datetime


class ChatAnswer(BaseModel):
    answer: str
    sources: list[dict[str, str]] = []


class MoodIn(BaseModel):
    mood: str = Field(min_length=1, max_length=40)
    intensity: int = Field(default=3, ge=1, le=5)
    note: str | None = Field(default=None, max_length=1000)


class MoodOut(ORMModel):
    id: str
    mood: str
    intensity: int
    note: str | None
    entry_date: date


class JournalIn(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    prompt: str | None = None


class JournalOut(ORMModel):
    id: str
    content: str
    prompt: str | None
    created_at: datetime


class ExpertSelect(BaseModel):
    expert_id: str


class ExpertQuestion(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ExpertReply(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ExpertProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    specialties: list[str] = Field(default_factory=list, max_length=10)
    bio: str = Field(default="", max_length=2000)
    credentials: str = Field(default="", max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    accepting_clients: bool = True
    max_clients: int = Field(default=30, ge=1, le=200)
