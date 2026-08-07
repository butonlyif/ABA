"""共享依赖函数：admin_user / expert_user / issue_tokens / add_ai_usage。"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import AiUsage, RefreshToken, User
from .schemas import TokenPair
from .security import create_access_token, current_user, random_refresh_token, token_digest


def add_ai_usage(db: Session, user: User, product: str, call) -> None:
    db.add(AiUsage(
        user_id=user.id, product=product, provider=call.provider, model=call.model,
        success=call.success, fallback=call.fallback, prompt_tokens=call.prompt_tokens,
        completion_tokens=call.completion_tokens, latency_ms=call.latency_ms,
        error_type=call.error_type,
    ))


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


def expert_user(user: User = Depends(current_user)) -> User:
    if user.role != "expert":
        raise HTTPException(403, "需要专家权限")
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    settings = get_settings()
    raw = random_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_digest(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    ))
    db.commit()
    return TokenPair(access_token=create_access_token(user), refresh_token=raw)
