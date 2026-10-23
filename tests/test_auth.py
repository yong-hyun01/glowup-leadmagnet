from app.security import SESSION_COOKIE


def test_login_success_sets_admin_scoped_cookie(client, operator):
    r = client.post("/admin/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@example.com"
    cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in cookie
    assert "Path=/admin" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=strict" in cookie.lower()


def test_login_wrong_password(client, operator):
    r = client.post("/admin/api/auth/login", json={"email": "admin@example.com", "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_email(client, operator):
    r = client.post("/admin/api/auth/login", json={"email": "ghost@example.com", "password": "secret123"})
    assert r.status_code == 401


def test_admin_api_requires_auth(client, operator):
    for path in ["/admin/api/auth/me", "/admin/api/templates", "/admin/api/campaigns", "/admin/api/forms",
                 "/admin/api/stats/channels"]:
        assert client.get(path).status_code == 401, path


def test_admin_ui_redirects_to_login(client, operator):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/admin/login"


def test_tampered_session_rejected(client, operator):
    client.cookies.set(SESSION_COOKIE, "forged.token.value", path="/admin")
    assert client.get("/admin/api/auth/me").status_code == 401


def test_logout_clears_session(admin):
    assert admin.get("/admin/api/auth/me").status_code == 200
    assert admin.post("/admin/api/auth/logout").status_code == 204
    assert admin.get("/admin/api/auth/me").status_code == 401
