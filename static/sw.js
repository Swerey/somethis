/* SomeWhere 社区离线缓存 Service Worker（批次二）
 * 策略：静态资源网络优先、失败回退缓存；API / WebSocket 一律放行不缓存。
 * 注册条件：仅 HTTPS 或 localhost（浏览器对 insecure context 不启用 SW）。
 */
const CACHE = 'somewhere-v1';

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) =>
      c.addAll(['/', '/index.html', '/common.css', '/common.js']).catch(() => null)
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // API / WebSocket 等动态请求不缓存，直接走网络
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) return;
  // 仅缓存本站静态资源
  if (url.origin !== location.origin) return;

  e.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => hit || caches.match('/index.html'))
      )
  );
});
