/* Fitnes Zal service worker.
   What it keeps: (1) /static/ files (stale-while-revalidate), (2) the branded /offline/ page, (3) the signed-in member's /card/ page with its QR,
   so the card opens at the gym door without internet. Nothing else is ever stored: pages, admin, chat, payments, login and API answers always
   come from the network, so no one can see another person's data from a cache. The card cache is wiped on logout (message CLEAR_PRIVATE).
   __SW_VERSION__ is replaced by a hash of this file, so caches (and the "update available" toast) change only when the worker itself changes. */
var VERSION = '__SW_VERSION__';
var STATIC = 'fz-static-' + VERSION;
var PRIVATE = 'fz-private';  // member card; survives worker updates, removed on logout
var CARD = '/card/';

function staticUrls(html) {  // /static/... files a page refers to (css, js, images): the app shell
  var out = [], re = /(?:src|href)="(\/static\/[^"#]+)"/g, m;
  while ((m = re.exec(html))) if (out.indexOf(m[1]) < 0) out.push(m[1].replace(/&amp;/g, '&'));
  return out;
}

function precache() {
  return caches.open(STATIC).then(function (cache) {
    var shell = ['/offline/', '/'];
    return Promise.all(shell.map(function (p) {
      return fetch(p, { cache: 'reload', credentials: 'omit' }).then(function (res) {
        if (!res.ok) return [];
        var copy = res.clone();
        var keep = p === '/offline/' ? cache.put('/offline/', copy) : Promise.resolve();  // only the offline page itself is stored, not the home page
        return keep.then(function () { return res.text(); }).then(staticUrls);
      }).catch(function () { return []; });
    })).then(function (lists) {
      var urls = [].concat.apply([], lists).filter(function (u, i, a) { return a.indexOf(u) === i; });
      return Promise.all(urls.map(function (u) { return cache.add(new Request(u, { credentials: 'omit' })).catch(function () {}); }));
    });
  });
}

self.addEventListener('install', function (e) {
  // no skipWaiting here: the page shows "update available" and asks the worker to take over (message SKIP_WAITING)
  e.waitUntil(precache());
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf('fz-') === 0 && k !== STATIC && k !== PRIVATE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('message', function (e) {
  var d = e.data || {};
  if (d.type === 'SKIP_WAITING') self.skipWaiting();
  if (d.type === 'CLEAR_PRIVATE') e.waitUntil(caches.delete(PRIVATE));
});

function prune(cache, req) {  // keep one version of a file: drop older ?v= copies of the same path
  var u = new URL(req.url);
  return cache.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) {
      var x = new URL(k.url);
      return x.pathname === u.pathname && x.search !== u.search;
    }).map(function (k) { return cache.delete(k); }));
  });
}

function staticFile(e, req) {
  return caches.open(STATIC).then(function (cache) {
    return cache.match(req).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res && res.status === 200) { cache.put(req, res.clone()).then(function () { return prune(cache, req); }).catch(function () {}); }
        return res;
      }).catch(function () {
        return hit || cache.match(req, { ignoreSearch: true }).then(function (r) { return r || Response.error(); });
      });
      if (hit) e.waitUntil(net.catch(function () {}));  // refresh in the background
      return hit || net;
    });
  });
}

function page(req, url) {
  var isCard = url.pathname === CARD;
  return fetch(req).then(function (res) {
    if (isCard) {
      var marked = res.ok && res.headers.get('X-FZ-Offline') === 'card';
      var copy = marked ? res.clone() : null;
      return caches.open(PRIVATE).then(function (c) {
        // signed in: remember the card; signed out (login page came back): forget it
        return marked ? c.put(CARD, copy) : (res.ok ? c.delete(CARD) : null);
      }).catch(function () {}).then(function () { return res; });
    }
    return res;
  }).catch(function () {
    if (isCard) return caches.open(PRIVATE).then(function (c) { return c.match(CARD); }).then(function (r) { return r || caches.match('/offline/'); });
    return caches.match('/offline/');
  });
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.indexOf('/static/') === 0) { e.respondWith(staticFile(e, req)); return; }
  if (req.mode === 'navigate') e.respondWith(page(req, url));
});

// ---- Web Push
self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Fitnes Zal', {
    body: d.body || '', icon: d.icon || '/static/img/icon-192.png', badge: d.badge || '/static/img/badge-96.png',
    tag: d.tag || undefined, data: { url: d.url || '/' }
  }));
});

self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var target;
  try { target = new URL((e.notification.data && e.notification.data.url) || '/', location.origin); } catch (err) { target = new URL('/', location.origin); }
  if (target.origin !== location.origin) target = new URL('/', location.origin);
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
    for (var i = 0; i < list.length; i++) {
      var c = list[i];
      if (c.url.indexOf(location.origin) === 0 && 'focus' in c) {
        return c.focus().then(function (w) { return (w && 'navigate' in w) ? w.navigate(target.href) : w; });
      }
    }
    return self.clients.openWindow(target.href);
  }));
});
