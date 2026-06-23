/* ═══════════════════════════════════════════════════════════════════
   ZKR Analiz Pro — Service Worker v2.0 (FAZ 43 PWA)
   Cache-first for app shell, network-first for pages, offline fallback
   ═══════════════════════════════════════════════════════════════════ */

const CACHE_VERSION = 'zkr-analiz-v1';
const SHELL_CACHE  = CACHE_VERSION + '-shell';
const PAGE_CACHE   = CACHE_VERSION + '-pages';
const IMG_CACHE    = CACHE_VERSION + '-images';

// App shell: CSS, JS, fonts, icons — cache-first
const APP_SHELL = [
  '/static/css/design_system.css',
  '/static/css/layout.css',
  '/static/css/components.css',
  '/static/css/animations.css',
  '/static/css/widgets.css',
  '/static/css/mobile_components.css',
  '/static/css/terminal.css',
  '/static/css/discover.css',
  '/static/js/components/toast.js',
  '/static/js/notifications.js',
  '/static/js/pwa_install.js',
  '/static/js/mobile_nav.js',
  '/static/js/utils.js',
  '/static/manifest.json',
  '/static/icon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Pages to pre-cache for offline
const OFFLINE_PAGES = [
  '/discover',
  '/offline',
];

/* ── Install ─────────────────────────────────────────────────── */
self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(SHELL_CACHE).then((c) => c.addAll(APP_SHELL)).catch(() => {}),
      caches.open(PAGE_CACHE).then((c) => c.addAll(OFFLINE_PAGES)).catch(() => {}),
    ]).then(() => self.skipWaiting())
  );
});

/* ── Activate — clean old caches ─────────────────────────────── */
self.addEventListener('activate', (event) => {
  const keep = new Set([SHELL_CACHE, PAGE_CACHE, IMG_CACHE]);
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/* ── Fetch strategy ──────────────────────────────────────────── */
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Skip: API, WebSocket, external origins
  if (url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/ws') ||
      url.pathname.startsWith('/sock') ||
      url.origin !== self.location.origin) {
    return;
  }

  // Static assets → cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(req, SHELL_CACHE));
    return;
  }

  // HTML pages → network-first with offline fallback
  if (req.headers.get('accept') && req.headers.get('accept').includes('text/html')) {
    event.respondWith(networkFirstPage(req));
    return;
  }

  // Everything else → stale-while-revalidate
  event.respondWith(staleWhileRevalidate(req, IMG_CACHE));
});

/* ── Cache-first (static assets) ─────────────────────────────── */
async function cacheFirst(req, cacheName) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res && res.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    return cached || new Response('', { status: 408 });
  }
}

/* ── Network-first (HTML pages) with offline fallback ────────── */
async function networkFirstPage(req) {
  try {
    const res = await fetch(req);
    if (res && res.status === 200) {
      const cache = await caches.open(PAGE_CACHE);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    const cached = await caches.match(req);
    if (cached) return cached;
    // Offline fallback page
    const fallback = await caches.match('/offline');
    return fallback || new Response('<h1>Offline</h1><p>No connection available.</p>',
      { headers: { 'Content-Type': 'text/html' } });
  }
}

/* ── Stale-while-revalidate ──────────────────────────────────── */
async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const fetchPromise = fetch(req).then((res) => {
    if (res && res.status === 200) cache.put(req, res.clone());
    return res;
  }).catch(() => cached);
  return cached || fetchPromise;
}

/* ── Push notification handler (FAZ 43 ready) ────────────────── */
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    event.waitUntil(
      self.registration.showNotification(data.title || 'ZKR Analiz Pro', {
        body: data.body || '',
        icon: '/static/icons/icon-192.png',
        badge: '/static/icons/icon-192.png',
        tag: data.tag || 'bw-notification',
        data: { url: data.url || '/discover' },
      })
    );
  } catch (e) { /* ignore malformed push */ }
});

/* ── Notification click → open page ──────────────────────────── */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/discover';
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(url) && 'focus' in client) return client.focus();
      }
      return self.clients.openWindow(url);
    })
  );
});
