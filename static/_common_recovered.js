/* SomeWhere社区 - 公共 JS：API 封装 / 登录�?/ 导航 / Toast / 空�?/ 申诉 */
/* 图标库：static/icons/icon-*.svg�?6 个黑白线性图标），getIcon(name, size) 返回内联 SVG 字符�?*/
const ICONS = {"appeal": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 2 4 5v6c0 5 3.4 8.6 8 11 4.6-2.4 8-6 8-11V5l-8-3z\"/><path d=\"M12 8v4\"/><path d=\"M12 16h.01\"/></svg>", "ban": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"m5.5 5.5 13 13\"/></svg>", "comment": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z\"/></svg>", "credit": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2\"/><path d=\"M7 9h4\"/><path d=\"m9 14 2 2 4-4\"/></svg>", "home": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 10 12 3l9 7\"/><path d=\"M5 9v12h5v-6h4v6h5V9\"/></svg>", "like": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M19.5 12.6 12 20l-7.5-7.4A5 5 0 1 1 12 7a5 5 0 1 1 7.5 5.6z\"/></svg>", "live": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"2.5\"/><path d=\"M7.5 16.5a6.5 6.5 0 0 1 0-9\"/><path d=\"M16.5 16.5a6.5 6.5 0 0 0 0-9\"/><path d=\"M4.5 19.5a10 10 0 0 1 0-15\"/><path d=\"M19.5 19.5a10 10 0 0 0 0-15\"/></svg>", "notification": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9\"/><path d=\"M13.7 21a2 2 0 0 1-3.4 0\"/></svg>", "post": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 20h9\"/><path d=\"M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z\"/></svg>", "review": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M9 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3\"/><rect x=\"9\" y=\"2\" width=\"6\" height=\"4\" rx=\"1\"/><path d=\"m9 13 2 2 4-4\"/></svg>", "search": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"11\" cy=\"11\" r=\"7\"/><path d=\"m21 21-4.3-4.3\"/></svg>", "settings": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.86 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z\"/></svg>", "share": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"18\" cy=\"5\" r=\"3\"/><circle cx=\"6\" cy=\"12\" r=\"3\"/><circle cx=\"18\" cy=\"19\" r=\"3\"/><path d=\"m8.6 13.5 6.8 4\"/><path d=\"m8.6 10.5 6.8-4\"/></svg>", "upload": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 16V4\"/><path d=\"m6 10 6-6 6 6\"/><path d=\"M4 20h16\"/></svg>", "pin": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 17v5\"/><path d=\"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z\"/></svg>", "user": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z\"/><path d=\"M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2\"/></svg>", "video": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"2\" y=\"6\" width=\"14\" height=\"12\" rx=\"2\"/><path d=\"m22 8-6 4 6 4V8z\"/></svg>"};
function getIcon(name, size = 20) {
  const svg = ICONS[name] || ICONS.search;
  return svg.replace('<svg ', '<svg class="icon" style="width:' + size + 'px;height:' + size + 'px" ');
}
/* 为静�?HTML 中带 data-icon 的元素注入图标（在元素内容前插入�?*/
function applyIcons() {
  document.querySelectorAll('[data-icon]').forEach(el => {
    if (el.classList.contains('card-title')) return; // 分组标题统一�?applyCardTitles（fa 图标�?    const name = el.getAttribute('data-icon');
    const size = Number(el.getAttribute('data-icon-size')) || 14;
    el.insertAdjacentHTML('afterbegin', getIcon(name, size));
  });
}

