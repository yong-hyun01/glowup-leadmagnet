# ADR 0001. 기술 스택 선택

- 상태: 채택
- 날짜: 2026-10-22

## 맥락
제출 기한이 3일이고, 과제는 "기능 수보다 운영자가 폼을 만들고 배포한 뒤 전환 데이터를 확인하는 흐름"의 완성을 요구한다. 관계형 DB, API 문서화, 자동화 테스트, 마이그레이션 제출이 필수다.

## 결정
- **백엔드: FastAPI + SQLAlchemy 2 + Alembic.** FastAPI 는 OpenAPI 문서를 자동 생성하므로 "API 문서화" 요구를 코드와 동기화된 상태로 충족한다. Pydantic 으로 입력 검증을 일관되게 처리한다.
- **DB: PostgreSQL 16 (docker compose).** 테스트와 빠른 로컬 실행은 SQLite 로도 가능하도록 DB 종속 기능(JSONB, 배열 등)은 쓰지 않고 SQLAlchemy 의 범용 타입(`JSON`, `Enum`)만 사용한다.
- **관리자 UI: Jinja2 서버 렌더링 + 소량의 fetch 스크립트.** 별도 프론트엔드 빌드 체인(React 등)을 두면 CORS·빌드·배포가 두 배가 된다. 관리자 화면은 JSON API 를 호출하는 얇은 껍데기로 만들어 API 가 단일 진실 공급원이 되게 했다.
- **테스트: pytest + FastAPI TestClient, SQLite 인메모리.**

## 결과
- 단일 프로세스(uvicorn)로 관리자 화면·API·공개 폼을 모두 서빙한다.
- Postgres 전용 최적화(JSONB 인덱스 등)는 포기했다. 트래픽이 커지면 `visits` 집계를 일별 롤업 테이블로 옮기는 것이 다음 단계다.
