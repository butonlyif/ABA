"""认证路由：register / login / refresh / logout / me。"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import issue_tokens
from ..models import RefreshToken, User
from ..schemas import Credentials, RefreshRequest, RegisterCredentials, TokenPair, UserOut
from ..security import current_user, hash_password, token_digest, verify_password
from ..services.rate_limit import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenPair, status_code=201)
def register(body: RegisterCredentials, db: Session = Depends(get_db)):
    username = body.username.strip()
    if len(username) < 2:
        raise HTTPException(422, "用户名至少需要 2 个字符")
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "用户名已存在")
    user = User(username=username, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在")
    db.refresh(user)
    return issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
def login(body: Credentials, request: Request, db: Session = Depends(get_db)):
    limiter.check(request, "login", settings.login_rate_limit, 300)
    user = db.scalar(select(User).where(User.username == body.username))
    now = datetime.now(timezone.utc)
    if user and not user.is_active:
        raise HTTPException(403, "账户已停用")
    if user and user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now:
        raise HTTPException(429, "登录尝试过多，请稍后再试")
    ok, legacy = verify_password(body.password, user.password_hash) if user else (False, False)
    if not user or not ok:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= 5:
                user.locked_until = now + timedelta(minutes=15)
            db.commit()
        raise HTTPException(401, "用户名或密码错误")
    user.failed_logins = 0
    user.locked_until = None
    if legacy:
        user.password_hash = hash_password(body.password)
    db.commit()
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == token_digest(body.refresh_token),
        RefreshToken.revoked_at.is_(None),
    ))
    now = datetime.now(timezone.utc)
    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(401, "刷新令牌无效")
    stored.revoked_at = now
    user = db.get(User, stored.user_id)
    db.commit()
    return issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_digest(body.refresh_token)))
    if stored:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