/* ===== 视觉改造：Font Awesome 图标映射 / 彩色分类 / 封面 ===== */
const FA_ICONS = {
  home: 'fa-house', post: 'fa-pen', upload: 'fa-upload', video: 'fa-film', live: 'fa-broadcast-tower',
  credit: 'fa-shield-heart', review: 'fa-clipboard-check', appeal: 'fa-scale-balanced',
  user: 'fa-user', settings: 'fa-gear', search: 'fa-magnifying-glass', notification: 'fa-bell', log: 'fa-clock',
  ban: 'fa-ban', comment: 'fa-comment', like: 'fa-heart', share: 'fa-share-nodes',
};
const CAT_ICONS = {
  '推荐': 'fa-fire', '科技': 'fa-microchip', '游戏': 'fa-gamepad', '影视': 'fa-clapperboard',
  '数码': 'fa-mobile-screen-button', '体育': 'fa-futbol', '生活': 'fa-mug-hot',
  '求助': 'fa-circle-question', '闲聊': 'fa-comments',
};
const CAT_COLORS = {
  '推荐': '#111111', '科技': '#2563eb', '游戏': '#7c3aed', '影视': '#db2777', '数码': '#0891b2',
  '体育': '#16a34a', '生活': '#ea580c', '求助': '#dc2626', '闲聊': '#64748b',
};
function faIcon(name, cls) {
  return '<i class="fa-solid ' + (FA_ICONS[name] || 'fa-circle-dot') + (cls ? ' ' + cls : '') + '"></i>';
}
function catColor(c) { return CAT_COLORS[c] || '#555555'; }
/* 视频/直播卡片封面：按标题关键词匹配真实素材，兜底�?id 轮换 */
function coverFor(id, title) {
  const t = String(title || '').toLowerCase();
  const pairs = [
    ['篮球', 'uploads/covers/cover_basketball_1.jpg'], ['basketball', 'uploads/covers/cover_basketball_1.jpg'],
    ['足球', 'uploads/covers/cover_football_1.jpg'], ['football', 'uploads/covers/cover_football_1.jpg'],
    ['游戏', 'uploads/covers/cover_game_1.jpg'], ['game', 'uploads/covers/cover_game_1.jpg'], ['电竞', 'uploads/covers/cover_game_1.jpg'],
    ['科技', 'uploads/rule_tech_1.jpg'], ['tech', 'uploads/rule_tech_1.jpg'], ['数码', 'uploads/rule_tech_1.jpg'], [' ai', 'uploads/rule_tech_1.jpg'],
    ['自然', 'uploads/rule_nature_1.jpg'], ['nature', 'uploads/rule_nature_1.jpg'], ['风景', 'uploads/rule_nature_1.jpg'],
    ['城市', 'uploads/rule_scene_1.jpg'], ['city', 'uploads/rule_scene_1.jpg'], ['生活', 'uploads/rule_scene_1.jpg'],
  ];
  for (const [k, p] of pairs) if (t.includes(k)) return p + '?v=20261027';
  const pool = ['uploads/covers/cover_basketball_1.jpg', 'uploads/covers/cover_football_1.jpg', 'uploads/covers/cover_game_1.jpg',
    'uploads/rule_tech_1.jpg', 'uploads/rule_nature_1.jpg', 'uploads/rule_scene_1.jpg'];
  return pool[Math.abs(Number(id) || 0) % pool.length] + '?v=20261027';
}

// 视频封面：优先用户上传封面（有缩略图用缩略图），否则回退 coverFor 预设图（批次三）
function videoCover(v) {
  if (v && v.cover_url) return (v.thumb_url || v.cover_url) + '?v=20261027';
  return coverFor(v && v.id, v && v.title);
}
/* 分组标题统一注入 fa 图标（data-icon 已有则复用同名映射，避免重复 SVG�?*/
function applyCardTitles() {
  document.querySelectorAll('.card-title').forEach(el => {
    if (el.querySelector('.fa, svg.icon')) return;
    const name = el.getAttribute('data-icon') || 'search';
    el.insertAdjacentHTML('afterbegin', faIcon(name, 'ct-icon'));
  });
}
document.addEventListener('DOMContentLoaded', applyIcons);
document.addEventListener('DOMContentLoaded', applyCardTitles);

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
};

