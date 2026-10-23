"""캠페인별 방문·방문자·신청·전환율과 채널별 성과 집계."""
from app.security import VISITOR_COOKIE


def _visit(anon, token, fresh=False):
    if fresh:
        anon.cookies.clear()
    anon.get(f"/l/{token}", follow_redirects=True)
    return anon.cookies.get(VISITOR_COOKIE)


def _submit(anon, slug, token, vid, **fields):
    r = anon.post(f"/public/api/forms/{slug}/submissions",
                  json={"link_token": token, "visitor_id": vid, "fields": fields or {"name": "x"}})
    assert r.status_code == 201


def test_campaign_and_channel_stats(setup_form, anon, admin):
    slug = setup_form["form"]["slug"]
    links = setup_form["links"]
    cid = setup_form["campaign"]["id"]

    # instagram: 방문자 A 가 2번 방문, 1번 신청
    vid_a = _visit(anon, links["instagram"]["token"], fresh=True)
    _visit(anon, links["instagram"]["token"])
    _submit(anon, slug, links["instagram"]["token"], vid_a)
    # youtube: 방문자 B, C 방문, B 만 신청
    vid_b = _visit(anon, links["youtube"]["token"], fresh=True)
    _submit(anon, slug, links["youtube"]["token"], vid_b)
    _visit(anon, links["youtube"]["token"], fresh=True)
    # x: 방문자 D 방문만
    _visit(anon, links["x"]["token"], fresh=True)

    s = admin.get(f"/admin/api/campaigns/{cid}/stats").json()
    assert s["visits"] == 5
    assert s["visitors"] == 4
    assert s["submissions"] == 2
    assert s["conversion_rate"] == 0.5

    by = {c["channel"]: c for c in s["channels"]}
    assert set(by) == {"instagram", "youtube", "x"}
    assert by["instagram"] == {"channel": "instagram", "visits": 2, "visitors": 1, "submissions": 1, "conversion_rate": 1.0}
    assert by["youtube"] == {"channel": "youtube", "visits": 2, "visitors": 2, "submissions": 1, "conversion_rate": 0.5}
    assert by["x"] == {"channel": "x", "visits": 1, "visitors": 1, "submissions": 0, "conversion_rate": 0.0}

    overall = admin.get("/admin/api/stats/channels").json()
    assert {c["channel"]: c["submissions"] for c in overall} == {"instagram": 1, "youtube": 1, "x": 0}


def test_empty_campaign_stats(admin):
    camp = admin.post("/admin/api/campaigns", json={"name": "빈 캠페인"}).json()
    s = admin.get(f"/admin/api/campaigns/{camp['id']}/stats").json()
    assert s == {"campaign_id": camp["id"], "campaign_name": "빈 캠페인", "visits": 0, "visitors": 0,
                 "submissions": 0, "conversion_rate": 0.0, "channels": []}


def test_stats_require_auth(setup_form, anon):
    cid = setup_form["campaign"]["id"]
    assert anon.get(f"/admin/api/campaigns/{cid}/stats").status_code == 401
    assert anon.get("/admin/api/stats/channels").status_code == 401
    assert anon.get(f"/admin/api/campaigns/{cid}/leads").status_code == 401


def test_dashboard_page_shows_stats(setup_form, anon, admin):
    slug = setup_form["form"]["slug"]
    token = setup_form["links"]["threads"]["token"]
    vid = _visit(anon, token, fresh=True)
    _submit(anon, slug, token, vid, email="lead@example.com")
    r = admin.get(f"/admin/campaigns/{setup_form['campaign']['id']}")
    assert r.status_code == 200
    assert "lead@example.com" in r.text
    assert "threads" in r.text
    assert "100.0%" in r.text
