// Service Worker básico — necesario para que Chrome habilite "Instalar"
const CACHE = 'qhapaq-v5';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => clients.claim())
  );
});

// Solo cachea assets estáticos; las llamadas API y la navegación (HTML)
// siempre van a la red para no quedarnos con una página vieja pegada.
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return; // API siempre en vivo
  if (e.request.mode === 'navigate') return;    // HTML siempre en vivo
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
