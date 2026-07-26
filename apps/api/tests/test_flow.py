from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor


def test_complete_core_flow(client, auth):
    child_response = client.post(
        "/api/v1/children",
        headers=auth,
        json={"name": "小星", "diagnosis": "ASD", "goals": "主动沟通"},
    )
    assert child_response.status_code == 201
    child_id = child_response.json()["id"]

    key = str(uuid4())
    assessment = client.post(
        "/api/v1/assessments",
        headers={**auth, "Idempotency-Key": key},
        json={"child_id": child_id, "answers": {
            "par_1": 0, "imi_1": 0, "vis_1": 0, "lan_1": 0,
            "pla_1": 0, "soc_1": 0, "emo_1": 0, "pre_1": 0, "slf_1": 0,
        }},
    )
    assert assessment.status_code == 200
    assert len(assessment.json()["generated_task_ids"]) > 0
    duplicate = client.post(
        "/api/v1/assessments",
        headers={**auth, "Idempotency-Key": key},
        json={"child_id": child_id, "answers": {"request": 2}},
    )
    assert duplicate.json()["id"] == assessment.json()["id"]

    tasks = client.get(f"/api/v1/tasks?child_id={child_id}", headers=auth).json()
    session = client.post(
        "/api/v1/training-sessions",
        headers={**auth, "Idempotency-Key": str(uuid4())},
        json={"child_id": child_id, "task_id": tasks[0]["id"], "skill_name": tasks[0]["name"]},
    ).json()
    first_trial = client.post(
        f"/api/v1/training-sessions/{session['id']}/trials",
        headers=auth,
        json={"result": "I"},
    )
    assert first_trial.status_code == 200
    too_short = client.post(f"/api/v1/training-sessions/{session['id']}/finish", headers=auth)
    assert too_short.status_code == 400
    assert "至少记录 5 个回合" in too_short.json()["detail"]
    for result in ["V", "M", "P", "E"]:
        response = client.post(
            f"/api/v1/training-sessions/{session['id']}/trials",
            headers=auth,
            json={"result": result},
        )
        assert response.status_code == 200
    invalid = client.post(
        f"/api/v1/training-sessions/{session['id']}/trials",
        headers=auth,
        json={"result": "X"},
    )
    assert invalid.status_code == 422
    active = client.get(f"/api/v1/training-sessions/active?child_id={child_id}", headers=auth).json()
    assert active["id"] == session["id"]
    client.post(f"/api/v1/training-sessions/{session['id']}/trials", headers=auth, json={"result": "E"})
    undone = client.delete(f"/api/v1/training-sessions/{session['id']}/trials/latest", headers=auth).json()
    assert undone["trials"] == ["I", "V", "M", "P", "E"]
    finished = client.post(f"/api/v1/training-sessions/{session['id']}/finish", headers=auth).json()
    assert finished["percentage"] == 20
    progress = client.get(f"/api/v1/progress?child_id={child_id}", headers=auth).json()
    assert progress["completed_sessions"] == 1
    assert progress["last_training_at"]
    assert progress["trend"]["status"] == "insufficient"
    assert len(progress["weekly"]) == 4
    assert progress["weekly"][-1]["results"] == {"I": 1, "V": 1, "M": 1, "P": 1, "E": 1}
    assert progress["skills"][0]["skill_name"] == tasks[0]["name"]
    assert progress["skills"][0]["status"] == "insufficient"
    report = client.post("/api/v1/reports", headers=auth, json={"child_id": child_id})
    assert report.status_code == 202
    reports = client.get(f"/api/v1/reports?child_id={child_id}", headers=auth).json()
    assert reports[0]["status"] == "completed"
    assert reports[0]["file_url"]
    pdf = client.get(reports[0]["file_url"], headers=auth)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_cross_user_child_isolation(client, auth):
    child_id = client.post("/api/v1/children", headers=auth, json={"name": "小星"}).json()["id"]
    task = client.post(
        "/api/v1/tasks", headers=auth,
        json={"child_id": child_id, "name": "私密训练", "category": "测试"},
    ).json()
    session = client.post(
        "/api/v1/training-sessions",
        headers={**auth, "Idempotency-Key": str(uuid4())},
        json={"child_id": child_id, "task_id": task["id"], "skill_name": task["name"]},
    ).json()
    client.post("/api/v1/coach/moods", headers=auth, json={"mood": "只属于A", "intensity": 3})
    client.post("/api/v1/coach/journals", headers=auth, json={"content": "A账户的私密日记"})
    client.post("/api/v1/coach/chat", headers=auth, json={"message": "A账户的私密对话"})
    other = client.post("/api/v1/auth/register", json={"username": "other", "password": "strongpass"}).json()
    other_auth = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/v1/tasks?child_id={child_id}", headers=other_auth).status_code == 404
    assert client.get(f"/api/v1/progress?child_id={child_id}", headers=other_auth).status_code == 404
    assert client.get(f"/api/v1/child-avatars/{child_id}", headers=other_auth).status_code == 404
    assert client.post(
        f"/api/v1/training-sessions/{session['id']}/trials",
        headers=other_auth, json={"result": "I"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/training-sessions/{session['id']}/trials/latest", headers=other_auth
    ).status_code == 404
    assert client.post(
        f"/api/v1/training-sessions/{session['id']}/finish", headers=other_auth
    ).status_code == 404
    assert client.get("/api/v1/coach/moods", headers=other_auth).json() == []
    assert client.get("/api/v1/coach/journals", headers=other_auth).json() == []
    assert client.get("/api/v1/chat/messages?product=coach", headers=other_auth).json() == []


def test_login_refresh_logout_token_lifecycle(client):
    tokens = client.post(
        "/api/v1/auth/register", json={"username": "logincheck", "password": "strongpass"}
    ).json()
    assert client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/login", json={"username": "logincheck", "password": "wrongpass"}
    ).status_code == 401
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code == 401
    current_refresh = refreshed.json()["refresh_token"]
    assert client.post(
        "/api/v1/auth/logout", json={"refresh_token": current_refresh}
    ).status_code == 204
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": current_refresh}
    ).status_code == 401


