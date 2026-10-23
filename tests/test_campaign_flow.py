"""운영자 핵심 흐름: 템플릿 → 캠페인 → 폼 → 배포 링크."""


def test_create_campaign_and_form(setup_form, admin):
    form = setup_form["form"]
    assert form["slug"]
    assert form["public_url"] == f"http://testserver/f/{form['slug']}"
    assert form["is_active"] is True
    assert admin.get(f"/admin/api/forms?campaign_id={setup_form['campaign']['id']}").json()[0]["id"] == form["id"]


def test_create_form_with_unknown_template_fails(admin):
    camp = admin.post("/admin/api/campaigns", json={"name": "c"}).json()
    r = admin.post("/admin/api/forms", json={"campaign_id": camp["id"], "template_id": 999, "name": "x"})
    assert r.status_code == 404


def test_create_campaign_requires_name(admin):
    assert admin.post("/admin/api/campaigns", json={"name": ""}).status_code == 422


def test_distribution_links_per_channel(setup_form, admin):
    links = setup_form["links"]
    assert set(links) == {"instagram", "x", "youtube", "threads"}
    assert len({l["token"] for l in links.values()}) == 4
    for ch, l in links.items():
        assert l["url"] == f"http://testserver/l/{l['token']}"
        assert l["channel"] == ch


def test_same_channel_link_is_reused(setup_form, admin):
    fid = setup_form["form"]["id"]
    again = admin.post(f"/admin/api/forms/{fid}/links", json={"channel": "instagram"}).json()
    assert again["token"] == setup_form["links"]["instagram"]["token"]
    assert len(admin.get(f"/admin/api/forms/{fid}/links").json()) == 4


def test_invalid_channel_rejected(setup_form, admin):
    fid = setup_form["form"]["id"]
    assert admin.post(f"/admin/api/forms/{fid}/links", json={"channel": "tiktok"}).status_code == 422


def test_link_redirects_to_public_form(setup_form, anon):
    link = setup_form["links"]["x"]
    r = anon.get(f"/l/{link['token']}", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == f"/f/{setup_form['form']['slug']}?l={link['token']}"


def test_unknown_link_404(anon):
    assert anon.get("/l/doesnotexist", follow_redirects=False).status_code == 404


def test_deactivated_form_is_not_public(setup_form, admin, anon):
    form = setup_form["form"]
    admin.patch(f"/admin/api/forms/{form['id']}", json={"is_active": False})
    assert anon.get(f"/f/{form['slug']}").status_code == 404
    assert anon.get(f"/l/{setup_form['links']['x']['token']}", follow_redirects=False).status_code == 404
    assert anon.post(f"/public/api/forms/{form['slug']}/submissions", json={"fields": {"name": "a"}}).status_code == 404
