# 리드마그넷 CRM 운영 시스템

## 실행 방법

### 1) Docker Compose (PostgreSQL 포함, 권장)

```bash
cp .env.example .env            # 필요하면 SECRET_KEY, ADMIN_* 수정
docker compose up --build
```

- 관리자 화면: http://localhost:8000/admin (초기 계정은 `.env` 의 `ADMIN_EMAIL` / `ADMIN_PASSWORD`)
- API 문서(Swagger): http://localhost:8000/docs
- 마이그레이션과 운영자 시드는 컨테이너 시작 시 자동 실행됩니다.
- 8000 번 포트가 이미 사용 중이면 `APP_PORT=8020 PUBLIC_BASE_URL=http://localhost:8020 docker compose up --build` 처럼 바꿔 실행하세요.

### 2) 로컬 직접 실행 (uv)

```bash
uv sync
cp .env.example .env
# PostgreSQL 이 없으면 .env 의 DATABASE_URL 을 sqlite:///./dev.db 로 바꿔도 됩니다.
uv run alembic upgrade head        # 스키마 생성
uv run python -m app.seed          # 운영자 계정 생성
uv run uvicorn app.main:app --reload --port 8000
```

`PUBLIC_BASE_URL` 은 배포 링크와 공개 폼에 노출되는 주소이므로 실제 접속 주소와 맞춰 주세요.

### 운영 흐름 맛보기

1. `/admin/templates` 에서 `examples/sample_form.html` 을 등록합니다.
2. 대시보드에서 캠페인을 만들고, 캠페인 화면에서 템플릿을 골라 폼을 만듭니다.
3. 채널별 **링크 생성** 을 눌러 인스타그램·X·유튜브·스레드용 링크를 발급합니다.
4. 발급된 링크(`/l/{token}`)로 접속해 폼을 제출하면 캠페인 화면에 방문·방문자·신청·전환율과 CRM 명단이 쌓입니다.

## 테스트 방법

```bash
uv sync
uv run pytest
```

테스트는 SQLite 인메모리 DB 를 사용하므로 별도 DB 설정이 필요 없습니다.
인증, HTML 등록, 캠페인·폼·배포 링크 생성, 공개 폼 제출, 성과 집계, HTML 격리에 대한 성공·실패 흐름을 검증합니다.
