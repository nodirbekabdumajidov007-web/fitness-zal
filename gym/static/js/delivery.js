/* Cart: pick "pickup" or "courier". For a courier the customer shares a position (the browser's location, or a city from the list) and
   the server answers with the distance, the price and the time (/delivery/quote/). Everything shown here is only a preview: the server
   works the price out again when the order is placed, from the position, never from what this script displays. */
(function () {
  var box = document.getElementById('dlv'), sub = document.getElementById('cart-total'), grand = document.getElementById('grand-total');
  if (!sub || !grand) return;
  var T = box ? box.dataset : {}, unit = T.unit || '';
  var priced = !!(box && T.priced), quote = null, seq = 0, cur = null, timer = 0;
  var dq = document.getElementById('dq'), btn = document.getElementById('dg-detect'), city = document.getElementById('dg-city');
  var latEl = document.getElementById('dg-lat'), lngEl = document.getElementById('dg-lng');

  function money(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  function digits(el) { return +(el.textContent || '').replace(/\D/g, '') || 0; }
  function fill(s, o) { return (s || '').replace(/@(\w+)/g, function (m, k) { return o[k] !== undefined ? o[k] : m; }); }
  function courier() { return !!(box && box.querySelector('input[value=courier]').checked); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }

  /* ---- totals ---- */
  function update() {
    var s = digits(sub), fee = 0, label = box ? T.freeLabel : '';
    if (courier()) {
      if (quote) { fee = quote.fee; label = fee ? money(fee) + ' ' + unit : T.freeLabel; }
      else if (priced) { label = '—'; }
      else { var free = +T.free || 0; fee = free && s >= free ? 0 : (+T.fee || 0); label = fee ? money(fee) + ' ' + unit : T.freeLabel; }
    }
    var feeEl = document.getElementById('dlv-fee');
    if (feeEl) feeEl.textContent = label;
    var old = digits(grand), now = s + fee;
    grand.innerHTML = money(now) + ' <small>' + (unit || grand.querySelector('small') && grand.querySelector('small').textContent || '') + '</small>';
    if (old !== now) { grand.classList.remove('bump'); void grand.offsetWidth; grand.classList.add('bump'); }
  }

  /* ---- the preview card ---- */
  function hint(text, bad) { dq.textContent = ''; dq.appendChild(el('p', bad ? 'dq-err' : 'dq-hint', text)); }

  function render(q) {
    dq.textContent = '';
    if (!q.ok) { dq.appendChild(el('p', 'dq-err', q.error)); return; }
    var card = el('div', 'dq-card' + (q.mode === 'region' ? ' region' : ''));
    var top = el('div', 'dq-top'), pin = el('span', 'dq-pin'), who = el('div', 'dq-who');
    var ico = btn && btn.querySelector('svg'); if (ico) pin.appendChild(ico.cloneNode(true));
    who.appendChild(el('b', '', fill(T.tNear, { place: q.place })));
    var meta = [];
    if (q.priced && q.km !== null) meta.push(fill(T.tKm, { km: String(q.km).replace('.', ',') }));
    if (q.priced) meta.push(q.mode === 'region' ? T.tModeRegion : T.tModeCity);
    if (meta.length) who.appendChild(el('small', '', meta.join(' · ')));
    top.appendChild(pin); top.appendChild(who);
    var map = el('a', 'dq-map', T.tMap); map.href = q.map; map.target = '_blank'; map.rel = 'noopener noreferrer'; top.appendChild(map);
    card.appendChild(top);

    var grid = el('div', 'dq-grid'), c1 = el('div'), c2 = el('div');
    c1.appendChild(el('small', '', T.tFee)); c1.appendChild(el('b', 'num dq-fee' + (q.free ? ' free' : ''), q.fee ? money(q.fee) + ' ' + unit : T.freeLabel));
    grid.appendChild(c1);
    if (q.eta) {
      c2.appendChild(el('small', '', T.tEta));
      c2.appendChild(el('b', 'num', fill(q.eta.kind === 'days' ? T.tEtaDays : T.tEtaMin, { a: q.eta.a, b: q.eta.b })));
      grid.appendChild(c2);
    }
    card.appendChild(grid);

    if (q.free && q.priced) card.appendChild(el('p', 'dq-note good', T.tFreeDone));
    else if (q.left > 0) {
      var s = digits(sub), bar = el('div', 'dq-bar'), fillBar = el('i'); fillBar.style.width = Math.min(100, Math.round(s / (s + q.left) * 100)) + '%';
      bar.appendChild(fillBar); card.appendChild(bar);
      card.appendChild(el('p', 'dq-note', fill(T.tFreeLeft, { n: money(q.left) })));
    }
    if (q.eta && q.eta.delayed && q.eta.kind === 'minutes') card.appendChild(el('p', 'dq-note warn', fill(T.tClosed, { time: q.eta.opens })));
    if (q.mode === 'region' && q.priced) card.appendChild(el('p', 'dq-note', T.tRegionNote));
    if (q.priced) card.appendChild(el('p', 'dq-fine', T.tApprox));
    dq.appendChild(card);
  }

  function ask(params) {
    cur = params; var my = ++seq;
    hint(T.tLoading);
    fetch(T.quoteUrl + '?' + new URLSearchParams(params).toString(), { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (q) { if (my !== seq) return; quote = q.ok ? q : null; render(q); update(); })
      .catch(function () { if (my !== seq) return; quote = null; hint(T.tFail, true); update(); });
  }

  function reset() { seq++; cur = null; quote = null; hint(T.tPick || dq.dataset.pick || ''); update(); }

  /* ---- where the customer is ---- */
  function useCoords(lat, lng) {
    latEl.value = (+lat).toFixed(6); lngEl.value = (+lng).toFixed(6); city.value = '';
    ask({ lat: latEl.value, lng: lngEl.value });
  }
  if (btn) {
    var label = btn.querySelector('span'), idle = label.textContent;
    btn.addEventListener('click', function () {
      if (!navigator.geolocation) { hint(T.tFail, true); return; }
      btn.disabled = true; label.textContent = T.tDetecting;
      navigator.geolocation.getCurrentPosition(function (p) {
        btn.disabled = false; label.textContent = idle; useCoords(p.coords.latitude, p.coords.longitude);
      }, function (e) {
        btn.disabled = false; label.textContent = idle; hint(e && e.code === 1 ? T.tDenied : T.tFail, true);
      }, { enableHighAccuracy: false, timeout: 12000, maximumAge: 120000 });
    });
    city.addEventListener('change', function () {
      latEl.value = ''; lngEl.value = '';
      if (city.value) ask({ place: city.value }); else reset();
    });
    var last = document.getElementById('dg-last');
    if (last) last.addEventListener('click', function () {
      var a = document.getElementById('dlv-a'); if (a && !a.value) a.value = last.dataset.addr || '';
      useCoords(last.dataset.lat, last.dataset.lng);
    });
  }
  if (dq) dq.dataset.pick = dq.textContent.trim();
  T.tPick = dq ? dq.dataset.pick : '';

  if (box) {
    var addr = document.getElementById('dlv-addr');
    box.addEventListener('change', function (ev) {
      if (!ev.target || ev.target.name !== 'delivery') return;
      var isCourier = courier();
      addr.hidden = !isCourier;
      document.getElementById('dlv-a').required = isCourier;
      box.classList.toggle('courier', isCourier);
      if (isCourier) { if (!cur) document.getElementById('dlv-a').focus(); }
      update();
    });
    var form = box.closest('form');
    if (form) form.addEventListener('submit', function (e) {
      if (courier() && priced && !quote) { e.preventDefault(); hint(T.tNeed, true); if (btn) btn.focus(); }
    });
  }
  new MutationObserver(function () {  // the cart's − n + changes the subtotal: the free-delivery threshold may be crossed
    update();
    if (courier() && cur) { clearTimeout(timer); timer = setTimeout(function () { ask(cur); }, 350); }
  }).observe(sub, { childList: true, characterData: true, subtree: true });
  update();
})();
