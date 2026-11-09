/* Front-desk console (admin panel): live member search, member panel with actions, embedded QR scanner, quick registration,
   guest-pass check, "Bugun" work tabs refreshed every 10 seconds without reloading, big entry banner with optional sound.
   Server-rendered HTML is inserted as is (it is escaped there); everything built here uses textContent. */
(function () {
  var FZ = window.FZScan;
  var root = document.getElementById('dk'), classesBody = document.getElementById('dk-classes-body');
  var toasts = document.getElementById('dk-toasts');
  if (!FZ || !toasts) return;

  function $(s, c) { return (c || document).querySelector(s); }
  function $$(s, c) { return [].slice.call((c || document).querySelectorAll(s)); }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }

  function toast(msg, bad, link) {
    var t = el('div', 'dk-toast' + (bad ? ' bad' : ''), msg);
    if (link) { var a = el('a', '', link.text); a.href = link.href; a.target = '_blank'; a.rel = 'noopener'; t.appendChild(a); }
    toasts.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 300); }, bad ? 6500 : 4200);
  }

  function getJSON(url, signal) {
    return fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' }, signal: signal }).then(function (r) {
      if (r.redirected || (r.headers.get('Content-Type') || '').indexOf('application/json') < 0) return { ok: false, status: r.status, d: { error: 'Sessiya tugagan. Sahifani yangilab, qayta kiring.' } };
      return r.json().then(function (d) { return { ok: r.ok && d.ok !== false, status: r.status, d: d }; });
    });
  }

  /* ---------- the big entry banner ---------- */
  var banner = document.getElementById('dk-banner'), bannerTimer = null;
  var ICON_OK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>';
  var ICON_NO = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>';
  var soundBtn = document.getElementById('dk-sound'), soundOn = store('fz-desk-sound') !== '0';
  function paintSound() { if (soundBtn) { soundBtn.setAttribute('aria-pressed', soundOn ? 'true' : 'false'); soundBtn.classList.toggle('off', !soundOn); } }
  paintSound();
  if (soundBtn) soundBtn.addEventListener('click', function () { soundOn = !soundOn; store('fz-desk-sound', soundOn ? '1' : '0'); paintSound(); if (soundOn) FZ.beep(true); });

  function showBanner(b, errText) {
    if (!banner) return;
    var good = !!(b && b.entered);
    banner.hidden = false;
    banner.className = 'dk-banner ' + (good ? 'good' : 'bad');
    banner.querySelector('.dk-banner-ico').innerHTML = good ? ICON_OK : ICON_NO;
    banner.querySelector('[data-b="title"]').textContent = b ? b.title : 'Kirish taqiqlangan';
    banner.querySelector('[data-b="name"]').textContent = b ? (b.name || '') : '';
    var sub = good ? [b.plan, b.until ? ('— ' + b.until + ' gacha') : '', b.note].filter(Boolean).join(' ') : ((b && b.reason_label) || errText || '');
    banner.querySelector('[data-b="sub"]').textContent = sub;
    if (soundOn) FZ.beep(good);
    clearTimeout(bannerTimer);
    bannerTimer = setTimeout(function () { banner.hidden = true; }, 6000);  // resets by itself for the next person in the queue
  }
  if (banner) banner.addEventListener('click', function () { banner.hidden = true; });

  /* ---------- member panel ---------- */
  var box = document.getElementById('dk-member'), urls = root ? JSON.parse(root.dataset.urls) : {}, currentId = null;

  function setMember(id, html) {
    currentId = id; box.innerHTML = html;
    box.classList.add('has');
    if (innerWidth < 1100) box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function openMember(id) {
    box.classList.add('busy');
    getJSON(urls.member.replace('/0/', '/' + id + '/')).then(function (x) {
      box.classList.remove('busy');
      if (!x.ok) { toast(x.d.error || 'A\'zo ochilmadi', true); return; }
      setMember(x.d.id, x.d.html);
      results.hidden = true; input.setAttribute('aria-expanded', 'false');
    });
  }

  function openForm(name, plan) {
    $$('.dk-form', box).forEach(function (f) { f.hidden = f.dataset.form !== name; });
    var f = $('.dk-form[data-form="' + name + '"]', box);
    if (!f) return;
    if (plan) { var s = $('select[name="plan"]', f); if (s) s.value = plan; }
    var h = $('h4', f); if (h && name === 'sell') h.textContent = plan ? 'Uzaytirish' : 'Abonement sotish';
    f.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    var first = $('select,input:not([type=hidden])', f); if (first) first.focus();
  }

  /* one handler for every button that posts to the server (member actions, payments, orders, PT, classes, guests) */
  function post(url, payload) { return FZ.post(url, payload || {}); }
  function done(x, btn) {
    if (!x.ok) { toast(x.d.error || 'Xatolik yuz berdi', true); if (btn) btn.disabled = false; return false; }
    if (x.d.banner) showBanner(x.d.banner);
    else if (x.d.message) toast(x.d.message, false, x.d.receipt ? { text: 'Chekni ochish', href: x.d.receipt } : null);
    if (x.d.html && x.d.id) setMember(x.d.id, x.d.html);
    if (btn && btn.hasAttribute('data-reload-member') && currentId) openMember(currentId);
    if (classesBody) setTimeout(function () { location.reload(); }, 350); else refresh();
    return true;
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act="post"]');
    if (b) {
      e.preventDefault();
      if (b.disabled) return;
      if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
      b.disabled = true;
      post(b.dataset.url).then(function (x) { if (done(x, b) && !x.d.html) b.disabled = false; });
      return;
    }
    var o = e.target.closest('[data-open]');
    if (o) { e.preventDefault(); openForm(o.dataset.open, o.dataset.plan || ''); return; }
    if (e.target.closest('[data-close]')) { $$('.dk-form', box).forEach(function (f) { f.hidden = true; }); return; }
    var m = e.target.closest('[data-open-member]');
    if (m) { e.preventDefault(); openMember(m.dataset.openMember); return; }
    var g = e.target.closest('[data-guest-id]');
    if (g) { g.disabled = true; post(urls.guest, { id: g.dataset.guestId, redeem: true }).then(function (x) { g.disabled = false; guestDone(x); }); }
  });

  function guestDone(x) {
    if (!x.ok) { toast(x.d.error || 'Xatolik', true); return; }
    if (x.d.banner) showBanner(x.d.banner);
    refresh();
  }

  if (box) box.addEventListener('submit', function (e) {
    var f = e.target.closest('.dk-form');
    if (!f) return;
    e.preventDefault();
    var data = {}, btn = $('button[type=submit]', f);
    $$('input,select', f).forEach(function (i) {
      if (i.type === 'radio' && !i.checked) return;
      if (i.type === 'checkbox') { if (i.checked) data[i.name] = true; return; }
      data[i.name] = i.value;
    });
    if (btn) btn.disabled = true;
    post(f.dataset.url, data).then(function (x) { if (btn) btn.disabled = false; done(x, null); });
  });

  /* ---------- search ---------- */
  var input = document.getElementById('dk-q'), results = document.getElementById('dk-results'), guestRes = document.getElementById('dk-guestres');
  var items = [], active = -1, abort = null, timer = null;

  function clearResults() { items = []; active = -1; results.hidden = true; results.textContent = ''; guestRes.hidden = true; guestRes.textContent = ''; input.setAttribute('aria-expanded', 'false'); }

  function paintActive() {
    $$('.dk-res', results).forEach(function (r, i) { r.classList.toggle('on', i === active); r.setAttribute('aria-selected', i === active ? 'true' : 'false'); });
    var a = $$('.dk-res', results)[active]; if (a) a.scrollIntoView({ block: 'nearest' });
  }

  function renderGuest(g) {
    guestRes.textContent = '';
    var c = el('div', 'dk-guestcard ' + g.state);
    c.appendChild(el('b', '', g.guest));
    c.appendChild(el('span', 'dk-sub', 'Taklif qilgan: ' + g.owner + ' (' + g.owner_code + ') · ' + g.date));
    c.appendChild(el('span', 'dk-st ' + g.state, g.label));
    if (g.can) { var bt = el('button', 'dk-btn sm primary', 'Kiritish'); bt.type = 'button'; bt.addEventListener('click', function () { bt.disabled = true; post(urls.guest, { id: g.id, redeem: true }).then(function (x) { guestDone(x); if (x.ok) guestRes.hidden = true; }); }); c.appendChild(bt); }
    guestRes.appendChild(c); guestRes.hidden = false;
  }

  function render(rows) {
    results.textContent = '';
    items = rows; active = rows.length ? 0 : -1;
    if (!rows.length) { var li = el('li', 'dk-res-empty', 'Hech narsa topilmadi'); results.appendChild(li); }
    rows.forEach(function (r, i) {
      var li = el('li', ''); li.setAttribute('role', 'presentation');
      var b = el('button', 'dk-res'); b.type = 'button'; b.setAttribute('role', 'option');
      b.appendChild(el('span', 'dk-ava', r.initials));
      var mid = el('span', 'dk-res-mid'); mid.appendChild(el('b', '', r.name));
      mid.appendChild(el('small', 'num', r.code + (r.phone ? ' · ' + r.phone : '')));
      b.appendChild(mid);
      var right = el('span', 'dk-res-right'); right.appendChild(el('span', 'dk-st ' + r.tone, r.label));
      if (r.plan) right.appendChild(el('small', '', r.plan + (r.days_left !== null && r.status !== 'blocked' ? ' · ' + r.days_left + ' kun' : '')));
      b.appendChild(right);
      b.addEventListener('click', function () { openMember(r.id); });
      b.addEventListener('mousemove', function () { active = i; paintActive(); });
      li.appendChild(b); results.appendChild(li);
    });
    results.hidden = false; input.setAttribute('aria-expanded', 'true'); paintActive();
  }

  function run() {
    var q = input.value.trim();
    if (q.length < 2) { clearResults(); return; }
    if (abort) abort.abort();
    abort = window.AbortController ? new AbortController() : null;
    getJSON(urls.search + '?q=' + encodeURIComponent(q), abort ? abort.signal : undefined).then(function (x) {
      if (!x.ok) { results.textContent = ''; results.appendChild(el('li', 'dk-res-empty', x.d.error || 'Qidiruvda xatolik')); results.hidden = false; return; }
      guestRes.hidden = true;
      if (x.d.guest) { results.hidden = true; renderGuest(x.d.guest); return; }
      render(x.d.results);
      if (x.d.results.length === 1 && /^FZ:/i.test(q)) openMember(x.d.results[0].id);  // a scanned card text opens at once
    }).catch(function () {});
  }

  if (input) {
    input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 180); });
    input.addEventListener('focus', function () { if (items.length) { results.hidden = false; input.setAttribute('aria-expanded', 'true'); } });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (!items.length) return;
        e.preventDefault(); active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length; results.hidden = false; paintActive();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (!results.hidden && items[active]) openMember(items[active].id); else { clearTimeout(timer); run(); }
      } else if (e.key === 'Escape') { input.value = ''; clearResults(); }
    });
    // "/" jumps here (before the admin top bar's own handler, which would take the key)
    window.addEventListener('keydown', function (e) {
      var t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
      if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); e.stopImmediatePropagation(); input.focus(); input.select(); }
    }, true);
    document.addEventListener('click', function (e) { if (!e.target.closest('.dk-find')) { results.hidden = true; input.setAttribute('aria-expanded', 'false'); } });
    if (root.dataset.q) { input.value = root.dataset.q; getJSON(urls.search + '?q=' + encodeURIComponent(root.dataset.q)).then(function (x) {
      if (x.ok && x.d.results) { render(x.d.results); if (x.d.results.length === 1) openMember(x.d.results[0].id); }
    }); }
  }

  /* ---------- embedded scanner ---------- */
  var scanInput = document.getElementById('scan-code'), lastCode = '', lastAt = 0;
  function scanSubmit(code) {
    code = (code || '').trim();
    if (!code || (code === lastCode && Date.now() - lastAt < 4000)) return;
    lastCode = code; lastAt = Date.now();
    post(urls.scan, { code: code }).then(function (x) {
      if (!x.ok) { showBanner(null, x.d.reason_label || x.d.error); toast(x.d.error || 'Kod noto\'g\'ri', true); refresh(); return; }
      showBanner(x.d.banner || { entered: x.d.entered, title: x.d.message, name: x.d.name });
      if (x.d.member_id) openMember(x.d.member_id);
      refresh();
    });
  }
  if (scanInput) {
    scanInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); scanSubmit(scanInput.value); scanInput.value = ''; } });
    FZ.camera({ video: document.getElementById('scan-video'), button: document.getElementById('scan-start'), support: document.getElementById('scan-support'), wrap: document.getElementById('dk-cam'),
      onCode: scanSubmit, unsupported: "Bu brauzerda kamera orqali skanerlash yo'q. Pastdagi maydonga kodni kiriting yoki USB skanerdan foydalaning." });
  }

  /* ---------- side tools: scanner / new member / guest ---------- */
  var tools = $('[data-tools]');
  if (tools) tools.addEventListener('click', function (e) {
    var b = e.target.closest('[data-tool]'); if (!b) return;
    $$('[data-tool]', tools).forEach(function (t) { t.setAttribute('aria-selected', t === b ? 'true' : 'false'); });
    $$('[data-toolpanel]').forEach(function (p) { p.hidden = p.dataset.toolpanel !== b.dataset.tool; });
    var f = $('[data-toolpanel="' + b.dataset.tool + '"] input'); if (f && b.dataset.tool !== 'scan') f.focus();
  });

  var nf = document.getElementById('dk-newform');
  if (nf) {
    var planSel = nf.elements.plan, sale = $('[data-newsale]', nf);
    planSel.addEventListener('change', function () { sale.hidden = !planSel.value; });
    nf.addEventListener('submit', function (e) {
      e.preventDefault();
      $$('[data-err]', nf).forEach(function (x) { x.textContent = ''; });
      var data = { first_name: nf.elements.first_name.value, last_name: nf.elements.last_name.value, phone: nf.elements.phone.value, plan: planSel.value };
      if (planSel.value) { data.method = (nf.querySelector('input[name=method]:checked') || {}).value; if (nf.elements.consent.checked) data.consent = true; }
      var btn = $('button[type=submit]', nf); btn.disabled = true;
      post(urls.newMember, data).then(function (x) {
        btn.disabled = false;
        if (!x.ok) { var t = $('[data-err="' + (x.d.field || '_') + '"]', nf) || $('[data-err="_"]', nf); t.textContent = x.d.error || 'Xatolik'; return; }
        toast(x.d.message, false, x.d.receipt ? { text: 'Chekni ochish', href: x.d.receipt } : null);
        var out = document.getElementById('dk-newres');
        out.innerHTML = x.d.card; out.hidden = false;
        var acts = el('div', 'dk-row');
        var pr = el('a', 'dk-btn primary', 'Kartani chop etish'); pr.href = x.d.card_url; pr.target = '_blank'; pr.rel = 'noopener';
        var dl = el('button', 'dk-btn', 'QR ni yuklab olish'); dl.type = 'button';
        dl.addEventListener('click', function () {
          var svg = $('[data-qr] svg', out); if (!svg) return;
          var a = document.createElement('a'); a.download = 'fitnes-zal-karta.svg';
          a.href = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)], { type: 'image/svg+xml' })); a.click();
        });
        acts.appendChild(pr); acts.appendChild(dl); out.appendChild(acts);
        setMember(x.d.id, x.d.html);
        nf.reset(); sale.hidden = true;
        refresh();
      });
    });
  }

  var gf = document.getElementById('dk-guestform'), gout = document.getElementById('dk-guestout');
  if (gf) gf.addEventListener('submit', function (e) {
    e.preventDefault();
    var code = gf.elements.code.value.trim(); if (!code) return;
    post(urls.guest, { code: code }).then(function (x) {
      gout.textContent = ''; gout.hidden = false;
      if (!x.ok) { gout.appendChild(el('p', 'dk-err', x.d.error || 'Xatolik')); return; }
      var g = x.d.guest, c = el('div', 'dk-guestcard ' + g.state);
      c.appendChild(el('b', '', g.guest)); c.appendChild(el('span', 'dk-sub', 'Taklif qilgan: ' + g.owner + ' (' + g.owner_code + ') · ' + g.date));
      c.appendChild(el('span', 'dk-st ' + g.state, g.label));
      if (g.can) { var bt = el('button', 'dk-btn sm primary', 'Kiritish'); bt.type = 'button'; bt.addEventListener('click', function () { bt.disabled = true; post(urls.guest, { id: g.id, redeem: true }).then(function (y) { guestDone(y); gout.hidden = true; gf.reset(); }); }); c.appendChild(bt); }
      gout.appendChild(c);
    });
  });

  /* ---------- "Bugun" tabs + polling ---------- */
  var tabs = $('[data-tabs]');
  function pick(name) {
    $$('[data-tab]', tabs).forEach(function (b) { b.setAttribute('aria-selected', b.dataset.tab === name ? 'true' : 'false'); });
    $$('[data-panel]').forEach(function (p) { p.hidden = p.dataset.panel !== name; });
    store('fz-desk-tab', name);
    var on = $('[aria-selected="true"]', tabs);
    if (on && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = on.offsetLeft - (tabs.clientWidth - on.offsetWidth) / 2;
  }
  if (tabs) {
    tabs.addEventListener('click', function (e) { var b = e.target.closest('[data-tab]'); if (b) pick(b.dataset.tab); });
    $$('[data-goto]').forEach(function (k) { k.addEventListener('click', function () { pick(k.dataset.goto); document.getElementById('dk-today').scrollIntoView({ behavior: 'smooth', block: 'start' }); }); });
    var saved = store('fz-desk-tab'), hot = $$('[data-tab]', tabs).filter(function (b) { return ['pay', 'orders', 'pt'].indexOf(b.dataset.tab) >= 0 && parseInt($('.dk-n', b).textContent, 10) > 0; })[0];
    pick(hot ? hot.dataset.tab : (saved && $('[data-tab="' + saved + '"]', tabs) ? saved : 'visits'));
  }

  var busy = false;
  function refresh() {
    if (!root || busy) return;
    busy = true;
    getJSON(urls.today).then(function (x) {
      busy = false;
      if (!x.ok) { if (x.status === 0 || !x.d.counts) { var s = document.getElementById('dk-stamp'); if (s) s.textContent = 'Aloqa yo\'q'; } return; }
      var d = x.d;
      Object.keys(d.counts).forEach(function (k) {
        var c = $('[data-tabcount="' + k + '"]'); if (c) { c.textContent = d.counts[k]; c.classList.toggle('hot', d.counts[k] > 0 && ['pay', 'orders', 'pt'].indexOf(k) >= 0); }
        var kp = $('[data-count="' + k + '"]'); if (kp) { kp.textContent = d.counts[k]; var card = kp.closest('.dk-kpi'); if (card && ['pay', 'orders'].indexOf(k) >= 0) card.classList.toggle('hot', d.counts[k] > 0); }
      });
      Object.keys(d.tabs).forEach(function (k) {
        var p = $('[data-panel="' + k + '"]'); if (p && p.dataset.hash !== d.tabs[k].hash) { p.innerHTML = d.tabs[k].html; p.dataset.hash = d.tabs[k].hash; }
      });
      var sh = document.getElementById('dk-shift'); if (sh) sh.innerHTML = d.shift;
      var n = $('[data-crowd-n]'); if (n && d.crowd) n.textContent = d.crowd.n;
      var cw = $('[data-crowd]'); if (cw && d.crowd) { cw.className = 'dk-kpi crowd ' + d.crowd.level; var bar = $('u', cw); if (bar) bar.style.width = d.crowd.pct + '%'; }
      var st = document.getElementById('dk-stamp'); if (st) st.textContent = 'Yangilandi ' + d.stamp;
    }).catch(function () { busy = false; });
  }
  if (root) {
    setInterval(function () { if (!document.hidden) refresh(); }, 10000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
    var clock = $('[data-clock]');
    if (clock) setInterval(function () { var d = new Date(); clock.textContent = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }, 10000);
    var stamp = document.getElementById('dk-stamp'); if (stamp) stamp.textContent = 'Yangilanish: har 10 soniyada';
  }
  var bx = $('[data-banner-close]'); if (bx) bx.addEventListener('click', function (e) { e.stopPropagation(); banner.hidden = true; });
})();