def test_registration_normalizes_username_and_reports_duplicates(client):
    created = client.post(
        "/api/v1/auth/register",
        json={"username": "  newfamily  ", "password": "strongpass"},
    )
    assert created.status_code == 201
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "newfamily", "password": "strongpass"},
    ).status_code == 200
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"username": "newfamily", "password": "strongpass"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "用户名已存在"
    whitespace = client.post(
        "/api/v1/auth/register",
        json={"username": "  ", "password": "strongpass"},
    )
    assert whitespace.status_code == 422
    assert whitespace.json()["detail"] == "用户名至少需要 2 个字符"


def test_concurrent_tokens_never_cross_users(client):
    identities = []
    for index in range(12):
        username = f"loaduser{index}"
        tokens = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "strongpass"},
        ).json()
        identities.append((username, tokens["access_token"]))

    requests = identities * 10

    def read_identity(item):
        expected, token = item
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Forwarded-For": f"10.0.0.{len(expected)}"},
        )
        return expected, response.status_code, response.json().get("username")

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(read_identity, requests))

    assert len(results) == 120
    assert all(status == 200 and actual == expected for expected, status, actual in results)


def test_coach_records_are_persisted(client, auth):
    mood = client.post("/api/v1/coach/moods", headers=auth, json={"mood": "疲惫", "intensity": 4})
    assert mood.status_code == 200
    journal = client.post("/api/v1/coach/journals", headers=auth, json={"content": "今天主动请家人帮忙。"})
    assert journal.status_code == 201
    overview = client.get("/api/v1/coach/overview", headers=auth).json()
    assert overview["mood_today"] == "疲惫"
    assert overview["journal_count"] == 1
    reply = client.post("/api/v1/coach/chat", headers=auth, json={"message": "今天真的很累"}).json()
    assert reply["answer"]
    assert "ABA" not in reply["answer"]
    assert "孩子" not in reply["answer"]
    assert "我注意到" in reply["answer"]
    history = client.get("/api/v1/chat/messages?product=coach", headers=auth).json()
    assert [item["role"] for item in history] == ["user", "assistant"]
    from app.database import SessionLocal
    from app.models import AiUsage
    from sqlalchemy import select
    db = SessionLocal()
    usage = db.scalar(select(AiUsage))
    db.close()
    assert usage.product == "coach"
    assert usage.fallback is True
    weekly = client.post("/api/v1/coach/weekly-report", headers=auth).json()
    exported = client.post("/api/v1/coach/weekly-report/export", headers=auth, json=weekly)
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/pdf"
    assert exported.content.startswith(b"%PDF")


