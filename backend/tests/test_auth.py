"""P0验收：认证链路。"""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "sqlite"
    assert body["mcp_mode"] == "seed"      # 未配 Token 必须走种子模式


def test_register_login_me(client, auth):
    assert auth["user"]["username"] == "tester"

    r = client.get("/api/v1/auth/me", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["username"] == "tester"


def test_register_duplicate_rejected(client):
    payload = {"username": "dupe", "password": "pwd123456"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/api/v1/auth/register",
                    json={"username": "weak", "password": "abcdefgh"})
    assert r.status_code == 422


def test_login_wrong_password_401(client, auth):
    r = client.post("/api/v1/auth/login",
                    json={"username": "tester", "password": "wrongpwd123"})
    assert r.status_code == 401
    assert "用户名或密码错误" in r.json()["detail"]


def test_login_nonexistent_no_user_enum(client):
    r = client.post("/api/v1/auth/login",
                    json={"username": "ghost", "password": "whatever123"})
    assert r.status_code == 401
    assert "用户名或密码错误" in r.json()["detail"]   # 与错误密码文案一致


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/orders").status_code == 401


def test_invalid_token_401(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert r.status_code == 401


def test_refresh_token_flow(client, auth):
    r = client.post("/api/v1/auth/refresh",
                    json={"refresh_token": auth["tokens"]["refresh_token"]})
    assert r.status_code == 200
    new_access = r.json()["access_token"]
    assert client.get("/api/v1/auth/me",
                      headers={"Authorization": f"Bearer {new_access}"}).status_code == 200


def test_access_token_cannot_be_used_as_refresh(client, auth):
    r = client.post("/api/v1/auth/refresh",
                    json={"refresh_token": auth["tokens"]["access_token"]})
    assert r.status_code == 401


def test_change_password(client, auth):
    h = auth["headers"]
    bad = client.post("/api/v1/auth/change-password",
                      json={"old_password": "nope12345", "new_password": "newpwd1234"},
                      headers=h)
    assert bad.status_code == 400

    ok = client.post("/api/v1/auth/change-password",
                     json={"old_password": "test123456", "new_password": "newpwd1234"},
                     headers=h)
    assert ok.status_code == 200

    assert client.post("/api/v1/auth/login",
                       json={"username": "tester", "password": "newpwd1234"}).status_code == 200


def test_oauth_providers_endpoint(client):
    r = client.get("/api/v1/auth/oauth-providers")
    assert r.status_code == 200
    assert r.json()["providers"] == []       # 接口位预留，未启用

# ---------------- 回归：未填邮箱的用户不得互相冲突 ----------------
# 背景：旧实现用 or_(username==X, email==Y) 单条查重，当 Y 为 None 时
# SQLAlchemy 生成 `email IS NULL`，会匹配到任意存量「无邮箱」用户，
# 导致后续所有不填邮箱的注册被误判「邮箱已注册」（HTTP 409）。
def test_multiple_users_can_register_without_email(client):
    for name in ("noemail1", "noemail2", "noemail3"):
        r = client.post("/api/v1/auth/register",
                        json={"username": name, "password": "pwd123456"})
        assert r.status_code == 201, f"{name} 注册失败：{r.json()}"
        assert r.json()["user"]["email"] is None


def test_register_with_email_then_without_email(client):
    # 先注册一个带邮箱的，再注册不填邮箱的，两者都应成功
    assert client.post("/api/v1/auth/register",
                       json={"username": "withmail", "password": "pwd123456",
                             "email": "a@b.com"}).status_code == 201
    r = client.post("/api/v1/auth/register",
                    json={"username": "nomail", "password": "pwd123456"})
    assert r.status_code == 201
    assert r.json()["user"]["username"] == "nomail"


def test_duplicate_email_still_rejected(client):
    # 用户名须≥3 位（UserRegisterIn 的 pattern 约束），否则会先被422 拦掉
    body = {"username": "emailuser1", "password": "pwd123456", "email": "dup@x.com"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    body2 = {"username": "emailuser2", "password": "pwd123456", "email": "dup@x.com"}
    r = client.post("/api/v1/auth/register", json=body2)
    assert r.status_code == 409
    assert "邮箱" in r.json()["detail"]


def test_duplicate_username_error_message(client):
    client.post("/api/v1/auth/register",
                json={"username": "dupname", "password": "pwd123456"})
    r = client.post("/api/v1/auth/register",
                    json={"username": "dupname", "password": "pwd123456"})
    assert r.status_code == 409
    assert "用户名" in r.json()["detail"]


def test_login_by_email_still_works(client):
    client.post("/api/v1/auth/register",
                json={"username": "mailer", "password": "pwd123456",
                      "email": "login@x.com"})
    r = client.post("/api/v1/auth/login",
                    json={"username": "login@x.com", "password": "pwd123456"})
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "mailer"
