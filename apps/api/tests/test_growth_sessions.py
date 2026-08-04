def test_growth_sessions_are_scoped_and_persisted(client, auth):
    empty = client.get("/api/v1/coach/growth-sessions", headers=auth)
    assert empty.status_code == 200
    assert empty.json()["sessions"] == []

    session = {
        "id": "act-1",
        "problem": "明天的事情让我紧张",
        "mode": "quick",
        "steps": {},
        "resolution": {"solved": None, "note": "", "updatedAt": None},
        "actionPlan": {
            "value": "稳定",
            "action": "先写下一句话",
            "fallback": "只打开笔记",
            "when": "今晚",
            "status": "planned",
            "obstacle": "",
            "updatedAt": "2026-07-26T00:00:00Z",
        },
        "status": "in_progress",
        "createdAt": "2026-07-26T00:00:00Z",
        "updatedAt": "2026-07-26T00:00:00Z",
    }
    saved = client.put("/api/v1/coach/growth-sessions", headers=auth, json={"sessions": [session]})
    assert saved.status_code == 200
    assert saved.json()["sessions"][0]["actionPlan"]["status"] == "planned"

    reloaded = client.get("/api/v1/coach/growth-sessions", headers=auth)
    assert reloaded.status_code == 200
    assert reloaded.json()["sessions"][0]["problem"] == session["problem"]

    other = client.post("/api/v1/auth/register", json={"username": "other-family", "password": "strongpass"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/api/v1/coach/growth-sessions", headers=other_headers).json()["sessions"] == []


def test_growth_sessions_limit(client, auth):
    response = client.put(
        "/api/v1/coach/growth-sessions",
        headers=auth,
        json={"sessions": [{"id": str(index)} for index in range(101)]},
    )
    assert response.status_code == 422
