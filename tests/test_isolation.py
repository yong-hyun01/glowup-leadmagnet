"""등록한 HTML 이 관리자 인증 정보나 관리자 API 에 접근하지 못하는지 검증."""
from app.security import SESSION_COOKIE, VISITOR_COOKIE

MALICIOUS_HTML = """<!doctype html><html><body>
<form><input name="e"><button>go</button></form>
<script>
fetch('/admin/api/campaigns', {credentials:'include'});
document.cookie;
</script>
</body></html>"""


def test_frame_and_shell_never_carry_admin_cookie(setup_form, admin):
    """운영자 브라우저로 공개 폼을 열어도 관리자 쿠키는 /admin 경로 밖으로 전송되지 않는다(Path 스코프)."""
    slug = setup_form["form"]["slug"]
    login_cookie = admin.cookies.get(SESSION_COOKIE)
    assert login_cookie
    # httpx 는 Path 속성을 따르므로 /f 요청에는 쿠키가 붙지 않는다.
    r = admin.get(f"/f/{slug}/frame?v=x")
    assert SESSION_COOKIE not in r.request.headers.get("cookie", "")


def test_visitor_cookie_cannot_access_admin(setup_form, anon):
    slug = setup_form["form"]["slug"]
    anon.get(f"/f/{slug}")
    assert anon.cookies.get(VISITOR_COOKIE)
    assert anon.get("/admin/api/campaigns").status_code == 401
    assert anon.get("/admin/api/auth/me").status_code == 401
    assert anon.get("/admin", follow_redirects=False).status_code == 302


def test_malicious_template_is_served_only_inside_sandbox(admin, anon):
    from tests.conftest import upload_template

    tpl = upload_template(admin, html=MALICIOUS_HTML).json()
    camp = admin.post("/admin/api/campaigns", json={"name": "c"}).json()
    form = admin.post("/admin/api/forms", json={"campaign_id": camp["id"], "template_id": tpl["id"], "name": "f"}).json()

    shell = anon.get(f"/f/{form['slug']}")
    # 셸: 운영자 HTML 은 inline 으로 들어가지 않고 sandbox iframe 으로만 로드된다.
    assert "fetch('/admin/api" not in shell.text
    assert 'sandbox="allow-scripts allow-forms"' in shell.text
    assert "frame-src 'self'" in shell.headers["content-security-policy"]

    frame = anon.get(f"/f/{form['slug']}/frame?v=x")
    # 프레임: 운영자 스크립트는 실행되지만 CSP 가 connect-src 를 공개 API 호스트로 제한하고
    # 폼 자체 전송(form-action) 은 금지되며, 다른 페이지에 임베드될 수 없다.
    csp = frame.headers["content-security-policy"]
    assert "connect-src 'self' http://testserver" in csp
    assert "form-action 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    assert frame.headers["referrer-policy"] == "no-referrer"


def test_admin_api_rejects_cross_site_style_request_without_cookie(setup_form, anon):
    """sandbox iframe(opaque origin) 에서 오는 요청은 쿠키가 없으므로 401."""
    r = anon.post("/admin/api/campaigns", json={"name": "hacked"}, headers={"Origin": "null"})
    assert r.status_code == 401
