/* SomeWhere绀惧尯 - 鍏叡 JS锛欰PI 灏佽 / 鐧诲綍鎬?/ 瀵艰埅 / Toast / 绌烘€?/ 鐢宠瘔 */
/* 鍥炬爣搴擄細static/icons/icon-*.svg锛?6 涓粦鐧界嚎鎬у浘鏍囷級锛実etIcon(name, size) 杩斿洖鍐呰仈 SVG 瀛楃涓?*/
const ICONS = {"appeal": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 2 4 5v6c0 5 3.4 8.6 8 11 4.6-2.4 8-6 8-11V5l-8-3z\"/><path d=\"M12 8v4\"/><path d=\"M12 16h.01\"/></svg>", "ban": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"m5.5 5.5 13 13\"/></svg>", "comment": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z\"/></svg>", "credit": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2\"/><path d=\"M7 9h4\"/><path d=\"m9 14 2 2 4-4\"/></svg>", "home": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 10 12 3l9 7\"/><path d=\"M5 9v12h5v-6h4v6h5V9\"/></svg>", "like": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M19.5 12.6 12 20l-7.5-7.4A5 5 0 1 1 12 7a5 5 0 1 1 7.5 5.6z\"/></svg>", "live": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"2.5\"/><path d=\"M7.5 16.5a6.5 6.5 0 0 1 0-9\"/><path d=\"M16.5 16.5a6.5 6.5 0 0 0 0-9\"/><path d=\"M4.5 19.5a10 10 0 0 1 0-15\"/><path d=\"M19.5 19.5a10 10 0 0 0 0-15\"/></svg>", "notification": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9\"/><path d=\"M13.7 21a2 2 0 0 1-3.4 0\"/></svg>", "post": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 20h9\"/><path d=\"M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z\"/></svg>", "review": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M9 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3\"/><rect x=\"9\" y=\"2\" width=\"6\" height=\"4\" rx=\"1\"/><path d=\"m9 13 2 2 4-4\"/></svg>", "search": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"11\" cy=\"11\" r=\"7\"/><path d=\"m21 21-4.3-4.3\"/></svg>", "settings": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.86 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z\"/></svg>", "share": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"18\" cy=\"5\" r=\"3\"/><circle cx=\"6\" cy=\"12\" r=\"3\"/><circle cx=\"18\" cy=\"19\" r=\"3\"/><path d=\"m8.6 13.5 6.8 4\"/><path d=\"m8.6 10.5 6.8-4\"/></svg>", "upload": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 16V4\"/><path d=\"m6 10 6-6 6 6\"/><path d=\"M4 20h16\"/></svg>", "pin": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 17v5\"/><path d=\"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z\"/></svg>", "user": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z\"/><path d=\"M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2\"/></svg>", "video": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"2\" y=\"6\" width=\"14\" height=\"12\" rx=\"2\"/><path d=\"m22 8-6 4 6 4V8z\"/></svg>"};
function getIcon(name, size = 20) {
  const svg = ICONS[name] || ICONS.search;
  return svg.replace('<svg ', '<svg class="icon" style="width:' + size + 'px;height:' + size + 'px" ');
}
/* 涓洪潤鎬?HTML 涓甫 data-icon 鐨勫厓绱犳敞鍏ュ浘鏍囷紙鍦ㄥ厓绱犲唴瀹瑰墠鎻掑叆锛?*/
function applyIcons() {
  document.querySelectorAll('[data-icon]').forEach(el => {
    if (el.classList.contains('card-title')) return; // 鍒嗙粍鏍囬缁熶竴璧?applyCardTitles锛坒a 鍥炬爣锛?    const name = el.getAttribute('data-icon');
    const size = Number(el.getAttribute('data-icon-size')) || 14;
    el.insertAdjacentHTML('afterbegin', getIcon(name, size));
  });
}

