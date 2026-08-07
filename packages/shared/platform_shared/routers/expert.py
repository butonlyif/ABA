"""专家系统路由（ABA 与 Coach 共享）：专家列表/选择/资料/消息/通知。"""

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, UnidentifiedImageError
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import expert_user
from ..models import AuditLog, ExpertAssignment, ExpertMessage, ExpertProfile, User
from ..schemas import ExpertProfileIn, ExpertQuestion, ExpertReply, ExpertSelect
from ..security import current_user

router = APIRouter(tags=["expert"])
settings = get_settings()
upload_root = Path(settings.upload_path)


@router.get("/api/v1/experts")
def list_experts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    selected = db.get(ExpertAssignment, user.id)
    if selected and selected.status != "active":
        selected = None
    experts = db.scalars(select(User).where(User.role == "expert", User.is_active.is_(True)).order_by(User.username)).all()
    items = []
    for item in experts:
        profile = db.get(ExpertProfile, item.id)
        client_count = db.scalar(select(func.count()).select_from(ExpertAssignment).where(
            ExpertAssignment.expert_id == item.id, ExpertAssignment.status == "active"
        ))
        accepting = profile.accepting_clients if profile else True
        max_clients = profile.max_clients if profile else 30
        if not accepting and (not selected or selected.expert_id != item.id):
            continue
        items.append({
            "id": item.id,
            "name": profile.display_name if profile else item.username,
            "title": profile.title if profile else "家庭支持专家",
            "specialties": profile.specialties if profile else [],
            "bio": profile.bio if profile else "",
            "credentials": profile.credentials if profile else "",
            "avatar_url": profile.avatar_url if profile else None,
            "accepting_clients": accepting and client_count < max_clients,
            "client_count": client_count,
        })
    return {
        "selected_expert_id": selected.expert_id if selected else None,
        "items": items,
    }


@router.put("/api/v1/experts/selection")
def select_expert(body: ExpertSelect, user: User = Depends(current_user), db: Session = Depends(get_db)):
    expert = db.scalar(select(User).where(User.id == body.expert_id, User.role == "expert"))
    if not expert:
        raise HTTPException(404, "专家不存在")
    profile = db.get(ExpertProfile, expert.id)
    client_count = db.scalar(select(func.count()).select_from(ExpertAssignment).where(
        ExpertAssignment.expert_id == expert.id, ExpertAssignment.status == "active"
    ))
    if profile and (not profile.accepting_clients or client_count >= profile.max_clients):
        raise HTTPException(409, "该专家目前暂停接收新客户")
    assignment = db.get(ExpertAssignment, user.id)
    if assignment:
        assignment.expert_id = expert.id
        assignment.status = "active"
        assignment.created_at = datetime.now(timezone.utc)
        assignment.ended_at = None
    else:
        db.add(ExpertAssignment(user_id=user.id, expert_id=expert.id))
    db.add(AuditLog(
        user_id=user.id, action="expert.selected", resource_type="expert_assignment",
        resource_id=expert.id, details={},
    ))
    db.commit()
    return {"expert_id": expert.id, "name": expert.username}


