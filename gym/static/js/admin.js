/* Admin niceties: sidebar drawer/collapse, user menu, collapsible filters, "/" jumps to the search box, numbers count up,
   and the dashboard's LIVE numbers refresh every 20 seconds. Everything works without it. */
document.addEventListener('DOMContentLoaded', function () {
  var q = document.getElementById('fz-q');
  document.addEventListener('keydown', function (e) {
    var t = e.target.tagName;
    if (e.key === '/' && q && t !== 'INPUT' && t !== 'TEXTAREA' && t !== 'SELECT' && !e.target.isContentEditable) { e.preventDefault(); q.focus(); q.select(); }
  });
  // broadcast page: ready-made texts, character counters and a live preview (text only, never HTML)
  var bf = document.querySelector('[data-broadcast]');
  if (bf) {
    var title = bf.elements.title, body = bf.elements.body;
    var who = bf.dataset.name || 'Aziz';  // personal messages show {ism} filled with the first recipient's name
    function fill(s) { return s.split('{ism}').join(who); }
    function sync() {
      document.querySelectorAll('[data-pv="title"]').forEach(function (e) { e.textContent = fill(title.value) || 'Sarlavha'; });
      document.querySelectorAll('[data-pv="body"]').forEach(function (e) { e.textContent = fill(body.value) || "Xabar matni shu yerda ko'rinadi…"; });
      bf.querySelectorAll('.bc-count').forEach(function (c) { var f = bf.elements[c.dataset.for]; c.textContent = f.value.length + ' / ' + f.maxLength; });
    }
    [title, body].forEach(function (f) { f.addEventListener('input', sync); });
    bf.querySelectorAll('.bc-presets [data-t]').forEach(function (b) {
      b.addEventListener('click', function () { title.value = b.dataset.t; body.value = b.dataset.b; sync(); body.focus(); });
    });
    bf.querySelectorAll('.fz-aud input').forEach(function (r) {
      r.addEventListener('change', function () { bf.querySelectorAll('.fz-aud label').forEach(function (l) { l.classList.toggle('on', l.contains(r) && r.checked); }); });
    });
    bf.addEventListener('submit', function () { var s = bf.querySelector('.bc-send'); if (s) s.classList.add('flying'); });
    // personal message: × takes a person off the list (and out of the search form's carried list too)
    bf.querySelectorAll('[data-drop]').forEach(function (x) {
      x.addEventListener('click', function () {
        x.closest('.msg-chip').remove();
        var left = [].map.call(bf.querySelectorAll('input[name="ids"]'), function (i) { return i.value; });
        var carry = document.querySelector('.msg-find input[name="ids"]'); if (carry) carry.value = left.join(',');
        var send = bf.querySelector('.bc-send'); if (send) send.disabled = !left.length;
      });
    });
    sync();
  }

  // sidebar: a drawer on phones (hamburger + scrim), collapsible to icons on desktop (remembered)
  var body = document.body, root = document.documentElement;
  function setDrawer(open) {
    body.classList.toggle('fz-nav-open', open);
    document.querySelectorAll('.fz-burger').forEach(function (b) { b.setAttribute('aria-expanded', open ? 'true' : 'false'); });
  }
  document.querySelectorAll('[data-fz-toggle]').forEach(function (b) {
    b.addEventListener('click', function () { setDrawer(!body.classList.contains('fz-nav-open')); });
  });
  document.querySelectorAll('.fz-nav-a').forEach(function (a) { a.addEventListener('click', function () { setDrawer(false); }); });
  var col = document.querySelector('[data-fz-collapse]');
  if (col) col.addEventListener('click', function () {
    var on = root.classList.toggle('fz-collapsed');
    try { localStorage.setItem('fz-side', on ? '0' : '1'); } catch (e) {}
  });
  var cur = document.querySelector('.fz-nav-a.on');
  if (cur && cur.scrollIntoView) { var nav = cur.closest('.fz-nav'); if (nav && (cur.offsetTop > nav.clientHeight - 60)) nav.scrollTop = cur.offsetTop - nav.clientHeight / 2; }

  // user menu closes on an outside click or Escape
  var um = document.querySelector('.fz-user');
  document.addEventListener('click', function (e) { if (um && um.open && !um.contains(e.target)) um.open = false; });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (um && um.open) { um.open = false; um.querySelector('summary').focus(); }
    if (body.classList.contains('fz-nav-open')) setDrawer(false);
  });

  // change lists: on small screens the filters panel hides behind a button
  var flt = document.getElementById('changelist-filter');
  if (flt) {
    var tg = document.createElement('button');
    tg.type = 'button'; tg.className = 'fz-filter-toggle'; tg.setAttribute('aria-expanded', 'false'); tg.setAttribute('aria-controls', 'changelist-filter');
    tg.textContent = 'Filtrlar';
    var holder = document.querySelector('#changelist .changelist-form-container');
    if (holder) holder.insertBefore(tg, holder.firstChild);
    var active = Array.from(new URLSearchParams(location.search).keys()).some(function (k) { return ['q', 'o', 'p', 'e', '_changelist_filters'].indexOf(k) < 0; });
    if (active) { flt.classList.add('fz-open'); tg.setAttribute('aria-expanded', 'true'); tg.textContent = 'Filtrlar (faol)'; }
    tg.addEventListener('click', function () { var o = flt.classList.toggle('fz-open'); tg.setAttribute('aria-expanded', o ? 'true' : 'false'); });
  }

  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function fmt(el, n) { el.textContent = el.hasAttribute('data-money') ? Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : Math.round(n); }
  function tween(el, from, to) {
    if (calm || from === to) { fmt(el, to); return; }
    var t0 = null;
    function step(t) { t0 = t0 || t; var k = Math.min(1, (t - t0) / 900); fmt(el, from + (to - from) * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  document.querySelectorAll('[data-count]').forEach(function (el) { var to = +el.getAttribute('data-count') || 0; if (to > 1) tween(el, 0, to); });

  // LIVE: poll the small JSON endpoint and animate whatever changed
  var box = document.querySelector('[data-live-url]');
  if (!box || !window.fetch) return;
  var url = box.getAttribute('data-live-url');
  function num(el) { return +(el.textContent || '0').replace(/\D/g, '') || 0; }
  function poll() {
    if (document.hidden) return;
    fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        document.querySelectorAll('[data-live]').forEach(function (el) {
          var k = el.getAttribute('data-live'), v = d[k];
          if (v === undefined) return;
          if (typeof v !== 'number') { el.textContent = v; return; }
          var old = num(el);
          if (old !== v) { tween(el, old, v); var card = el.closest('.nb,a,.fz-hero'); if (card) { card.classList.remove('bump'); void card.offsetWidth; card.classList.add('bump'); } }
        });
      }).catch(function () {});
  }
  setInterval(poll, 20000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
});
