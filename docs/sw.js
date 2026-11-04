// Offline-Unterstützung: App-Hülle aus dem Cache, Nachrichten zuerst aus dem Netz.
const VERSION = "ainews-v1";
const HUELLE = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest",
                "icons/icon.svg", "icons/icon-192.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(HUELLE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;

  if (url.pathname.includes("/data/")) {
    e.respondWith(fetch(e.request).then((r) => {
      if (r.ok) { const kopie = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, kopie)); }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true })));
    return;
  }

  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then((treffer) => {
    const netz = fetch(e.request).then((r) => {
      if (r.ok) { const kopie = r.clone(); caches.open(VERSION).then((c) => c.put(e.request, kopie)); }
      return r;
    }).catch(() => treffer);
    return treffer || netz;
  }));
});
