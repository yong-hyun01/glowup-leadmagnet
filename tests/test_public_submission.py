"""방문자 흐름: 배포 링크 → 공개 폼 → 제출 → CRM 저장."""
import re

from app.security import VISITOR_COOKIE


def test_visit_sets_visitor_cookie_and_renders_sandboxed_iframe(setup_form, anon):
    slug = setup_form["form"]["slug"]
    r = anon.get(f"/f/{slug}")
    assert r.status_code == 200
    assert VISITOR_COOKIE in r.cookies
    assert 'sandbox="allow-scripts allow-forms"' in r.text
    assert "allow-same-origin" not in r.text
    assert f'src="/f/{slug}/frame?v=' in r.text


def test_frame_serves_operator_html_with_bridge_and_csp(setup_form, anon):
    slug = setup_form["form"]["slug"]
    r = anon.get(f"/f/{slug}/frame?v=abc123")
    assert r.status_code == 200
    assert "<h1>신청</h1>" in r.text
    assert "submitUrl" in r.text and f"/public/api/forms/{slug}/submissions" in r.text
    csp = r.headers["content-security-policy"]
    assert "form-action 'none'" in csp
    assert "frame-ancestors 'self'" in csp


def test_submit_success_creates_lead_with_channel(setup_form, anon, admin):
    slug = setup_form["form"]["slug"]
    link = setup_form["links"]["instagram"]
    anon.get(f"/l/{link['token']}", follow_redirects=True)  # 방문 기록
    vid = anon.cookies.get(VISITOR_COOKIE)

    r = anon.post(f"/public/api/forms/{slug}/submissions",
                  json={"link_token": link["token"], "visitor_id": vid, "fields": {"name": "홍길동", "email": "a@b.c"}})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ok"] is True and body["message"]

    leads = admin.get(f"/admin/api/forms/{setup_form['form']['id']}/leads").json()
    assert len(leads) == 1
    assert leads[0]["channel"] == "instagram"
    assert leads[0]["data"] == {"name": "홍길동", "email": "a@b.c"}
    assert leads[0]["visitor_id"] == vid


def test_submit_without_link_is_direct(setup_form, anon, admin):
    slug = setup_form["form"]["slug"]
    r = anon.post(f"/public/api/forms/{slug}/submissions", json={"fields": {"name": "x"}})
    assert r.status_code == 201
    leads = admin.get(f"/admin/api/campaigns/{setup_form['campaign']['id']}/leads").json()
    assert leads[0]["channel"] == "direct"


def test_submit_with_foreign_link_token_falls_back_to_direct(setup_form, anon, admin):
    """다른 폼의 토큰을 넣어도 이 폼의 채널로 둔갑하지 못한다."""
    tpl = setup_form["template"]
    camp2 = admin.post("/admin/api/campaigns", json={"name": "other"}).json()
    form2 = admin.post("/admin/api/forms", json={"campaign_id": camp2["id"], "template_id": tpl["id"], "name": "f2"}).json()
    other_link = admin.post(f"/admin/api/forms/{form2['id']}/links", json={"channel": "youtube"}).json()

    slug = setup_form["form"]["slug"]
    r = anon.post(f"/public/api/forms/{slug}/submissions", json={"link_token": other_link["token"], "fields": {"a": "1"}})
    assert r.status_code == 201
    lead = admin.get(f"/admin/api/forms/{setup_form['form']['id']}/leads").json()[0]
    assert lead["channel"] == "direct"


def test_submit_empty_fields_rejected(setup_form, anon):
    slug = setup_form["form"]["slug"]
    assert anon.post(f"/public/api/forms/{slug}/submissions", json={"fields": {}}).status_code == 422
    assert anon.post(f"/public/api/forms/{slug}/submissions", json={"fields": {"name": "   "}}).status_code == 422
    assert anon.post(f"/public/api/forms/{slug}/submissions", json={}).status_code == 422


def test_submit_unknown_slug_404(anon):
    assert anon.post("/public/api/forms/nope/submissions", json={"fields": {"a": "b"}}).status_code == 404


def test_submit_truncates_long_values(setup_form, anon, admin):
    slug = setup_form["form"]["slug"]
    r = anon.post(f"/public/api/forms/{slug}/submissions", json={"fields": {"memo": "x" * 5000}})
    assert r.status_code == 201
    lead = admin.get(f"/admin/api/forms/{setup_form['form']['id']}/leads").json()[0]
    assert len(lead["data"]["memo"]) == 2000


def test_submit_allows_null_origin_cors(setup_form, anon):
    slug = setup_form["form"]["slug"]
    r = anon.options(f"/public/api/forms/{slug}/submissions")
    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == "*"


def test_bridge_config_escapes_script_breakout(setup_form, admin, anon):
    """success_message 등에 </script> 가 들어가도 브리지 스크립트 컨텍스트가 깨지지 않는다."""
    slug = setup_form["form"]["slug"]
    r = anon.get(f"/f/{slug}/frame?v=</script><script>alert(1)</script>")
    assert "</script><script>alert(1)" not in r.text.split("var CFG = ")[1].split(";")[0]
    assert re.search(r"\\u003c/script", r.text)
