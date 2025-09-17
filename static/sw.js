/* Lightweight service worker to improve perceived cold-start on navigation.
 * Strategy: network-first with short timeout for navigations; fallback to cached shell or minimal inline skeleton.
 */
const CACHE_NAME = 'mlb-shell-v2';
// Cache navigations under their own request URL, not a single shell.
// This avoids serving the wrong page when the network is slow.
const TIMEOUT_MS = 3000;

const FALLBACK_HTML = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Loading…</title><style>body{margin:0;font-family:Segoe UI,Roboto,Arial,sans-serif;background:#0b1e2a;color:#e5e7eb;display:flex;align-items:center;justify-content:center;height:100vh} .spinner{width:48px;height:48px;border:4px solid rgba(255,255,255,0.2);border-top-color:#4fd1c7;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}</style></head><body><div><div class="spinner"></div><div style="margin-top:12px;text-align:center;opacity:.85">Warming up…</div></div></body></html>`;

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    try {
      const cache = await caches.open(CACHE_NAME);
      // Pre-cache nothing heavy; shell will be cached on first successful navigation
      await cache.addAll([]);
    } catch (e) {}
  })());
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

function timeout(ms) { return new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms)); }

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only intercept top-level navigations
  const isNavigation = req.mode === 'navigate' || (req.destination === 'document');
  if (!isNavigation) return; // let API/static proceed normally

  event.respondWith((async () => {
    // Try network with timeout
    try {
      const controller = new AbortController();
      const t = setTimeout(() => controller.abort(), TIMEOUT_MS);
      const netResp = await fetch(req, { signal: controller.signal });
      clearTimeout(t);
      // On success, update cache asynchronously
      try {
        const cache = await caches.open(CACHE_NAME);
        // Cache by request URL, not a single shell key
        cache.put(req.url, netResp.clone());
      } catch (e) {}
      return netResp;
    } catch (e) {
      // Network slow or down: try cached shell
      try {
        const cache = await caches.open(CACHE_NAME);
        // Return the cached document for this exact URL if present
        const cached = await cache.match(req.url);
        if (cached) return cached;
      } catch (e2) {}
      // Last resort: inline minimal fallback
      return new Response(FALLBACK_HTML, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }
  })());
});
