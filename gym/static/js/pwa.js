/* PWA glue, loaded on every page: service worker registration + "update available" toast, offline banner, install button/banner/iOS sheet,
   cleanup on logout, and the per-device Web Push switch on the account page. Everything degrades silently when a feature is missing. */
(function () {
  'use strict';
  var doc = document, root = doc.documentElement;
  var T = (doc.getElementById('pwa-i18n') || {}).dataset || {};
  function $(s, ctx) { return (ctx || doc).querySelector(s); }
  function $$(s, ctx) { return [].slice.call((ctx || doc).querySelectorAll(s)); }
  function store(op, k, v) {
    try { return op === 'get' ? localStorage.getItem(k) : localStorage.setItem(k, v); } catch (e) { return null; }
  }
  function csrf(ctx) {
    var m = doc.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    var i = $('[name=csrfmiddlewaretoken]', ctx);
    return i ? i.value : '';
  }

  // ---------- standalone (running as an installed app)
  function standalone() {
    return (window.matchMedia && (matchMedia('(display-mode: standalone)').matches || matchMedia('(display-mode: window-controls-overlay)').matches)) ||
      navigator.standalone === true || (doc.referrer || '').indexOf('android-app://') === 0;
  }
  if (standalone()) root.classList.add('pwa-standalone');

  // ---------- toasts
  function toast(text, btnText, onBtn) {
    var el = doc.createElement('div');
    el.className = 'pwa-toast'; el.setAttribute('role', 'status');
    var s = doc.createElement('span'); s.textContent = text; el.appendChild(s);
    if (btnText) {
      var b = doc.createElement('button'); b.type = 'button'; b.className = 'btn small primary'; b.textContent = btnText;
      b.addEventListener('click', function () { onBtn(); el.remove(); }); el.appendChild(b);
    }
    doc.body.appendChild(el);
    return el;
  }

  // ---------- service worker + update toast
  var hadController = false, reloading = false, updateToast = null;
  function showUpdate(worker) {
    if (updateToast) return;
    updateToast = toast(T.update || 'Update', T.updateBtn || 'OK', function () { worker.postMessage({ type: 'SKIP_WAITING' }); });
  }
  if ('serviceWorker' in navigator) {
    hadController = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', function () {
      if (!hadController || reloading) return;  // the very first install also "changes" the controller: no reload then
      reloading = true; location.reload();
    });
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(function (reg) {
        if (reg.waiting && navigator.serviceWorker.controller) showUpdate(reg.waiting);
        reg.addEventListener('updatefound', function () {
          var nw = reg.installing;
          if (!nw) return;
          nw.addEventListener('statechange', function () { if (nw.state === 'installed' && navigator.serviceWorker.controller) showUpdate(nw); });
        });
        doc.addEventListener('visibilitychange', function () { if (!doc.hidden) reg.update().catch(function () {}); });
      }).catch(function () {});
    });
  }

  // ---------- offline banner
  var offBar = null;
  function netState() {
    if (navigator.onLine === false) {
      if (!offBar) { offBar = doc.createElement('div'); offBar.className = 'pwa-offline'; offBar.setAttribute('role', 'status'); offBar.textContent = T.offline || 'Offline'; doc.body.appendChild(offBar); }
    } else if (offBar) { offBar.remove(); offBar = null; }
  }
  window.addEventListener('online', netState); window.addEventListener('offline', netState);
  netState();

  // ---------- install button / banner / iOS sheet
  var deferred = null;
  var ua = navigator.userAgent || '';
  var isIOS = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var iosSafari = isIOS && !/CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(ua);
  var DISMISS = 'fz-pwa-dismiss', DAYS = 14;
  function dismissed() {
    var t = parseInt(store('get', DISMISS), 10);
    return !!t && Date.now() - t < DAYS * 864e5;
  }
  function refreshInstall() {
    var can = !standalone() && (!!deferred || iosSafari);
    $$('[data-pwa-install]').forEach(function (el) {
      var show = can && !(el.hasAttribute('data-pwa-banner') && dismissed());
      el.hidden = !show;
    });
  }
  window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); deferred = e; refreshInstall(); });
  window.addEventListener('appinstalled', function () { deferred = null; root.classList.add('pwa-standalone'); refreshInstall(); });
  refreshInstall();

  var sheet = $('[data-pwa-ios]');
  function closeSheet() { if (sheet) sheet.hidden = true; }
  doc.addEventListener('click', function (e) {
    var inst = e.target.closest('[data-pwa-install-btn]');
    if (inst) {
      e.preventDefault();
      if (deferred) {
        var d = deferred; deferred = null;
        d.prompt(); d.userChoice.then(refreshInstall, refreshInstall);
      } else if (iosSafari && sheet) sheet.hidden = false;
      return;
    }
    if (e.target.closest('[data-pwa-dismiss]')) { store('set', DISMISS, String(Date.now())); refreshInstall(); return; }
    if (e.target.closest('[data-pwa-close]') || e.target === sheet) closeSheet();
  });
  doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeSheet(); });

  // ---------- Web Push (account page)
  function b64(s) {
    var p = '='.repeat((4 - s.length % 4) % 4), r = atob((s + p).replace(/-/g, '+').replace(/_/g, '/')), a = new Uint8Array(r.length);
    for (var i = 0; i < r.length; i++) a[i] = r.charCodeAt(i);
    return a;
  }
  function post(url, body, ctx) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(ctx), 'X-Requested-With': 'fetch' }, body: JSON.stringify(body) });
  }
  var box = $('[data-push]');
  if (box) {
    var btn = $('[data-push-btn]', box), label = $('[data-push-label]', box), state = $('[data-push-state]', box);
    var supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    box.hidden = false;
    var render = function (sub) {
      var on = !!sub && Notification.permission === 'granted';
      state.textContent = Notification.permission === 'denied' ? (T.pushDenied || '') : (on ? T.pushEnabled : T.pushInactive);
      label.textContent = on ? T.pushOff : T.pushOn;
      btn.dataset.on = on ? '1' : '';
      btn.disabled = Notification.permission === 'denied';
    };
    var current = function () { return navigator.serviceWorker.ready.then(function (reg) { return reg.pushManager.getSubscription().then(function (s) { return { reg: reg, sub: s }; }); }); };
    if (!supported) {
      state.textContent = T.pushUnsupported || ''; btn.hidden = true;
    } else {
      current().then(function (c) { render(c.sub); }).catch(function () {});
      btn.addEventListener('click', function () {
        btn.disabled = true;
        current().then(function (c) {
          if (btn.dataset.on && c.sub) {  // switch off on this device
            return post('/push/unsubscribe/', { endpoint: c.sub.endpoint }, box).then(function () { return c.sub.unsubscribe(); }).then(function () { render(null); });
          }
          return Notification.requestPermission().then(function (perm) {
            if (perm !== 'granted') { render(null); return; }
            var subscribe = function () { return c.reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(box.dataset.key) }); };
            return (c.sub ? c.sub.unsubscribe() : Promise.resolve()).then(subscribe).then(function (sub) {
              return post('/push/subscribe/', sub.toJSON(), box).then(function (r) {
                if (!r.ok) { sub.unsubscribe(); throw new Error('server'); }
                render(sub);
              });
            });
          });
        }).catch(function () { state.textContent = T.pushErr || ''; }).then(function () { btn.disabled = Notification.permission === 'denied'; });
      });
    }
  }

  // ---------- logout: forget the offline card and stop pushes to this device, then sign out
  doc.addEventListener('submit', function (e) {
    var f = e.target;
    if (!f.matches || !f.matches('form[data-pwa-logout]') || f.dataset.done) return;
    if (!('serviceWorker' in navigator)) return;
    e.preventDefault();
    var finish = function () { f.dataset.done = '1'; f.submit(); };
    var work = navigator.serviceWorker.ready.then(function (reg) {
      if (reg.active) reg.active.postMessage({ type: 'CLEAR_PRIVATE' });
      return reg.pushManager ? reg.pushManager.getSubscription().then(function (sub) {
        if (!sub) return;
        return post('/push/unsubscribe/', { endpoint: sub.endpoint }, f).catch(function () {}).then(function () { return sub.unsubscribe(); });
      }) : null;
    }).catch(function () {});
    var timer = new Promise(function (res) { setTimeout(res, 1500); });
    Promise.race([work, timer]).then(finish, finish);
  });
})();
