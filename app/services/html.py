"""운영자 HTML 검증과 공개 서빙용 스크립트 주입."""
import re

from fastapi import HTTPException, status

FORM_TAG_RE = re.compile(r"<form\b", re.IGNORECASE)
BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)


def validate_uploaded_html(filename: str, raw: bytes, max_bytes: int) -> str:
    if not filename.lower().endswith(".html"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=".html 파일만 등록할 수 있습니다.")
    if len(raw) == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="빈 파일은 등록할 수 없습니다.")
    if len(raw) > max_bytes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"HTML 크기는 {max_bytes // 1024}KB 이하여야 합니다.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="UTF-8 로 인코딩된 HTML 만 지원합니다.")
    if not FORM_TAG_RE.search(text):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="HTML 안에 <form> 요소가 있어야 합니다.")
    return text


# iframe(sandbox, opaque origin) 안에서 동작하는 제출 스크립트.
# 운영자 HTML 의 첫 번째 <form> submit 을 가로채 공개 제출 API 로 JSON 전송한다.
# 쿠키·관리자 API 에는 접근할 수 없다 (sandbox 에 allow-same-origin 이 없음).
_BRIDGE = """
<script>
(function () {
  var CFG = __CFG__;
  function findForm() { return document.querySelector('form'); }
  function collect(form) {
    var fd = new FormData(form), out = {};
    fd.forEach(function (v, k) {
      if (typeof v !== 'string') return;
      if (k in out) { out[k] = [].concat(out[k], v); } else { out[k] = v; }
    });
    return out;
  }
  function showMessage(form, text, ok) {
    var box = document.createElement('div');
    box.setAttribute('data-glowup-result', ok ? 'ok' : 'error');
    box.style.cssText = 'margin:12px 0;padding:12px 16px;border-radius:8px;font-family:system-ui,sans-serif;' +
      (ok ? 'background:#e7f8ee;color:#136c3a;' : 'background:#fdecec;color:#a11d1d;');
    box.textContent = text;
    form.parentNode.insertBefore(box, form.nextSibling);
    if (ok) form.style.display = 'none';
  }
  function bind() {
    var form = findForm();
    if (!form) return;
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var btn = form.querySelector('[type=submit]');
      if (btn) btn.disabled = true;
      fetch(CFG.submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link_token: CFG.linkToken, visitor_id: CFG.visitorId, fields: collect(form) })
      }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (res) {
          var old = document.querySelector('[data-glowup-result]'); if (old) old.remove();
          if (res.ok) showMessage(form, res.body.message, true);
          else { showMessage(form, (res.body && res.body.detail) || '제출에 실패했습니다.', false); if (btn) btn.disabled = false; }
        })
        .catch(function () { showMessage(form, '네트워크 오류로 제출하지 못했습니다.', false); if (btn) btn.disabled = false; });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind); else bind();
})();
</script>
"""


def inject_bridge(html: str, *, submit_url: str, link_token: str | None, visitor_id: str) -> str:
    import json

    cfg = json.dumps({"submitUrl": submit_url, "linkToken": link_token, "visitorId": visitor_id})
    # </script> 등으로 컨텍스트를 깨지 못하도록 '<' 를 이스케이프
    cfg = cfg.replace("<", "\\u003c")
    bridge = _BRIDGE.replace("__CFG__", cfg)
    if BODY_CLOSE_RE.search(html):
        return BODY_CLOSE_RE.sub(lambda _: bridge + "</body>", html, count=1)
    return html + bridge
