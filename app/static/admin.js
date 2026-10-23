async function api(method, url, body) {
  const opts = { method, credentials: 'same-origin', headers: {} };
  if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const r = await fetch(url, opts);
  let data = null;
  try { data = r.status === 204 ? null : await r.json(); } catch (e) { data = null; }
  if (r.status === 401 && !location.pathname.endsWith('/login')) location.href = '/admin/login';
  return { ok: r.ok, status: r.status, body: data || {} };
}
async function del(url) {
  if (!confirm('정말 삭제할까요?')) return;
  const r = await api('DELETE', url);
  if (r.ok) location.reload(); else flash(r.body.detail || '삭제 실패', true);
}
function flash(msg, isError) {
  const el = document.getElementById('flash');
  el.textContent = msg; el.className = 'flash' + (isError ? ' error' : ''); el.hidden = false;
  clearTimeout(el._t); el._t = setTimeout(() => { el.hidden = true; }, 3500);
}