/* ===== 瑙嗚鏀归€狅細Font Awesome 鍥炬爣鏄犲皠 / 褰╄壊鍒嗙被 / 灏侀潰 ===== */
const FA_ICONS = {
  home: 'fa-house', post: 'fa-pen', upload: 'fa-upload', video: 'fa-film', live: 'fa-broadcast-tower',
  credit: 'fa-shield-heart', review: 'fa-clipboard-check', appeal: 'fa-scale-balanced',
  user: 'fa-user', settings: 'fa-gear', search: 'fa-magnifying-glass', notification: 'fa-bell', log: 'fa-clock',
  ban: 'fa-ban', comment: 'fa-comment', like: 'fa-heart', share: 'fa-share-nodes',
};
const CAT_ICONS = {
  '鎺ㄨ崘': 'fa-fire', '绉戞妧': 'fa-microchip', '娓告垙': 'fa-gamepad', '褰辫': 'fa-clapperboard',
  '鏁扮爜': 'fa-mobile-screen-button', '浣撹偛': 'fa-futbol', '鐢熸椿': 'fa-mug-hot',
  '姹傚姪': 'fa-circle-question', '闂茶亰': 'fa-comments',
};
const CAT_COLORS = {
  '鎺ㄨ崘': '#111111', '绉戞妧': '#2563eb', '娓告垙': '#7c3aed', '褰辫': '#db2777', '鏁扮爜': '#0891b2',
  '浣撹偛': '#16a34a', '鐢熸椿': '#ea580c', '姹傚姪': '#dc2626', '闂茶亰': '#64748b',
};
function faIcon(name, cls) {
  return '<i class="fa-solid ' + (FA_ICONS[name] || 'fa-circle-dot') + (cls ? ' ' + cls : '') + '"></i>';
}
function catColor(c) { return CAT_COLORS[c] || '#555555'; }
/* 瑙嗛/鐩存挱鍗＄墖灏侀潰锛氭寜鏍囬鍏抽敭璇嶅尮閰嶇湡瀹炵礌鏉愶紝鍏滃簳鎸?id 杞崲 */
function coverFor(id, title) {
  const t = String(title || '').toLowerCase();
  const pairs = [
    ['绡悆', 'uploads/covers/cover_basketball_1.jpg'], ['basketball', 'uploads/covers/cover_basketball_1.jpg'],
    ['瓒崇悆', 'uploads/covers/cover_football_1.jpg'], ['football', 'uploads/covers/cover_football_1.jpg'],
    ['娓告垙', 'uploads/covers/cover_game_1.jpg'], ['game', 'uploads/covers/cover_game_1.jpg'], ['鐢电珵', 'uploads/covers/cover_game_1.jpg'],
    ['绉戞妧', 'uploads/rule_tech_1.jpg'], ['tech', 'uploads/rule_tech_1.jpg'], ['鏁扮爜', 'uploads/rule_tech_1.jpg'], [' ai', 'uploads/rule_tech_1.jpg'],
    ['鑷劧', 'uploads/rule_nature_1.jpg'], ['nature', 'uploads/rule_nature_1.jpg'], ['椋庢櫙', 'uploads/rule_nature_1.jpg'],
    ['鍩庡競', 'uploads/rule_scene_1.jpg'], ['city', 'uploads/rule_scene_1.jpg'], ['鐢熸椿', 'uploads/rule_scene_1.jpg'],
  ];
  for (const [k, p] of pairs) if (t.includes(k)) return p + '?v=20261027';
  const pool = ['uploads/covers/cover_basketball_1.jpg', 'uploads/covers/cover_football_1.jpg', 'uploads/covers/cover_game_1.jpg',
    'uploads/rule_tech_1.jpg', 'uploads/rule_nature_1.jpg', 'uploads/rule_scene_1.jpg'];
  return pool[Math.abs(Number(id) || 0) % pool.length] + '?v=20261027';
}

