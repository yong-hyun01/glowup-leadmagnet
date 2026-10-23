from tests.conftest import SAMPLE_HTML, upload_template


def test_upload_html_success(admin):
    r = upload_template(admin)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "샘플"
    assert body["size_bytes"] == len(SAMPLE_HTML.encode())
    assert admin.get("/admin/api/templates").json()[0]["id"] == body["id"]


def test_upload_rejects_non_html_extension(admin):
    r = upload_template(admin, filename="form.txt")
    assert r.status_code == 422
    assert ".html" in r.json()["detail"]


def test_upload_rejects_html_without_form(admin):
    r = upload_template(admin, html="<html><body><h1>폼 없음</h1></body></html>")
    assert r.status_code == 422
    assert "<form>" in r.json()["detail"]


def test_upload_rejects_empty_file(admin):
    assert upload_template(admin, html="").status_code == 422


def test_upload_rejects_oversized_file(admin, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "max_html_bytes", 100)
    r = upload_template(admin, html="<form></form>" + "x" * 200)
    assert r.status_code == 422


def test_upload_requires_auth(client, operator):
    assert upload_template(client).status_code == 401


def test_delete_template_in_use_conflicts(setup_form, admin):
    tid = setup_form["template"]["id"]
    assert admin.delete(f"/admin/api/templates/{tid}").status_code == 409


def test_preview_is_forced_into_sandbox(setup_form, admin):
    tid = setup_form["template"]["id"]
    r = admin.get(f"/admin/api/templates/{tid}/preview")
    assert r.status_code == 200
    assert "sandbox" in r.headers["content-security-policy"]
