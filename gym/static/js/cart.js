/* Shop: "+ Add" turns into − n +, instantly (no page reload), with a little celebration: the picture flies to the cart,
   the badge bounces, a toast appears and the floating cart bar updates. The forms still work without JavaScript. */
(function () {
  if (!document.querySelector('.qty-ctl')) return;
  var t = (document.getElementById('cart-i18n') || { dataset: {} }).dataset;
  var badge = document.getElementById('cart-badge'), bar = document.getElementById('cart-bar'), toastEl = document.getElementById('cart-toast');
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var toastTimer;

  function csrf() { return (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || ''; }
  function money(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }

  function toast(text, ok) {
    if (!toastEl) return;
    toastEl.textContent = '';
    var i = document.createElement('span'); i.className = 'ct-ico'; i.textContent = ok ? '✓' : '!';
    var s = document.createElement('span'); s.textContent = text;
    toastEl.appendChild(i); toastEl.appendChild(s);
    toastEl.className = 'cart-toast' + (ok ? '' : ' bad');
    toastEl.hidden = false;
    void toastEl.offsetWidth; toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); setTimeout(function () { toastEl.hidden = true; }, 300); }, 1800);
  }

  function bump(el) { if (!el || reduce) return; el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); }

  function fly(ctl) {
    if (reduce || !badge) return;
    var card = ctl.closest('.prod, .prod-buy, .cart-line, .grid');
    var img = card && (card.querySelector('.prod-img img, .cl-img img') || document.querySelector('.prod-hero img'));
    if (!img) return;
    var a = img.getBoundingClientRect(), target = (badge.hidden ? badge.parentElement : badge).getBoundingClientRect();
    var c = img.cloneNode(); c.className = 'fly-img'; c.removeAttribute('loading');
    c.style.left = a.left + 'px'; c.style.top = a.top + 'px'; c.style.width = a.width + 'px'; c.style.height = a.height + 'px';
    document.body.appendChild(c);
    requestAnimationFrame(function () {
      var dx = target.left + target.width / 2 - (a.left + a.width / 2), dy = target.top + target.height / 2 - (a.top + a.height / 2);
      c.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(.12) rotate(18deg)';
      c.style.opacity = '.4';
    });
    setTimeout(function () { c.remove(); bump(badge); }, 650);
  }

  function setCtl(ctl, qty, max) {
    ctl.dataset.qty = qty;
    if (max != null) ctl.dataset.max = max;
    var add = ctl.querySelector('.qc-add'), step = ctl.querySelector('.qc-step');
    add.hidden = qty > 0; step.hidden = qty < 1;
    ctl.querySelector('.qc-n').textContent = qty;
    ctl.querySelector('.qc-minus-val').value = qty - 1;
    ctl.querySelector('.qc-plus-val').value = qty + 1;
    ctl.querySelector('.qc-plus').disabled = qty >= parseInt(ctl.dataset.max || '0', 10);
    bump(ctl.querySelector('.qc-n'));
  }

  function setTotals(j) {
    if (badge) { badge.textContent = j.count; badge.hidden = j.count < 1; }
    if (bar) {
      bar.hidden = j.count < 1;
      var items = document.getElementById('cb-items'), total = document.getElementById('cb-total');
      if (items) items.textContent = (bar.dataset.tItems || '@').replace('@', j.count);
      if (total) total.textContent = money(j.total) + ' ' + (bar.dataset.unit || '');
      if (j.count > 0) bump(bar);
    }
    // cart page: line subtotal, grand total, empty state
    var line = document.querySelector('[data-line="' + j.pid + '"]');
    if (line) line.textContent = money(j.line);
    var gt = document.getElementById('cart-total');
    if (gt) gt.textContent = money(j.total) + ' ' + (t.unit || '');
    if (j.qty < 1) {
      var row = document.querySelector('.cart-line[data-pid="' + j.pid + '"]');
      if (row) { row.classList.add('leaving'); setTimeout(function () { row.remove(); }, reduce ? 0 : 280); }
    }
    if (j.count < 1 && document.getElementById('cart-page')) {
      document.getElementById('cart-page').hidden = true;
      document.getElementById('cart-empty').hidden = false;
    }
    document.querySelectorAll('.qty-ctl[data-pid="' + j.pid + '"]').forEach(function (c) { setCtl(c, j.qty, j.max); });
  }

  document.addEventListener('submit', function (e) {
    var form = e.target, ctl = form.closest('.qty-ctl');
    if (!ctl) return;
    e.preventDefault();
    if (ctl.classList.contains('busy')) return;
    var before = parseInt(ctl.dataset.qty || '0', 10);
    ctl.classList.add('busy');
    fetch(form.action, { method: 'POST', credentials: 'same-origin', body: new FormData(form),
                         headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': csrf() } })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        setTotals(j);
        if (!j.ok) { toast(j.error, false); return; }
        if (j.qty > before) { fly(ctl); toast(t.added || '✓', true); if (navigator.vibrate) navigator.vibrate(12); }
        else if (j.qty < before && j.qty === 0) toast(t.removed || '', true);
      })
      .catch(function () { form.submit(); })  // network trouble: fall back to the normal form post
      .then(function () { ctl.classList.remove('busy'); });
  });
})();