def test_parent_selects_expert_and_expert_replies(client, auth):
    from app.database import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    expert = User(username="expert", password_hash=hash_password("expertpass12"), role="expert")
    db.add(expert)
    db.commit()
    db.refresh(expert)
    expert_id = expert.id
    db.close()

    experts = client.get("/api/v1/experts", headers=auth).json()
    assert experts["items"][0]["id"] == expert_id
    assert client.put("/api/v1/experts/selection", headers=auth, json={"expert_id": expert_id}).status_code == 200
    assert client.post("/api/v1/expert/questions", headers=auth, json={"content": "孩子发脾气时怎么办？"}).status_code == 201

    tokens = client.post("/api/v1/auth/login", json={"username": "expert", "password": "expertpass12"}).json()
    expert_auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    profile = client.put("/api/v1/expert/profile", headers=expert_auth, json={
        "display_name": "林老师", "title": "家庭干预顾问",
        "specialties": ["语言发展", "情绪行为"], "bio": "专注家庭场景支持。",
        "credentials": "ABA 家长培训", "accepting_clients": True, "max_clients": 10,
    })
    assert profile.status_code == 200
    from io import BytesIO
    from PIL import Image
    image_bytes = BytesIO()
    Image.new("RGB", (900, 600), "#46756b").save(image_bytes, "PNG")
    avatar = client.post(
        "/api/v1/expert/profile/avatar", headers=expert_auth,
        files={"avatar": ("avatar.png", image_bytes.getvalue(), "image/png")},
    )
    assert avatar.status_code == 200
    assert client.get(avatar.json()["avatar_url"]).headers["content-type"] == "image/webp"
    public_profile = client.get("/api/v1/experts", headers=auth).json()["items"][0]
    assert public_profile["name"] == "林老师"
    assert public_profile["specialties"] == ["语言发展", "情绪行为"]
    assert public_profile["avatar_url"].endswith(expert_id)
    clients = client.get("/api/v1/expert/clients", headers=expert_auth).json()["items"]
    assert clients[0]["unread"] == 1
    client_id = clients[0]["id"]
    assert client.get(f"/api/v1/expert/clients/{client_id}/messages", headers=expert_auth).status_code == 200
    assert client.post(
        f"/api/v1/expert/clients/{client_id}/reply",
        headers=expert_auth,
        json={"content": "先记录触发情境，再提供可替代的表达方式。"},
    ).status_code == 201
    assert client.get("/api/v1/notifications", headers=auth).json()["expert_unread"] == 1
    conversation = client.get("/api/v1/expert/conversation", headers=auth).json()["items"]
    assert [item["sender"] for item in conversation] == ["client", "expert"]
    assert client.get("/api/v1/notifications", headers=auth).json()["expert_unread"] == 0
    assert client.post(f"/api/v1/expert/clients/{client_id}/close", headers=expert_auth).status_code == 200
    assert client.get("/api/v1/experts", headers=auth).json()["selected_expert_id"] is None
    assert client.get("/api/v1/admin/users", headers=expert_auth).status_code == 403


def test_admin_can_manage_user_status_and_role(client, auth):
    from app.database import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    admin = User(username="admin", password_hash=hash_password("adminpass123"), role="admin")
    db.add(admin)
    db.commit()
    db.close()
    admin_tokens = client.post("/api/v1/auth/login", json={"username": "admin", "password": "adminpass123"}).json()
    admin_auth = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    assert client.get("/api/v1/admin/operations", headers=auth).status_code == 403
    operations = client.get("/api/v1/admin/operations", headers=admin_auth)
    assert operations.status_code == 200
    assert operations.json()["queue"]["mode"] == "local"
    family = client.get("/api/v1/admin/users", headers=admin_auth).json()["items"]
    target = next(item for item in family if item["username"] == "family")

    detail = client.get(f"/api/v1/admin/users/{target['id']}", headers=admin_auth)
    assert detail.status_code == 200
    assert client.patch(f"/api/v1/admin/users/{target['id']}/role?role=expert", headers=admin_auth).json()["role"] == "expert"
    assert client.patch(f"/api/v1/admin/users/{target['id']}/status?active=false", headers=admin_auth).json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 403
    assert client.patch(f"/api/v1/admin/users/{target['id']}/status?active=true", headers=admin_auth).json()["is_active"] is True
    created = client.post(
        "/api/v1/admin/users", headers=admin_auth,
        json={"username": "newexpert", "password": "temporary123", "role": "expert"},
    )
    assert created.status_code == 201
    new_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/admin/users/{new_id}/password", headers=admin_auth,
        json={"password": "changedpass12"},
    ).status_code == 200
    audit = client.get("/api/v1/admin/audit-logs", headers=admin_auth).json()["items"]
    assert {"admin.user.created", "admin.user.password_reset"}.issubset({item["action"] for item in audit})


def test_public_chat_rate_limit_and_child_access_audit(client, auth):
    for index in range(20):
        assert client.post("/api/v1/chat/public", json={"message": f"问题 {index}"}).status_code == 200
    limited = client.post("/api/v1/chat/public", json={"message": "再问一次"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0

    child_id = client.post("/api/v1/children", headers=auth, json={"name": "审计测试"}).json()["id"]
    assert client.get(f"/api/v1/tasks?child_id={child_id}", headers=auth).status_code == 200
    from app.database import SessionLocal
    from app.models import AuditLog
    from sqlalchemy import select

    db = SessionLocal()
    event = db.scalar(select(AuditLog).where(
        AuditLog.action == "child.data_accessed", AuditLog.resource_id == child_id
    ))
    db.close()
    assert event is not None
