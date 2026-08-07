from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from platform_shared.schemas import ORMModel


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


class CoachGrowthStateIn(BaseModel):
    sessions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class CoachGrowthStateOut(ORMModel):
    sessions: list[dict[str, Any]]
    updated_at: datetime


class WeeklyReportExport(BaseModel):
    week_start: str
    week_end: str
    mood_count: int = Field(ge=0)
    journal_count: int = Field(ge=0)
    chat_count: int = Field(ge=0)
    content: str = Field(min_length=1, max_length=20000)