// 瑙嗛灏侀潰锛氫紭鍏堢敤鎴蜂笂浼犲皝闈紙鏈夌缉鐣ュ浘鐢ㄧ缉鐣ュ浘锛夛紝鍚﹀垯鍥為€€ coverFor 棰勮鍥撅紙鎵规涓夛級
function videoCover(v) {
  if (v && v.cover_url) return (v.thumb_url || v.cover_url) + '?v=20261027';
  return coverFor(v && v.id, v && v.title);
}
/* 鍒嗙粍鏍囬缁熶竴娉ㄥ叆 fa 鍥炬爣锛坉ata-icon 宸叉湁鍒欏鐢ㄥ悓鍚嶆槧灏勶紝閬垮厤閲嶅 SVG锛?*/
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
    const msg = data && data.detail ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : ('璇锋眰澶辫触 ' + r.status);
    if (r.status === 401) {
      localStorage.removeItem('token'); localStorage.removeItem('user');
      // 鐧诲綍椤佃嚜韬け璐ヤ笉璺宠浆锛岄伩鍏嶆寰幆锛涘叾浣欓〉闈㈢粺涓€璺崇櫥褰?      if (!/login\.html([?#]|$)/.test(location.href)) location.href = 'login.html';
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

/* Toast锛歴uccess / error / warning / info 涓夋€?锛堥粯璁?info锛?*/
function showToast(msg, type = 'info') {
  const d = document.createElement('div');
  d.className = 'alert-bar ' + (type || 'info');
  d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 2600);
}
/* 鍏煎鏃ц皟鐢?toast(msg, ok) */
function toast(msg, ok = false) {
  showToast(msg, ok ? 'success' : 'error');
}

/* 绌烘€佺粺涓€娓叉煋 */
function renderEmpty(container, text) {
  if (!container) return;
  container.innerHTML = `<div class="empty-tip">${getIcon('search', 18)} ${esc(text || '鏆傛棤鍐呭')}</div>`;
}

/* 婊氬姩鍒板簳閮ㄨ嚜鍔ㄥ姞杞戒笅涓€椤?*/
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
      tail.textContent = '鍔犺浇涓?..';
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

