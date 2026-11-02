/* SomeWhere社区 - UI 模块（批次C拆分自 common.js）：导航 / 空态 / 申诉 / 轮播置顶 / 工具函数 */

/* ===== 空态统一渲染（批次A-4：图标 + 主文案 + 行动按钮） ===== */
function renderEmpty(container, text, action) {
  if (!container) return;
  const act = (action && action.text)
    ? `<a class="btn primary sm empty-act" href="${esc(action.href || '#')}">${esc(action.text)}</a>`
    : '';
  container.innerHTML = `<div class="empty-tip">${getIcon('search', 18)}<span class="empty-main">${esc(text || '暂无内容')}</span>${act}</div>`;
}

/* 滚动到底部自动加载下一页 */
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
      tail.textContent = '加载中...';
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

/* 申诉弹窗（source_type: posts/comments/video_comment/danmaku/live，source_id 必填）*/
function openAppeal(sourceType, sourceId, extraText) {
  if (!isLogin()) { showToast('请先登录', 'warning'); location.href = 'login.html'; return; }
  const mask = document.createElement('div');
  mask.className = 'appeal-mask';
  mask.innerHTML = `
    <div class="appeal-box">
      <div class="card-title">提交申诉 <span class="hot-tag" style="background:var(--fg);color:var(--bg);border:1px solid var(--border)">APPEAL</span></div>
      <div class="hint" style="margin-bottom:10px">${esc(extraText || '该内容因违规被折叠/封禁，如认为误判可提交申诉，管理员将在存疑队列处理。')}</div>
      <textarea class="form-input" id="appealReason" placeholder="请填写申诉理由（必填，至少 2 字）"></textarea>
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
    showToast('申诉已提交，等待管理员处理', 'success');
    mask.remove();
  } catch (e) {
    if (!e._toasted) showToast(e.message, 'error');
    btn.disabled = false;
  }
}

/* ===== 导航渲染（批次C-1：移动端底部 Tab，5 项内；批次V-2：管理功能收进下拉防截断） ===== */
function renderNav(activePage) {
  const nav = document.getElementById('nav');
  if (!nav) return;
  const u = currentUser();
  const isAdmin = u && u.role === 'admin';
  const community = [
    ['index.html', '推荐', 'home'],
    ['video_list.html', '视频', 'video'],
    ['live_list.html', '直播', 'live'],
  ];
  const publish = [
    ['publish.html', '发帖', 'post'],
    ['publish.html?tab=video', '上传视频', 'upload'],
  ];
  const adminItems = [
    ['video_review.html', '视频审核', 'review'],
    ['review_queue.html', '存疑队列', 'appeal'],
    ['user_manage.html', '用户管理', 'user'],
    ['admin.html', '审核台', 'settings'],
    ['audit_logs.html', '审计日志', 'log'],
  ];
  const pageKey = activePage ? String(activePage).replace('.html', '') : '';
  const navLink = (l) => {
    const key = l[0].split('?')[0].replace('.html', '');
    return `<a href="${l[0]}" ${pageKey === key ? 'class="active"' : ''}>${faIcon(l[2] || 'home', 'nav-fa')}<span class="nav-txt">${l[1]}</span></a>`;
  };
  nav.innerHTML = `
    <div class="nav-inner">
      <button class="nav-toggle" onclick="toggleNav()" aria-label="打开菜单">${getIcon('bars', 18)}</button>
      <a href="index.html" class="logo">SomeWhere社区</a>
      <nav class="nav-links" id="navLinks" aria-label="主导航">
        ${community.map(navLink).join('')}
        <span class="nav-sep"></span>
        ${publish.map(navLink).join('')}
        ${isAdmin ? `
          <span class="nav-sep"></span>
          <details class="nav-drop" id="navAdminDrop">
            <summary>${faIcon('settings', 'nav-fa')} 管理 ${faIcon('chevron-down', 'nav-fa')}</summary>
            <div class="nav-drop-menu">
              ${adminItems.map(l => {
                const key = l[0].split('?')[0].replace('.html', '');
                return `<a href="${l[0]}" ${pageKey === key ? 'class="active"' : ''}>${faIcon(l[2] || 'settings', 'nav-fa')} ${l[1]}</a>`;
              }).join('')}
            </div>
          </details>` : ''}
      </nav>
      <div class="nav-search"><input id="navKw" placeholder="搜索帖子 / 视频..." aria-label="搜索关键词"><button onclick="navSearch()">${faIcon('search', 'nav-fa')} 搜索</button></div>
      <div class="nav-right" id="navRight">
        ${u ? `
          <span class="user"><span class="avatar" aria-hidden="true">${esc((u.nickname || u.username || '?').slice(0, 1))}</span>
          <span>${esc(u.nickname || u.username)}</span>
          <span class="credit">信用 ${esc(u.credit_score)}</span>
          <a href="profile.html"><button class="btn sm">${faIcon('credit', 'nav-fa')} 我的信用</button></a>
          ${u.role === 'admin' ? '<span class="chip blocked">管理员</span>' : ''}
          <button class="btn sm logout" onclick="logout()">退出</button></span>` : `
          <a href="login.html"><button class="btn primary">${faIcon('user', 'nav-fa')} 登录 / 注册</button></a>`}
      </div>
    </div>
    <div class="cats"><div class="cats-inner" id="catBar"></div></div>
    <div class="bottom-tab" role="navigation" aria-label="移动端快捷导航">
      ${[['index.html', '首页', 'home'], ['video_list.html', '视频', 'video'], ['live_list.html', '直播', 'live'], ['publish.html', '发布', 'post'], ['profile.html', '我的', 'user']].map(t => {
        const key = t[0].split('?')[0].replace('.html', '');
        return `<a href="${t[0]}" class="${pageKey === key ? 'active' : ''}" aria-current="${pageKey === key ? 'page' : 'false'}">${getIcon(t[2], 20)}<span>${t[1]}</span></a>`;
      }).join('')}
    </div>`;
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

/* ===== 工具函数 ===== */
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
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前';
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前';
  return String(s).slice(0, 10);
}

/* 离线缓存：注册 Service Worker（localhost/HTTPS 下生效，失败静默不影响功能） */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

/* ===== 轮播置顶弹窗（管理端通用） ===== */
let pinModalEl = null;
function openPinModal(kind, targetId, title) {
  if (pinModalEl) pinModalEl.remove();
  const mask = document.createElement('div');
  mask.className = 'appeal-mask';
  mask.style.zIndex = 100;
  mask.innerHTML = `
    <div class="appeal-box" style="max-width:420px">
      <div class="card-title">置顶轮播 <span class="hot-tag" style="background:var(--fg);color:var(--bg);border:1px solid var(--border)">CAROUSEL</span></div>
      <div class="hint" style="margin:0 0 10px">${esc(title)}（${kind === 'post' ? '帖子' : '视频'} #${targetId}）</div>
      <div id="pinState" class="hint" style="margin:0 0 10px">检查置顶状态...</div>
      <div class="hint" style="margin:0 0 4px">排序值（越小越靠前，0 最前）</div>
      <input class="form-input" id="pinSort" type="number" min="0" value="0" style="margin-bottom:10px" aria-label="排序值">
      <div class="hint" style="margin:0 0 4px">生效时间（留空立即生效）</div>
      <input class="form-input" id="pinStart" type="datetime-local" style="margin-bottom:10px" aria-label="生效时间">
      <div class="hint" style="margin:0 0 4px">截止时间（留空长期置顶）</div>
      <input class="form-input" id="pinEnd" type="datetime-local" style="margin-bottom:12px" aria-label="截止时间">
      <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">
        <button class="btn primary" onclick="submitPin('${kind}', ${targetId})">${getIcon('pin', 13)} 确认置顶</button>
        <button class="btn" onclick="closePin()">取消</button>
        <span style="flex:1"></span>
        <button class="btn danger sm" id="pinUnpinBtn" style="display:none" onclick="unpinCarousel(Number(this.dataset.pinId))">${getIcon('ban', 13)} 取消置顶</button>
      </div>
    </div>`;
  document.body.appendChild(mask);
  pinModalEl = mask;
  API.get('/api/carousel').then(res => {
    const hit = (res.items || []).find(x => x.kind === kind && x.target_id === targetId);
    const stateEl = document.getElementById('pinState');
    if (!stateEl) return;
    if (hit) {
      stateEl.innerHTML = '<span class="chip ok">当前已置顶</span> 排序 ' + hit.id + '（目标 #' + hit.target_id + '）';
      const btn = document.getElementById('pinUnpinBtn');
      btn.style.display = 'inline-block';
      btn.dataset.pinId = hit.id;
      btn.textContent = getIcon('ban', 13) + ' 取消置顶';
    } else {
      stateEl.textContent = '当前未置顶，置顶后优先展示在轮播。';
    }
  }).catch(() => {
    const stateEl = document.getElementById('pinState');
    if (stateEl) stateEl.textContent = '';
  });
}
function closePin() { if (pinModalEl) { pinModalEl.remove(); pinModalEl = null; } }
function dtToApi(v) { if (!v) return ''; return v.replace('T', ' '); }
async function submitPin(kind, targetId) {
  const sortOrder = parseInt(document.getElementById('pinSort').value, 10) || 0;
  const startAt = dtToApi(document.getElementById('pinStart').value);
  const endAt = dtToApi(document.getElementById('pinEnd').value);
  if (endAt && startAt && endAt <= startAt) { showToast('截止时间需晚于生效时间', 'warning'); return; }
  try {
    const res = await API.post('/api/admin/carousel', { item_type: kind, item_id: targetId, sort_order: sortOrder, start_at: startAt, end_at: endAt });
    showToast(res.updated ? '已更新置顶项' : '已置顶到轮播', 'success');
    closePin();
  } catch (e) { showToast(e.message, 'error'); }
}
async function unpinCarousel(pinId) {
  if (!confirm('确认取消该置顶？')) return;
  try {
    await API.del('/api/admin/carousel/' + pinId);
    showToast('已取消置顶', 'success');
  } catch (e) { showToast(e.message, 'error'); }
}
