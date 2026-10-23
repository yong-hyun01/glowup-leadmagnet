# ADR 0002. 등록한 HTML 의 격리

- 상태: 채택
- 날짜: 2026-10-22

## 맥락
운영자가 AI 로 만든 임의의 HTML(스크립트 포함)을 등록하고, 그 HTML 이 공개 페이지로 서빙된다. 비기능 요구사항: *등록한 HTML 이 관리자 인증 정보나 관리자 API 에 접근하지 못해야 한다.* 운영자 본인이 로그인한 브라우저로 공개 폼을 열어보는 경우까지 포함해야 한다.

## 고려한 대안
1. **HTML 새니타이징(스크립트 제거).** AI 가 만든 폼은 인라인 스크립트·CSS 에 의존하는 경우가 많아 기능이 깨지고, 새니타이저 우회 사례가 끊임없이 나온다.
2. **별도 도메인에서 서빙.** 가장 강력하지만 과제 환경(단일 localhost)에서 재현이 어렵고 인프라 의존이 생긴다.
3. **sandbox iframe + 쿠키 경로 한정 + CSP (채택).**

## 결정
세 겹으로 방어한다.

1. **sandbox iframe (origin 격리).** 공개 페이지 `/f/{slug}` 는 운영자 HTML 을 inline 으로 넣지 않고 `<iframe sandbox="allow-scripts allow-forms">` 로 `/f/{slug}/frame` 을 로드한다. `allow-same-origin` 을 주지 않으므로 프레임은 **opaque origin** 이 된다. 프레임 안의 스크립트는 부모 문서·쿠키·localStorage 에 접근할 수 없고, `fetch('/admin/api/...')` 를 해도 cross-site 요청이라 `SameSite=Strict` 쿠키가 붙지 않는다.
2. **관리자 세션 쿠키 스코프.** `Path=/admin`, `HttpOnly`, `SameSite=Strict`. 관리자 API 는 모두 `/admin/api/*` 아래에 두어 쿠키가 `/f`, `/l`, `/public` 로는 아예 전송되지 않는다. 운영자가 로그인한 채 공개 폼을 열어도 프레임 요청에 세션 쿠키가 포함되지 않는다 (`tests/test_isolation.py`).
3. **CSP.** 프레임 응답: `connect-src 'self' {PUBLIC_BASE_URL}` 로 외부 전송을 막고, `form-action 'none'` 으로 폼의 네이티브 제출을 차단하며, `frame-ancestors 'self'` 로 타 사이트 임베드를 막는다. 셸 응답: `frame-src 'self'`, `default-src 'self'`. 관리자 미리보기도 `Content-Security-Policy: sandbox` 로 프레임 밖에서 열리면 스크립트가 실행되지 않게 했다.

그 외 업로드 단계에서 확장자·크기·UTF-8·`<form>` 존재를 검증하되 내용은 수정하지 않는다.

## 결과
- 운영자 HTML 은 자유롭게 스크립트·외부 CSS·폰트(https)를 쓸 수 있다.
- 프레임이 opaque origin 이므로 제출 API 는 `Access-Control-Allow-Origin: *`(자격증명 없음)로 열어야 한다. 이 API 는 원래 공개 API 이므로 노출 범위가 늘지 않는다.
- 방문자 식별 쿠키는 프레임에서 읽을 수 없어, 셸이 프레임 URL 의 쿼리로 `visitor_id` 를 넘긴다 (ADR 0003).
- 운영 환경에서 공개 폼을 `forms.example.com` 같은 별도 도메인으로 분리하면 한 겹이 더 생긴다. `PUBLIC_BASE_URL` 설정만으로 전환 가능하다.
