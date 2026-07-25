"""孩子头像测试：卡通生成确定性 + 上传/删除/生成路径。"""
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image


def test_cartoon_svg_is_deterministic():
    from app.services.avatar import generate_avatar_svg
    a = generate_avatar_svg("小星")
    b = generate_avatar_svg("小星")
    assert a == b
    assert a.startswith("<svg") and a.endswith("</svg>")


def test_cartoon_svg_differs_per_seed():
    from app.services.avatar import generate_avatar_svg
    a = generate_avatar_svg("小星")
    b = generate_avatar_svg("小明")
    assert a != b


def test_cartoon_svg_handles_empty_seed():
    from app.services.avatar import generate_avatar_svg
    s = generate_avatar_svg("")
    assert "<svg" in s and "viewBox" in s


def test_avatar_url_format():
    from app.services.avatar import avatar_url_for
    url = avatar_url_for("abc-123", "小星")
    assert url == "/api/v1/child-avatars/abc-123"
    # 移除后路径仍可识别（不依赖 seed）
    url2 = avatar_url_for("abc-123", None)
    assert url2 == "/api/v1/child-avatars/abc-123"


def test_avatar_static_route_returns_svg_when_no_file(client):
    """未上传时静态路由应返回卡通 SVG（兜底）。"""
    response = client.get("/api/v1/child-avatars/non-existent-id")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "<svg" in response.text


def test_upload_remove_regenerate_flow(client, auth):
    """完整流程：创建孩子 → 上传 → 移除 → 重新生成。"""
    cid = client.post("/api/v1/children", headers=auth, json={"name": "小测"}).json()["id"]

    # 1. 生成 PNG 临时图片
    img = Image.new("RGB", (50, 50), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # 2. 上传
    upload = client.post(f"/api/v1/children/{cid}/avatar", headers=auth, files={"avatar": ("a.png", buf, "image/png")})
    assert upload.status_code == 200
    body = upload.json()
    assert body["avatar_url"] == f"/api/v1/child-avatars/{cid}"
    assert body["avatar_seed"] == "小测"

    # 3. 静态 GET 返回 webp
    static = client.get(f"/api/v1/child-avatars/{cid}")
    assert static.status_code == 200
    assert static.headers["content-type"] == "image/webp"

    # 4. 移除
    rm = client.delete(f"/api/v1/children/{cid}/avatar", headers=auth)
    assert rm.status_code == 200
    assert rm.json()["avatar_url"] is None

    # 5. 重新生成（清空 webp，回到 SVG）
    regen = client.post(f"/api/v1/children/{cid}/avatar/regenerate", headers=auth)
    assert regen.status_code == 200
    assert regen.json()["avatar_url"] == f"/api/v1/child-avatars/{cid}"

    static2 = client.get(f"/api/v1/child-avatars/{cid}")
    assert "image/svg+xml" in static2.headers["content-type"]


def test_upload_rejects_oversize(client, auth):
    cid = client.post("/api/v1/children", headers=auth, json={"name": "小测"}).json()["id"]
    big = b"x" * (5 * 1024 * 1024 + 1)
    bad = client.post(
        f"/api/v1/children/{cid}/avatar",
        headers=auth,
        files={"avatar": ("big.png", BytesIO(big), "image/png")},
    )
    assert bad.status_code in (400, 413, 422)


def test_upload_rejects_wrong_type(client, auth):
    cid = client.post("/api/v1/children", headers=auth, json={"name": "小测"}).json()["id"]
    bad = client.post(
        f"/api/v1/children/{cid}/avatar",
        headers=auth,
        files={"avatar": ("a.gif", BytesIO(b"x"), "image/gif")},
    )
    assert bad.status_code in (400, 415)


def test_isolation_across_users(client, auth):
    """用户 A 不能改用户 B 的孩子头像。"""
    import os
    os.environ.setdefault("JWT_SECRET", "x" * 32)
    a_token = client.post("/api/v1/auth/register", json={"username": f"a_{uuid4().hex[:6]}", "password": "abcdefgh"}).json()["access_token"]
    b_token = client.post("/api/v1/auth/register", json={"username": f"b_{uuid4().hex[:6]}", "password": "abcdefgh"}).json()["access_token"]
    cid_a = client.post("/api/v1/children", headers={"Authorization": f"Bearer {a_token}"}, json={"name": "A娃"}).json()["id"]
    forbidden = client.delete(f"/api/v1/children/{cid_a}/avatar", headers={"Authorization": f"Bearer {b_token}"})
    assert forbidden.status_code == 404
