# API 문서

실행 중인 서버의 `/docs` (Swagger UI) 또는 `/redoc` 에서 모든 엔드포인트와 스키마를 인터랙티브하게 확인할 수 있습니다.
아래는 핵심 API 요약입니다.

## 공통

- Base URL: `PUBLIC_BASE_URL` (기본 `http://localhost:8000`)
- 요청·응답 본문은 JSON (`Content-Type: application/json`). HTML 등록만 `multipart/form-data`.
- 오류는 `{"detail": "메시지"}` 형식. 입력 검증 실패는 `422`, 인증 실패는 `401`, 없는 리소스는 `404`.
- `/admin/api/*` 는 **운영자 인증 필수**. 로그인 시 발급되는 세션 쿠키(`glowup_admin_session`, `Path=/admin`, `HttpOnly`, `SameSite=Strict`)로 인증합니다.
- `/l/*`, `/f/*`, `/public/api/*` 는 인증 없이 접근 가능한 공개 영역입니다.

## 1. 인증 (auth)

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/admin/api/auth/login` | 로그인. 성공 시 세션 쿠키 발급 |
| POST | `/admin/api/auth/logout` | 로그아웃 (쿠키 삭제, 204) |
| GET | `/admin/api/auth/me` | 현재 운영자 정보 |

```http
POST /admin/api/auth/login
{"email": "admin@example.com", "password": "admin1234"}

200 {"id": 1, "email": "admin@example.com"}
401 {"detail": "이메일 또는 비밀번호가 올바르지 않습니다."}
```

## 2. HTML 템플릿 (templates)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/api/templates` | 목록 |
| POST | `/admin/api/templates` | 등록 (multipart: `file`=.html, `name`=선택) |
| GET | `/admin/api/templates/{id}` | 상세 |
| GET | `/admin/api/templates/{id}/preview` | 미리보기 HTML (CSP sandbox 강제) |
| DELETE | `/admin/api/templates/{id}` | 삭제. 사용 중이면 409 |

등록 조건: 확장자 `.html`, UTF-8, `MAX_HTML_BYTES`(기본 512KB) 이하, 본문에 `<form>` 포함.

```http
POST /admin/api/templates  (multipart/form-data)
file=@sample_form.html, name=전자책 신청폼

201 {"id": 1, "name": "전자책 신청폼", "original_filename": "sample_form.html", "size_bytes": 1547, "created_at": "..."}
422 {"detail": "HTML 안에 <form> 요소가 있어야 합니다."}
```

## 3. 캠페인 (campaigns)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/api/campaigns` | 목록 |
| POST | `/admin/api/campaigns` | 생성 `{"name": "...", "description": "..."}` |
| GET | `/admin/api/campaigns/{id}` | 상세 |
| DELETE | `/admin/api/campaigns/{id}` | 삭제 (폼·링크·방문·신청 함께 삭제) |
| GET | `/admin/api/campaigns/{id}/leads` | 캠페인의 CRM 명단 |

## 4. 커스텀 신청 폼 (forms)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/api/forms?campaign_id=` | 목록 (캠페인 필터 선택) |
| POST | `/admin/api/forms` | 생성 |
| GET | `/admin/api/forms/{id}` | 상세 |
| PATCH | `/admin/api/forms/{id}` | 수정 (`name`, `success_message`, `is_active`) |
| DELETE | `/admin/api/forms/{id}` | 삭제 |
| GET | `/admin/api/forms/{id}/leads` | 폼의 CRM 명단 |

```http
POST /admin/api/forms
{"campaign_id": 1, "template_id": 1, "name": "메인 폼", "success_message": "감사합니다!"}

201 {"id": 1, "campaign_id": 1, "template_id": 1, "name": "메인 폼", "slug": "e93a32ad7799",
     "success_message": "감사합니다!", "is_active": true,
     "public_url": "http://localhost:8000/f/e93a32ad7799", "created_at": "..."}
```

## 5. 배포 링크 (links)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/api/forms/{id}/links` | 폼의 배포 링크 목록 |
| POST | `/admin/api/forms/{id}/links` | 채널별 링크 생성. `channel` ∈ `instagram`, `x`, `youtube`, `threads`. 같은 채널은 기존 링크 반환 |

```http
POST /admin/api/forms/1/links
{"channel": "instagram"}

201 {"id": 1, "form_id": 1, "channel": "instagram", "token": "e4bb2f3a4148",
     "url": "http://localhost:8000/l/e4bb2f3a4148", "created_at": "..."}
422 (지원하지 않는 채널)
```

## 6. 성과 조회 (stats)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/admin/api/campaigns/{id}/stats` | 캠페인별 방문·방문자·신청·전환율 + 채널별 성과 |
| GET | `/admin/api/stats/channels` | 전체 캠페인 합산 채널별 성과 |

```http
GET /admin/api/campaigns/1/stats

200 {"campaign_id": 1, "campaign_name": "10월 전자책 캠페인",
     "visits": 5, "visitors": 4, "submissions": 2, "conversion_rate": 0.5,
     "channels": [
       {"channel": "instagram", "visits": 2, "visitors": 1, "submissions": 1, "conversion_rate": 1.0},
       {"channel": "youtube",   "visits": 2, "visitors": 2, "submissions": 1, "conversion_rate": 0.5},
       {"channel": "x",         "visits": 1, "visitors": 1, "submissions": 0, "conversion_rate": 0.0}
     ]}
```

지표 정의: 방문 = 공개 폼 페이지 로드 수, 방문자 = 쿠키 기준 고유 방문자 수, 신청 = 저장된 CRM 명단 수, 전환율 = 신청 ÷ 방문자 (0~1).

## 7. 공개 영역 (public, 인증 불필요)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/l/{token}` | 배포 링크. `/f/{slug}?l={token}` 으로 302 |
| GET | `/f/{slug}` | 공개 폼 페이지(셸). 방문 기록 + 방문자 쿠키 발급 + sandbox iframe |
| GET | `/f/{slug}/frame?v=&l=` | 운영자 HTML + 제출 브리지 스크립트 (iframe 내부용) |
| POST | `/public/api/forms/{slug}/submissions` | 폼 제출 → CRM 명단 저장 |

```http
POST /public/api/forms/e93a32ad7799/submissions
{"link_token": "e4bb2f3a4148", "visitor_id": "6859a2a4...", "fields": {"name": "홍길동", "email": "a@b.c"}}

201 {"ok": true, "lead_id": 1, "message": "신청이 접수되었습니다. 감사합니다!"}
404 {"detail": "폼을 찾을 수 없거나 비활성화되었습니다."}
422 {"detail": "입력된 내용이 없습니다."}
```

`fields` 는 운영자 HTML 의 `<form>` 안 필드명을 그대로 키로 사용하며, 값은 2,000자·최대 50개 필드로 잘립니다.
`link_token` 이 다른 폼의 토큰이면 채널은 `direct` 로 기록됩니다. 응답에는 `Access-Control-Allow-Origin: *` 가 포함되어 sandbox iframe(opaque origin)에서 호출할 수 있습니다.
