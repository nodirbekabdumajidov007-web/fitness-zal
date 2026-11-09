/* AI yordamchi: the slide-over chat. Everything the server sends is put into the page with textContent (never as HTML). */
(function () {
  'use strict';
  var panel = document.getElementById('fz-ai');
  if (!panel) return;
  var fab = document.getElementById('fz-ai-fab');
  var scrim = document.querySelector('.fz-ai-scrim');
  var log = panel.querySelector('.fz-ai-log');
  var chipsBox = panel.querySelector('.fz-ai-chips');
  var form = panel.querySelector('form');
  var input = form.elements.q;
  var send = panel.querySelector('.fz-ai-send');
  var url = panel.dataset.ask;
  var opener = null, loaded = false, busy = false;
  var DEFAULT_CHIPS = ["Bugun tushum qancha?", "Bu oy yangi a'zolar", "Bu hafta kim tugaydi?", "14 kundan beri kelmaganlar", "Eng ko'p sotilgan mahsulotlar", "Kutilayotgan to'lovlar"];

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function token() { var t = form.querySelector('[name=csrfmiddlewaretoken]'); return t ? t.value : ''; }
  function scroll() { log.scrollTop = log.scrollHeight; }

  function chips(list) {
    chipsBox.textContent = '';
    (list && list.length ? list : DEFAULT_CHIPS).slice(0, 8).forEach(function (q) {
      var b = h('button', '', q); b.type = 'button';
      b.addEventListener('click', function () { ask(q); });
      chipsBox.appendChild(b);
    });
  }

  function bubbleMe(text) { var m = h('div', 'fz-ai-msg me', text); log.appendChild(m); scroll(); }

  function bubbleBot(a) {
    var m = h('div', 'fz-ai-msg bot');
    m.appendChild(h('p', '', a.text));
    if (a.chart && a.chart.items && a.chart.items.length) {
      var top = Math.max.apply(null, a.chart.items.map(function (i) { return i.value; }).concat([1]));
      var box = h('div', 'fz-ai-bars');
      a.chart.items.slice(0, 12).forEach(function (it) {
        var row = h('div', 'fz-ai-bar'), l = h('div');
        l.appendChild(h('span', '', it.label)); l.appendChild(h('b', '', it.text));
        var bar = h('i'); bar.style.setProperty('--w', Math.max(2, Math.round(it.value / top * 100)) + '%');
        row.appendChild(l); row.appendChild(bar); box.appendChild(row);
      });
      m.appendChild(box);
    }
    if (a.table && a.table.rows && a.table.rows.length) {
      var wrap = h('div', 'fz-ai-tbl'), t = h('table'), hd = h('tr');
      a.table.cols.forEach(function (c) { hd.appendChild(h('th', '', c)); });
      t.appendChild(hd);
      a.table.rows.forEach(function (r) { var tr = h('tr'); r.forEach(function (c) { tr.appendChild(h('td', '', c)); }); t.appendChild(tr); });
      wrap.appendChild(t); m.appendChild(wrap);
    }
    if (a.links && a.links.length) {
      var ls = h('div', 'fz-ai-links');
      a.links.forEach(function (l) { if (typeof l.url === 'string' && l.url.charAt(0) === '/') { var x = h('a', '', l.label); x.href = l.url; ls.appendChild(x); } });
      m.appendChild(ls);
    }
    log.appendChild(m); scroll();
  }

  function typing() { var m = h('div', 'fz-ai-msg bot'), d = h('span', 'fz-ai-typing'); d.setAttribute('aria-label', 'Yozmoqda'); d.innerHTML = '<i></i><i></i><i></i>'; m.appendChild(d); log.appendChild(m); scroll(); return m; }

  function ask(q) {
    q = (q || '').trim();
    if (!q || busy) return;
    busy = true; send.disabled = true; input.value = '';
    bubbleMe(q);
    var t = typing();
    fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token(), 'X-Requested-With': 'fetch' }, body: JSON.stringify({ q: q }) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'Server javobi tushunarsiz.' }; }); })
      .then(function (a) {
        t.remove();
        if (a.ok === false) { var m = h('div', 'fz-ai-msg bot'); m.appendChild(h('p', 'fz-ai-err', a.error || 'Xatolik yuz berdi.')); log.appendChild(m); scroll(); return; }
        bubbleBot(a); chips(a.suggestions);
      })
      .catch(function () { t.remove(); var m = h('div', 'fz-ai-msg bot'); m.appendChild(h('p', 'fz-ai-err', "Aloqa yo'q. Internetni tekshirib qayta urinib ko'ring.")); log.appendChild(m); scroll(); })
      .then(function () { busy = false; send.disabled = false; input.focus(); });
  }

  function load() {
    if (loaded) return; loaded = true;
    bubbleBot({ text: "Salom! Zal ma'lumotlari haqida o'zbekcha, ruscha yoki inglizcha so'rang: tushum, a'zolar, tashriflar, mahsulotlar, abonementlar." });
    chips();
    fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) return;
      if (d.history && d.history.length) {
        log.textContent = '';
        d.history.forEach(function (m) { if (m.role === 'user') bubbleMe(m.text); else if (m.answer) bubbleBot(m.answer); });
        var lastBot = d.history.filter(function (m) { return m.role === 'bot'; }).pop();
        chips(lastBot && lastBot.answer ? lastBot.answer.suggestions : d.suggestions);
      } else { chips(d.suggestions); }
    }).catch(function () {});
  }

  function open(from) {
    opener = from || document.activeElement;
    panel.classList.add('open'); panel.setAttribute('aria-hidden', 'false'); scrim.hidden = false; fab.classList.add('hide');
    load();
    setTimeout(function () { input.focus(); }, 60);
  }
  function close() {
    panel.classList.remove('open'); panel.setAttribute('aria-hidden', 'true'); scrim.hidden = true; fab.classList.remove('hide');
    if (opener && opener.focus) opener.focus();
  }

  document.addEventListener('click', function (e) {
    var o = e.target.closest('[data-fz-ai-open]'); if (o) { e.preventDefault(); open(o); return; }
    if (e.target.closest('[data-fz-ai-close]')) { close(); return; }
    if (e.target.closest('[data-fz-ai-clear]')) {
      fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token() }, body: JSON.stringify({ clear: true }) }).catch(function () {});
      log.textContent = ''; loaded = false; load();
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('open')) { e.preventDefault(); close(); }
    if (e.key === 'Tab' && panel.classList.contains('open')) {  // keep Tab inside the open panel
      var f = [].slice.call(panel.querySelectorAll('button,input,a[href]')).filter(function (x) { return x.offsetParent !== null && !x.disabled; });
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); ask(input.value); });
  window.fzAI = { open: open, close: close, ask: ask };
})();
