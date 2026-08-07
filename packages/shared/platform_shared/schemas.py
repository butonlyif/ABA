from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Credentials(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=4, max_length=128)


class RegisterCredentials(Credentials):
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
