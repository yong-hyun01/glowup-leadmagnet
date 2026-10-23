from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import admin_ui, auth, campaigns, forms, public, templates

DESCRIPTION = """
리드마그넷 CRM 운영 시스템 API.

- **auth**: 운영자 로그인/로그아웃 (세션 쿠키, `/admin` 경로 한정)
- **templates**: AI 로 만든 단일 `.html` 파일 등록
- **campaigns / forms / links**: 캠페인, 커스텀 신청 폼, 채널별 배포 링크
- **stats**: 캠페인별 방문·방문자·신청·전환율, 채널별 성과
- **public**: 배포 링크 리다이렉트, 공개 폼 페이지, 제출 API (인증 불필요)

`/admin/api/*` 는 모두 운영자 인증이 필요합니다.
"""

app = FastAPI(title="리드마그넷 CRM 운영 시스템", version="0.1.0", description=DESCRIPTION,
              docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(campaigns.router)
app.include_router(campaigns.stats_router)
app.include_router(forms.router)
app.include_router(public.router)
app.include_router(admin_ui.router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}