@router.delete("/api/v1/experts/selection", status_code=204)
def release_expert(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if assignment and assignment.status == "active":
        assignment.status = "ended"
        assignment.ended_at = datetime.now(timezone.utc)
        db.add(AuditLog(
            user_id=user.id, action="expert.released", resource_type="expert_assignment",
            resource_id=assignment.expert_id, details={},
        ))
        db.commit()


@router.get("/api/v1/expert/profile")
def get_expert_profile(expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    profile = db.get(ExpertProfile, expert.id)
    return {
        "display_name": profile.display_name if profile else expert.username,
        "title": profile.title if profile else "家庭支持专家",
        "specialties": profile.specialties if profile else [],
        "bio": profile.bio if profile else "",
        "credentials": profile.credentials if profile else "",
        "avatar_url": profile.avatar_url if profile else None,
        "accepting_clients": profile.accepting_clients if profile else True,
        "max_clients": profile.max_clients if profile else 30,
    }


@router.put("/api/v1/expert/profile")
def update_expert_profile(body: ExpertProfileIn, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    profile = db.get(ExpertProfile, expert.id)
    if profile:
        for key, value in body.model_dump().items():
            setattr(profile, key, value)
    else:
        profile = ExpertProfile(user_id=expert.id, **body.model_dump())
        db.add(profile)
    db.add(AuditLog(
        user_id=expert.id, action="expert.profile_updated", resource_type="expert_profile",
        resource_id=expert.id, details={"accepting_clients": body.accepting_clients},
    ))
    db.commit()
    return get_expert_profile(expert, db)


@router.post("/api/v1/expert/profile/avatar")
async def upload_expert_avatar(
    avatar: UploadFile = File(...), expert: User = Depends(expert_user), db: Session = Depends(get_db),
):
    if avatar.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "仅支持 JPG、PNG 或 WebP 图片")
    content = await avatar.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 5MB")
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "图片文件无效")
    image = image.convert("RGB")
    edge = min(image.size)
    left = (image.width - edge) // 2
    top = (image.height - edge) // 2
    image = image.crop((left, top, left + edge, top + edge))
    image.thumbnail((640, 640))
    avatar_dir = upload_root / "expert_avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    target = avatar_dir / f"{expert.id}.webp"
    image.save(target, "WEBP", quality=88, method=6)
    profile = db.get(ExpertProfile, expert.id)
    avatar_url = f"/api/v1/expert-avatars/{expert.id}"
    if profile:
        profile.avatar_url = avatar_url
    else:
        db.add(ExpertProfile(user_id=expert.id, display_name=expert.username, avatar_url=avatar_url))
    db.add(AuditLog(
        user_id=expert.id, action="expert.avatar_updated", resource_type="expert_profile",
        resource_id=expert.id, details={"content_type": "image/webp"},
    ))
    db.commit()
    return {"avatar_url": avatar_url}


@router.get("/api/v1/expert-avatars/{expert_id}", include_in_schema=False)
def expert_avatar(expert_id: str, db: Session = Depends(get_db)):
    expert = db.scalar(select(User).where(User.id == expert_id, User.role == "expert", User.is_active.is_(True)))
    target = upload_root / "expert_avatars" / f"{expert_id}.webp"
    if not expert or not target.is_file():
        raise HTTPException(404, "专家头像不存在")
    return FileResponse(target, media_type="image/webp", headers={"Cache-Control": "public, max-age=3600"})


@router.post("/api/v1/expert/questions", status_code=201)
def ask_expert(body: ExpertQuestion, user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if not assignment or assignment.status != "active":
        raise HTTPException(409, "请先选择专家")
    message = ExpertMessage(client_id=user.id, expert_id=assignment.expert_id, sender_id=user.id, content=body.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "created_at": message.created_at}


@router.get("/api/v1/expert/conversation")
def client_expert_conversation(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    if not assignment or assignment.status != "active":
        return {"items": []}
    rows = db.scalars(select(ExpertMessage).where(
        ExpertMessage.client_id == user.id, ExpertMessage.expert_id == assignment.expert_id
    ).order_by(ExpertMessage.created_at)).all()
    for item in rows:
        if item.sender_id == assignment.expert_id and not item.read_at:
            item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"items": [{"id": item.id, "sender": "client" if item.sender_id == user.id else "expert", "content": item.content, "created_at": item.created_at} for item in rows]}


@router.get("/api/v1/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    assignment = db.get(ExpertAssignment, user.id)
    expert_unread = 0
    if assignment and assignment.status == "active":
        expert_unread = db.scalar(select(func.count()).select_from(ExpertMessage).where(
            ExpertMessage.client_id == user.id, ExpertMessage.expert_id == assignment.expert_id,
            ExpertMessage.sender_id == assignment.expert_id, ExpertMessage.read_at.is_(None),
        ))
    return {"expert_unread": expert_unread}


@router.get("/api/v1/expert/clients")
def expert_clients(expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignments = db.scalars(select(ExpertAssignment).where(
        ExpertAssignment.expert_id == expert.id, ExpertAssignment.status == "active"
    )).all()
    items = []
    for assignment in assignments:
        client = db.get(User, assignment.user_id)
        unread = db.scalar(select(func.count()).select_from(ExpertMessage).where(
            ExpertMessage.client_id == client.id, ExpertMessage.expert_id == expert.id,
            ExpertMessage.sender_id == client.id, ExpertMessage.read_at.is_(None),
        ))
        latest = db.scalar(select(ExpertMessage).where(
            ExpertMessage.client_id == client.id, ExpertMessage.expert_id == expert.id
        ).order_by(ExpertMessage.created_at.desc()))
        items.append({"id": client.id, "name": client.username, "unread": unread, "latest": latest.content if latest else None})
    return {"items": items}


@router.get("/api/v1/expert/clients/{client_id}/messages")
def expert_client_messages(client_id: str, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户不存在")
    rows = db.scalars(select(ExpertMessage).where(
        ExpertMessage.client_id == client_id, ExpertMessage.expert_id == expert.id
    ).order_by(ExpertMessage.created_at)).all()
    for item in rows:
        if item.sender_id == client_id and not item.read_at:
            item.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"items": [{"id": item.id, "sender": "expert" if item.sender_id == expert.id else "client", "content": item.content, "created_at": item.created_at} for item in rows]}


@router.post("/api/v1/expert/clients/{client_id}/reply", status_code=201)
def reply_to_client(client_id: str, body: ExpertReply, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户不存在")
    message = ExpertMessage(client_id=client_id, expert_id=expert.id, sender_id=expert.id, content=body.content)
    db.add(message)
    db.commit()
    return {"id": message.id}


@router.post("/api/v1/expert/clients/{client_id}/close")
def close_expert_consultation(client_id: str, expert: User = Depends(expert_user), db: Session = Depends(get_db)):
    assignment = db.scalar(select(ExpertAssignment).where(
        ExpertAssignment.user_id == client_id, ExpertAssignment.expert_id == expert.id,
        ExpertAssignment.status == "active",
    ))
    if not assignment:
        raise HTTPException(404, "客户咨询不存在")
    assignment.status = "ended"
    assignment.ended_at = datetime.now(timezone.utc)
    db.add(AuditLog(
        user_id=expert.id, action="expert.consultation_closed", resource_type="expert_assignment",
        resource_id=client_id, details={},
    ))
    db.commit()
    return {"closed": True}