async function handle(r) {
  let data = null;
  try { data = await r.json(); } catch (e) { data = {}; }
  if (!r.ok) {
    const msg = data && data.detail ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : ('请求失败 ' + r.status);
    if (r.status === 401) {
      localStorage.removeItem('token'); localStorage.removeItem('user');
      // 登录页自身失败不跳转，避免死循环；其余页面统一跳登�?      if (!/login\.html([?#]|$)/.test(location.href)) location.href = 'login.html';
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

/* Toast：success / error / warning / info 三�?（默�?info�?*/
function showToast(msg, type = 'info') {
  const d = document.createElement('div');
  d.className = 'alert-bar ' + (type || 'info');
  d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 2600);
}
/* 兼容旧调�?toast(msg, ok) */
function toast(msg, ok = false) {
  showToast(msg, ok ? 'success' : 'error');
}

/* 空态统一渲染 */
function renderEmpty(container, text) {
  if (!container) return;
  container.innerHTML = `<div class="empty-tip">${getIcon('search', 18)} ${esc(text || '暂无内容')}</div>`;
}

/* 滚动到底部自动加载下一�?*/
function setupInfiniteScroll(opts) {
  const { container, loadMore, hasMore, threshold = 120 } = opts;
  if (container && container._infScroller) return container._infScroller;
  let loading = false;
  async function onScroll() {
    if (loading || !hasMore() || !container) return;
    const rect = container.getBoundingClientRect();
    if (rect.bottom <= window.innerHeight + threshold) {
      loading = true;
      const tail = document.getElementById('listTail') || createTail();
      tail.textContent = '加载�?..';
      try {
        await loadMore();
      } finally {
        if (!hasMore()) { tail.textContent = ''; } else { tail.textContent = ''; }
        loading = false;
      }
    }
  }
  function createTail() {
    const t = document.createElement('div');
    t.id = 'listTail';
    t.className = 'empty-tip';
    t.style.padding = '12px 0';
    container.parentNode && container.parentNode.insertBefore(t, container.nextSibling);
    return t;
  }
  window.addEventListener('scroll', onScroll);
  if (container) container._infScroller = onScroll;
  return onScroll;
}

/* 申诉弹窗（source_type: posts/comments/video_comment/danmaku/live，source_id 必填�?*/
function openAppeal(sourceType, sourceId, extraText) {
  if (!isLogin()) { showToast('请先登录', 'warning'); location.href = 'login.html'; return; }
  const mask = document.createElement('div');
  mask.className = 'appeal-mask';
  mask.innerHTML = `
    <div class="appeal-box">
      <div class="card-title">提交申诉 <span class="hot-tag" style="background:#000000;color:#ffffff;border:1px solid #ffffff">APPEAL</span></div>
      <div class="hint" style="margin-bottom:10px">${esc(extraText || '该内容因违规被折�?封禁，如认为误判可提交申诉，管理员将在存疑队列处理�?)}</div>
      <textarea class="form-input" id="appealReason" placeholder="请填写申诉理由（必填，至�?2 字）"></textarea>
      <div style="display:flex;gap:10px;margin-top:12px">
        <button class="btn primary" onclick="submitAppeal(this)">提交申诉</button>
        <button class="btn" onclick="closeAppeal(this)">取消</button>
      </div>
    </div>`;
  document.body.appendChild(mask);
  mask._st = sourceType;
  mask._sid = sourceId;
  setTimeout(() => { const ta = document.getElementById('appealReason'); ta && ta.focus(); }, 50);
}

function closeAppeal(btn) {
  const mask = btn.closest('.appeal-mask');
  mask && mask.remove();
}

async function submitAppeal(btn) {
  const mask = btn.closest('.appeal-mask');
  const reason = document.getElementById('appealReason').value.trim();
  if (!reason || reason.length < 2) { showToast('请填写申诉理由（至少 2 字）', 'warning'); return; }
  btn.disabled = true;
  try {
    const res = await API.post('/api/appeals', { source_type: mask._st, source_id: mask._sid, reason });
    showToast('申诉已提交，等待管理员处�?, 'success');
    mask.remove();
  } catch (e) {
    if (!e._toasted) showToast(e.message, 'error');
    btn.disabled = false;
  }
}

function renderNav(activePage) {
  const nav = document.getElementById('nav');
  if (!nav) return;
  const u = currentUser();
  const isAdmin = u && u.role === 'admin';
  const groups = [
    {
      label: '社区',
      items: [
        ['index.html', '推荐', 'home'],
        ['video.html', '视频', 'video'],
        ['live_list.html', '直播', 'live'],
      ],
    },
    {
      label: '发布',
      items: [
        ['publish.html', '发帖', 'post'],
        ['publish.html?tab=video', '上传视频', 'upload'],
      ],
    },
  ];
  if (isAdmin) {
    groups.push({
      label: '管理',
      items: [
        ['video_review.html', '视频审核', 'review'],
        ['review_queue.html', '存疑队列', 'appeal'],
        ['user_manage.html', '用户管理', 'user'],
        ['admin.html', '审核�?, 'settings'],
        ['audit_logs.html', '审计日志', 'log'],
      ],
    });
  }
  nav.innerHTML = `
    <div class="nav-inner">
      <button class="nav-toggle" onclick="toggleNav()" aria-label="菜单"><i class="fa-solid fa-bars"></i></button>
      <a href="index.html" class="logo">SomeWhere社区</a>
      <nav class="nav-links" id="navLinks">
        ${groups.map((g, gi) => `
          ${gi ? '<span class="nav-sep"></span>' : ''}
          ${g.items.map(l => `<a href="${l[0]}" ${activePage && activePage === l[0].split('?')[0].replace('.html', '') ? 'class="active"' : ''}>${faIcon(l[2] || 'home', 'nav-fa')}<span class="nav-txt">${l[1]}</span></a>`).join('')}
        `).join('')}
      </nav>
      <div class="nav-search"><input id="navKw" placeholder="搜索帖子 / 视频..."><button onclick="navSearch()">${faIcon('search', 'nav-fa')} 搜索</button></div>
      <div class="nav-right" id="navRight">
        ${u ? `
          <span class="user"><span class="avatar">${esc((u.nickname || u.username || '?').slice(0, 1))}</span>
          <span>${esc(u.nickname || u.username)}</span>
          <span class="credit">信用 ${esc(u.credit_score)}</span>
          <a href="profile.html"><button class="btn sm">${faIcon('credit', 'nav-fa')} 我的信用</button></a>
          ${u.role === 'admin' ? '<span class="chip blocked">管理�?/span>' : ''}
          <button class="btn sm logout" onclick="logout()">退�?/button></span>` : `
          <a href="login.html"><button class="btn primary">${faIcon('user', 'nav-fa')} 登录 / 注册</button></a>`}
      </div>
    </div>
    <div class="cats"><div class="cats-inner" id="catBar"></div></div>`;
  if (activePage === 'index') {
    const cats = ['推荐', '科技', '游戏', '影视', '数码', '体育', '生活', '求助', '闲聊'];
    document.getElementById('catBar').innerHTML = cats.map(c => {
      const act = (new URLSearchParams(location.search).get('cat') || '推荐') === c;
      return `<a href="index.html?cat=${encodeURIComponent(c)}" class="${act ? 'active' : ''}" ${act ? '' : 'style="color:' + catColor(c) + '"'}>${faIcon(CAT_ICONS[c] || 'search', 'cat-fa')} ${c}</a>`;
    }).join('');
  }
}

function toggleNav() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  nav.classList.toggle('nav-open');
}

function navSearch() {
  const kw = document.getElementById('navKw').value.trim();
  if (!kw) return;
  location.href = 'index.html?q=' + encodeURIComponent(kw);
}

function logout() {
  localStorage.removeItem('token'); localStorage.removeItem('user');
  location.href = 'index.html';
}

function esc(s) {
  return (s == null ? '' : String(s)).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* 用户主页跳转链接：userId 缺失时不生成链接（原样返回内容） */
function userLink(userId, innerHtml) {
  if (userId == null || userId === '') return innerHtml || '';
  return `<a class="user-link" href="user_page.html?id=${userId}" onclick="event.stopPropagation()">${innerHtml || ''}</a>`;
}

function timeAgo(s) {
  if (!s) return '';
  const t = new Date(String(s).replace(' ', 'T'));
  const diff = (Date.now() - t.getTime()) / 1000;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟�?;
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时�?;
  return String(s).slice(0, 10);
}

/* 离线缓存：注�?Service Worker（批次二）。localhost/HTTPS 下生效，失败静默不影响功�?*/
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
