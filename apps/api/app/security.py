import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, stored: str) -> tuple[bool, bool]:
    try:
        return hasher.verify(stored, password), False
    except VerifyMismatchError:
        legacy = hashlib.sha256(f"{password}aba_assistant_salt_2024".encode()).hexdigest()
        return secrets.compare_digest(legacy, stored), secrets.compare_digest(legacy, stored)
    except Exception:
        return False, False


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user.id, "role": user.role, "exp": expires}, settings.jwt_secret, algorithm="HS256")


def random_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(401, "需要登录")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"])
        user = db.scalar(select(User).where(User.id == payload["sub"]))
    except (JWTError, KeyError):
        user = None
    if not user:
        raise HTTPException(401, "登录已失效")
    if not user.is_active:
        raise HTTPException(403, "账户已停用")
    return user
