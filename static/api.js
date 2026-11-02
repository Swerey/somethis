/* SomeWhere社区 - API 模块（批次C拆分自 common.js） */
const API = {
  get: (url) => fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } }).then(r => handle(r)),
  post: (url, body) => fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    body: JSON.stringify(body),
  }).then(r => handle(r)),
  postForm: (url, formData) => fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    body: formData,
  }).then(r => handle(r)),
  put: (url, body) => fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    body: JSON.stringify(body),
  }).then(r => handle(r)),
  del: (url) => fetch(url, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
  }).then(r => handle(r)),
};

async function handle(r) {
  let data = null;
  try { data = await r.json(); } catch (e) { data = {}; }
  if (!r.ok) {
    const msg = data && data.detail ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : ('请求失败 ' + r.status);
    if (r.status === 401) {
      localStorage.removeItem('token'); localStorage.removeItem('user');
      // 登录页自身失败不跳转，避免死循环；其余页面统一跳登录
      if (!/login\.html([?#]|$)/.test(location.href)) location.href = 'login.html';
    }
    const err = new Error(msg); err.status = r.status; err._toasted = true;
    showToast(msg, r.status === 401 ? 'warning' : 'error');
    throw err;
  }
  return data;
}

function currentUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch (e) { return null; }
}
function isLogin() { return !!currentUser(); }

/* Toast：success / error / warning / info（默认 info）*/
function showToast(msg, type = 'info') {
  const d = document.createElement('div');
  d.className = 'alert-bar ' + (type || 'info');
  d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 2600);
}
/* 兼容旧调用 toast(msg, ok) */
function toast(msg, ok = false) {
  showToast(msg, ok ? 'success' : 'error');
}

/* ===== 批次C-4：全局错误捕获 ===== */
window.addEventListener('error', function (e) {
  if (window.__somewhere_err_log) {
    try {
      window.__somewhere_err_log.push({ at: new Date().toISOString(), msg: String(e.message || ''), src: String(e.filename || ''), line: e.lineno || 0 });
      if (window.__somewhere_err_log.length > 20) window.__somewhere_err_log.shift();
    } catch (_) {}
  }
  console.error('[SomeWhere] 全局错误:', e.message || e);
});
window.addEventListener('unhandledrejection', function (e) {
  const msg = (e && e.reason && (e.reason.message || e.reason)) || '未处理的 Promise 异常';
  console.error('[SomeWhere] 未处理异常:', msg);
  if (typeof e.preventDefault === 'function') e.preventDefault();
});
