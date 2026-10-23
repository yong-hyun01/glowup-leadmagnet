import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Operator
from app.security import hash_password

SAMPLE_HTML = (
    "<!doctype html><html><head><meta charset='utf-8'><title>t</title></head>"
    "<body><h1>신청</h1><form><input name='name'><input name='email'><button type='submit'>보내기</button></form></body></html>"
)


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def operator(db):
    op = Operator(email="admin@example.com", password_hash=hash_password("secret123"))
    db.add(op)
    db.commit()
    return op


@pytest.fixture
def admin(client, operator):
    """로그인된 운영자 클라이언트."""
    r = client.post("/admin/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def anon(engine):
    """쿠키가 전혀 없는 별도 클라이언트 (방문자/공격자 역할)."""
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def upload_template(client, html=SAMPLE_HTML, filename="form.html", name="샘플"):
    return client.post("/admin/api/templates", files={"file": (filename, html.encode(), "text/html")}, data={"name": name})


@pytest.fixture
def setup_form(admin):
    """템플릿 + 캠페인 + 폼 + 4개 채널 링크까지 만든 상태를 돌려준다."""
    tpl = upload_template(admin).json()
    camp = admin.post("/admin/api/campaigns", json={"name": "10월 전자책"}).json()
    form = admin.post("/admin/api/forms", json={"campaign_id": camp["id"], "template_id": tpl["id"], "name": "메인 폼"}).json()
    links = {}
    for ch in ["instagram", "x", "youtube", "threads"]:
        links[ch] = admin.post(f"/admin/api/forms/{form['id']}/links", json={"channel": ch}).json()
    return {"template": tpl, "campaign": camp, "form": form, "links": links}