/* 鐢宠瘔寮圭獥锛坰ource_type: posts/comments/video_comment/danmaku/live锛宻ource_id 蹇呭～锛?*/
function openAppeal(sourceType, sourceId, extraText) {
  if (!isLogin()) { showToast('璇峰厛鐧诲綍', 'warning'); location.href = 'login.html'; return; }
  const mask = document.createElement('div');
  mask.className = 'appeal-mask';
  mask.innerHTML = `
    <div class="appeal-box">
      <div class="card-title">鎻愪氦鐢宠瘔 <span class="hot-tag" style="background:#000000;color:#ffffff;border:1px solid #ffffff">APPEAL</span></div>
      <div class="hint" style="margin-bottom:10px">${esc(extraText || '璇ュ唴瀹瑰洜杩濊琚姌鍙?灏佺锛屽璁や负璇垽鍙彁浜ょ敵璇夛紝绠＄悊鍛樺皢鍦ㄥ瓨鐤戦槦鍒楀鐞嗐€?)}</div>
      <textarea class="form-input" id="appealReason" placeholder="璇峰～鍐欑敵璇夌悊鐢憋紙蹇呭～锛岃嚦灏?2 瀛楋級"></textarea>
      <div style="display:flex;gap:10px;margin-top:12px">
        <button class="btn primary" onclick="submitAppeal(this)">鎻愪氦鐢宠瘔</button>
        <button class="btn" onclick="closeAppeal(this)">鍙栨秷</button>
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
  if (!reason || reason.length < 2) { showToast('璇峰～鍐欑敵璇夌悊鐢憋紙鑷冲皯 2 瀛楋級', 'warning'); return; }
  btn.disabled = true;
  try {
    const res = await API.post('/api/appeals', { source_type: mask._st, source_id: mask._sid, reason });
    showToast('鐢宠瘔宸叉彁浜わ紝绛夊緟绠＄悊鍛樺鐞?, 'success');
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
      label: '绀惧尯',
      items: [
        ['index.html', '鎺ㄨ崘', 'home'],
        ['video.html', '瑙嗛', 'video'],
        ['live_list.html', '鐩存挱', 'live'],
      ],
    },
    {
      label: '鍙戝竷',
      items: [
        ['publish.html', '鍙戝笘', 'post'],
        ['publish.html?tab=video', '涓婁紶瑙嗛', 'upload'],
      ],
    },
  ];
  if (isAdmin) {
    groups.push({
      label: '绠＄悊',
      items: [
        ['video_review.html', '瑙嗛瀹℃牳', 'review'],
        ['review_queue.html', '瀛樼枒闃熷垪', 'appeal'],
        ['user_manage.html', '鐢ㄦ埛绠＄悊', 'user'],
        ['admin.html', '瀹℃牳鍙?, 'settings'],
        ['audit_logs.html', '瀹¤鏃ュ織', 'log'],
      ],
    });
  }
  nav.innerHTML = `
    <div class="nav-inner">
      <button class="nav-toggle" onclick="toggleNav()" aria-label="鑿滃崟"><i class="fa-solid fa-bars"></i></button>
      <a href="index.html" class="logo">SomeWhere绀惧尯</a>
      <nav class="nav-links" id="navLinks">
        ${groups.map((g, gi) => `
          ${gi ? '<span class="nav-sep"></span>' : ''}
          ${g.items.map(l => `<a href="${l[0]}" ${activePage && activePage === l[0].split('?')[0].replace('.html', '') ? 'class="active"' : ''}>${faIcon(l[2] || 'home', 'nav-fa')}<span class="nav-txt">${l[1]}</span></a>`).join('')}
        `).join('')}
      </nav>
      <div class="nav-search"><input id="navKw" placeholder="鎼滅储甯栧瓙 / 瑙嗛..."><button onclick="navSearch()">${faIcon('search', 'nav-fa')} 鎼滅储</button></div>
      <div class="nav-right" id="navRight">
        ${u ? `
          <span class="user"><span class="avatar">${esc((u.nickname || u.username || '?').slice(0, 1))}</span>
          <span>${esc(u.nickname || u.username)}</span>
          <span class="credit">淇＄敤 ${esc(u.credit_score)}</span>
          <a href="profile.html"><button class="btn sm">${faIcon('credit', 'nav-fa')} 鎴戠殑淇＄敤</button></a>
          ${u.role === 'admin' ? '<span class="chip blocked">绠＄悊鍛?/span>' : ''}
          <button class="btn sm logout" onclick="logout()">閫€鍑?/button></span>` : `
          <a href="login.html"><button class="btn primary">${faIcon('user', 'nav-fa')} 鐧诲綍 / 娉ㄥ唽</button></a>`}
      </div>
    </div>
    <div class="cats"><div class="cats-inner" id="catBar"></div></div>`;
  if (activePage === 'index') {
    const cats = ['鎺ㄨ崘', '绉戞妧', '娓告垙', '褰辫', '鏁扮爜', '浣撹偛', '鐢熸椿', '姹傚姪', '闂茶亰'];
    document.getElementById('catBar').innerHTML = cats.map(c => {
      const act = (new URLSearchParams(location.search).get('cat') || '鎺ㄨ崘') === c;
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

/* 鐢ㄦ埛涓婚〉璺宠浆閾炬帴锛歶serId 缂哄け鏃朵笉鐢熸垚閾炬帴锛堝師鏍疯繑鍥炲唴瀹癸級 */
function userLink(userId, innerHtml) {
  if (userId == null || userId === '') return innerHtml || '';
  return `<a class="user-link" href="user_page.html?id=${userId}" onclick="event.stopPropagation()">${innerHtml || ''}</a>`;
}

function timeAgo(s) {
  if (!s) return '';
  const t = new Date(String(s).replace(' ', 'T'));
  const diff = (Date.now() - t.getTime()) / 1000;
  if (diff < 60) return '鍒氬垰';
  if (diff < 3600) return Math.floor(diff / 60) + ' 鍒嗛挓鍓?;
  if (diff < 86400) return Math.floor(diff / 3600) + ' 灏忔椂鍓?;
  return String(s).slice(0, 10);
}

/* 绂荤嚎缂撳瓨锛氭敞鍐?Service Worker锛堟壒娆′簩锛夈€俵ocalhost/HTTPS 涓嬬敓鏁堬紝澶辫触闈欓粯涓嶅奖鍝嶅姛鑳?*/
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
