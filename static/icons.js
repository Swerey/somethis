/* SomeWhere社区 - 图标模块（批次C拆分自 common.js）
 * 图标库：内联 SVG（黑白线性），getIcon(name, size) 返回内联 SVG 字符串 */
const ICONS = {"appeal": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 2 4 5v6c0 5 3.4 8.6 8 11 4.6-2.4 8-6 8-11V5l-8-3z\"/><path d=\"M12 8v4\"/><path d=\"M12 16h.01\"/></svg>", "ban": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"m5.5 5.5 13 13\"/></svg>", "comment": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z\"/></svg>", "credit": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2\"/><path d=\"M7 9h4\"/><path d=\"m9 14 2 2 4-4\"/></svg>", "home": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 10 12 3l9 7\"/><path d=\"M5 9v12h5v-6h4v6h5V9\"/></svg>", "like": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M19.5 12.6 12 20l-7.5-7.4A5 5 0 1 1 12 7a5 5 0 1 1 7.5 5.6z\"/></svg>", "live": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"2.5\"/><path d=\"M7.5 16.5a6.5 6.5 0 0 1 0-9\"/><path d=\"M16.5 16.5a6.5 6.5 0 0 0 0-9\"/><path d=\"M4.5 19.5a10 10 0 0 1 0-15\"/><path d=\"M19.5 19.5a10 10 0 0 0 0-15\"/></svg>", "notification": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9\"/><path d=\"M13.7 21a2 2 0 0 1-3.4 0\"/></svg>", "post": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 20h9\"/><path d=\"M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z\"/></svg>", "review": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M9 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3\"/><rect x=\"9\" y=\"2\" width=\"6\" height=\"4\" rx=\"1\"/><path d=\"m9 13 2 2 4-4\"/></svg>", "search": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"11\" cy=\"11\" r=\"7\"/><path d=\"m21 21-4.3-4.3\"/></svg>", "settings": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.86 1 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z\"/></svg>", "share": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"18\" cy=\"5\" r=\"3\"/><circle cx=\"6\" cy=\"12\" r=\"3\"/><circle cx=\"18\" cy=\"19\" r=\"3\"/><path d=\"m8.6 13.5 6.8 4\"/><path d=\"m8.6 10.5 6.8-4\"/></svg>", "upload": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 16V4\"/><path d=\"m6 10 6-6 6 6\"/><path d=\"M4 20h16\"/></svg>", "pin": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 17v5\"/><path d=\"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1z\"/></svg>", "user": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z\"/><path d=\"M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2\"/></svg>", "video": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"2\" y=\"6\" width=\"14\" height=\"12\" rx=\"2\"/><path d=\"m22 8-6 4 6 4V8z\"/></svg>", "bars": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\"><path d=\"M4 6h16\"/><path d=\"M4 12h16\"/><path d=\"M4 18h16\"/></svg>", "chevron-down": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>", "chevron-left": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m15 18-6-6 6-6\"/></svg>", "chevron-right": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m9 18 6-6-6-6\"/></svg>", "menu": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"24\" height=\"24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\"><circle cx=\"5\" cy=\"12\" r=\"1\"/><circle cx=\"12\" cy=\"12\" r=\"1\"/><circle cx=\"19\" cy=\"12\" r=\"1\"/></svg>"};
function getIcon(name, size = 20) {
  const svg = ICONS[name] || ICONS.search;
  return svg.replace('<svg ', '<svg class="icon" style="width:' + size + 'px;height:' + size + 'px" ');
}
/* 为静态 HTML 中带 data-icon 的元素注入图标（在元素内容前插入）*/
function applyIcons() {
  document.querySelectorAll('[data-icon]').forEach(el => {
    if (el.classList.contains('card-title')) return; // 分组标题统一走 applyCardTitles
    const name = el.getAttribute('data-icon');
    const size = Number(el.getAttribute('data-icon-size')) || 14;
    el.insertAdjacentHTML('afterbegin', getIcon(name, size));
  });
}

/* ===== 图标映射：全部收敛到内联 SVG 体系（批次B-3 轻量替换 Font Awesome） ===== */
const FA_ICONS = {
  home: 'home', post: 'post', upload: 'upload', video: 'video', live: 'live',
  credit: 'credit', review: 'review', appeal: 'appeal',
  user: 'user', settings: 'settings', search: 'search', notification: 'notification', log: 'notification',
  ban: 'ban', comment: 'comment', like: 'like', share: 'share',
};
const CAT_ICONS = {
  '推荐': 'search', '科技': 'settings', '游戏': 'video', '影视': 'live',
  '数码': 'settings', '体育': 'like', '生活': 'post',
  '求助': 'appeal', '闲聊': 'comment',
};
const CAT_COLORS = {
  '推荐': '#111111', '科技': '#2563eb', '游戏': '#7c3aed', '影视': '#db2777', '数码': '#0891b2',
  '体育': '#16a34a', '生活': '#ea580c', '求助': '#dc2626', '闲聊': '#64748b',
};
/* faIcon(name, cls)：兼容旧签名，输出内联 SVG（替换原 <i class="fa-solid ...">）*/
function faIcon(name, cls) {
  const key = (FA_ICONS[name] || (CAT_ICONS[name] || 'search'));
  return '<span class="fa-ic ' + (cls || '') + '" aria-hidden="true">' + getIcon(key, 14) + '</span>';
}
function catColor(c) { return CAT_COLORS[c] || '#555555'; }
/* 视频/直播卡片封面：按标题关键词匹配真实素材，兜底用 id 轮换 */
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
  for (const [k, p] of pairs) if (t.includes(k)) return p + '?v=20261029';
  const pool = ['uploads/covers/cover_basketball_1.jpg', 'uploads/covers/cover_football_1.jpg', 'uploads/covers/cover_game_1.jpg',
    'uploads/rule_tech_1.jpg', 'uploads/rule_nature_1.jpg', 'uploads/rule_scene_1.jpg'];
  return pool[Math.abs(Number(id) || 0) % pool.length] + '?v=20261029';
}

// 视频封面：优先用户上传封面（有缩略图用缩略图），否则回退 coverFor 预设图
function videoCover(v) {
  if (v && v.cover_url) return (v.thumb_url || v.cover_url) + '?v=20261029';
  return coverFor(v && v.id, v && v.title);
}
/* 分组标题统一注入 SVG 图标（兼容旧 fa 映射）*/
function applyCardTitles() {
  document.querySelectorAll('.card-title').forEach(el => {
    if (el.querySelector('.fa-ic, svg.icon')) return;
    const name = el.getAttribute('data-icon') || 'search';
    el.insertAdjacentHTML('afterbegin', faIcon(name, 'ct-icon'));
  });
}
document.addEventListener('DOMContentLoaded', applyIcons);
document.addEventListener('DOMContentLoaded', applyCardTitles);
