/* Messenger: live over WebSocket (falls back to polling every 3 s), photos, read ticks, typing, presence, day separators, grouped bubbles.
   Everything a member typed is inserted with textContent, never as HTML. */
(function () {
  var log = document.getElementById('chat-log');
  if (!log) return;
  var d = log.dataset;
  var form = document.getElementById('chat-form'), body = document.getElementById('chat-body'), err = document.getElementById('chat-err');
  var file = document.getElementById('chat-file'), preview = document.getElementById('chat-preview'), drop = document.getElementById('chat-drop');
  var statusEl = document.getElementById('m-status'), lightbox = document.getElementById('chat-lightbox');
  var last = parseInt(d.last || '0', 10), busy = false, sending = false, picked = null;
  var direct = d.kind === 'direct';

  function csrf() { return (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || ''; }
  function post(url, data) {
    var opts = { method: 'POST', credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': csrf() } };
    if (data instanceof FormData) opts.body = data;
    else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(data || {}); }
    return fetch(url, opts).then(function (r) { return r.json().then(function (j) { j._ok = r.ok; return j; }, function () { return { _ok: false }; }); });
  }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function nearBottom() { return log.scrollHeight - log.scrollTop - log.clientHeight < 120; }
  function toBottom() { log.scrollTop = log.scrollHeight; }

  function dayLabel(iso) {
    var t = new Date(), y = new Date(Date.now() - 864e5);
    var f = function (x) { return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0'); };
    if (iso === f(t)) return d.tToday;
    if (iso === f(y)) return d.tYesterday;
    var p = iso.split('-'); return p[2] + '.' + p[1] + '.' + p[0];
  }
  function lastRow() { var rows = log.querySelectorAll('.m-row'); return rows.length ? rows[rows.length - 1] : null; }

  function markDeleted(row) {
    var b = row.querySelector('.m-bubble');
    b.querySelectorAll('.m-photo,.m-text,.m-acts,.m-tick').forEach(function (x) { x.remove(); });
    if (!b.querySelector('.m-del')) b.insertBefore(el('i', 'm-del', d.tDeleted), b.querySelector('.m-meta'));
    b.classList.remove('photo-only');
  }

  function act(label, onClick) { var b = el('button', 'link', label); b.type = 'button'; b.addEventListener('click', onClick); return b; }

  function render(m) {
    if (log.querySelector('.m-row[data-id="' + m.id + '"]')) return;
    var empty = document.getElementById('chat-empty'); if (empty) empty.remove();
    var prev = lastRow(), newDay = !prev || prev.dataset.day !== m.day;
    if (newDay) { var sep = el('div', 'm-day'); sep.dataset.day = m.day; sep.appendChild(el('span', '', dayLabel(m.day))); log.appendChild(sep); }
    var first = newDay || !prev || prev.dataset.sender !== String(m.sender);
    var row = el('div', 'm-row' + (m.mine ? ' mine' : '') + (first ? ' first' : ''));
    row.dataset.id = m.id; row.dataset.sender = m.sender; row.dataset.day = m.day;
    if (!direct && !m.mine) { var av = el('span', 'm-ava', first ? m.initials : ''); av.style.setProperty('--h', m.hue); row.appendChild(av); }
    var b = el('div', 'm-bubble' + (m.image && !m.body ? ' photo-only' : ''));
    if (!direct && !m.mine && first) { var nm = el('div', 'm-name', m.name); nm.style.setProperty('--h', m.hue); b.appendChild(nm); }
    if (m.deleted) b.appendChild(el('i', 'm-del', d.tDeleted));
    else {
      if (m.image) { var a = el('a', 'm-photo'); a.href = m.image; a.target = '_blank'; a.rel = 'noopener'; a.setAttribute('data-lightbox', ''); var im = el('img'); im.src = m.image; im.alt = ''; im.addEventListener('load', function () { if (stick) toBottom(); }); a.appendChild(im); b.appendChild(a); }
      if (m.body) b.appendChild(el('div', 'm-text', m.body));
    }
    var meta = el('div', 'm-meta'); meta.appendChild(el('span', 'num', m.time));
    if (m.mine && direct && !m.deleted) meta.appendChild(el('span', 'm-tick' + (m.read ? ' read' : ''), m.read ? '✓✓' : '✓'));
    b.appendChild(meta);
    if (m.can_delete || m.can_report) {
      var acts = el('div', 'm-acts');
      if (m.can_delete) acts.appendChild(act(d.tDelete, function (e) {
        var btn = e.target;
        if (!btn.classList.contains('armed')) { btn.classList.add('armed'); btn.textContent = d.tSure; return; }
        post(d.delete.replace('/0/', '/' + m.id + '/')).then(function (j) { if (j._ok) markDeleted(row); });
      }));
      if (m.can_report) acts.appendChild(act(d.tReport, function (e) {
        post(d.report.replace('/0/', '/' + m.id + '/')).then(function (j) { if (j._ok) e.target.textContent = d.tReported; });
      }));
      b.appendChild(acts);
    }
    row.appendChild(b);
    var stick = nearBottom() || m.mine;
    log.appendChild(row);
    if (stick) toBottom();
    if (m.id > last) last = m.id;
  }

  function applyReads(upto) {
    if (!direct || !upto) return;
    log.querySelectorAll('.m-row.mine .m-tick:not(.read)').forEach(function (t) {
      if (parseInt(t.closest('.m-row').dataset.id, 10) <= upto) { t.classList.add('read'); t.textContent = '✓✓'; }
    });
  }
  function applyPresence(p) {
    if (!statusEl || !p) return;
    statusEl.classList.toggle('on', !!p.online);
    if (p.online) statusEl.textContent = d.tOnline;
    else if (p.seen) statusEl.textContent = d.tSeen.replace('@', p.seen);
    var dot = document.querySelector('.m-head .m-dot');
    if (p.online && !dot) { var a = document.querySelector('.m-head .m-ava'); if (a) a.appendChild(el('i', 'm-dot')); }
    if (!p.online && dot) dot.remove();
  }

  function poll() {
    if (busy || document.hidden) return;
    busy = true;
    fetch(d.poll + '?after=' + last, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        j.messages.forEach(render);
        applyReads(j.read_upto);
        applyPresence(j.presence);
        (j.deleted || []).forEach(function (id) { var row = log.querySelector('.m-row[data-id="' + id + '"]'); if (row && !row.querySelector('.m-del')) markDeleted(row); });
      })
      .catch(function () {})
      .then(function () { busy = false; });
  }

  // ---- composer: photo pick / paste / drop, preview, auto-grow, Enter to send
  function setPicked(f) {
    if (f && !/^image\/(jpeg|png|webp)$/.test(f.type)) { err.textContent = form.dataset.badImage || ''; return; }
    picked = f || null;
    if (!preview) return;
    if (picked) { preview.querySelector('img').src = URL.createObjectURL(picked); preview.hidden = false; }
    else { preview.hidden = true; preview.querySelector('img').removeAttribute('src'); if (file) file.value = ''; }
  }
  function grow() { body.style.height = 'auto'; body.style.height = Math.min(body.scrollHeight, 160) + 'px'; }

  if (form) {
    form.dataset.badImage = d.tBadImage || '';
    if (file) file.addEventListener('change', function () { setPicked(file.files[0]); });
    var x = document.getElementById('chat-preview-x'); if (x) x.addEventListener('click', function () { setPicked(null); });
    body.addEventListener('input', grow);
    body.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
    body.addEventListener('paste', function (e) {
      var item = [].slice.call((e.clipboardData || {}).items || []).find(function (i) { return i.type.indexOf('image/') === 0; });
      if (item) { e.preventDefault(); setPicked(item.getAsFile()); }
    });
    var section = form.closest('.messenger');
    ['dragenter', 'dragover'].forEach(function (t) { section.addEventListener(t, function (e) { if ([].slice.call(e.dataTransfer.types).indexOf('Files') > -1) { e.preventDefault(); drop.hidden = false; } }); });
    ['dragleave', 'drop'].forEach(function (t) { section.addEventListener(t, function (e) { if (t === 'drop' || e.target === drop) drop.hidden = true; }); });
    section.addEventListener('drop', function (e) { e.preventDefault(); if (e.dataTransfer.files[0]) setPicked(e.dataTransfer.files[0]); });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = body.value;
      if (sending || (!text.trim() && !picked)) return;
      err.textContent = '';
      var fd = new FormData(); fd.append('body', text); if (picked) fd.append('image', picked, picked.name || 'photo.png');
      sending = true; form.classList.add('sending');
      post(d.send, fd).then(function (j) {
        if (j._ok) { render(j.message); body.value = ''; grow(); setPicked(null); toBottom(); }
        else err.textContent = j.error || '!';
      }).catch(function () { err.textContent = '!'; }).then(function () { sending = false; form.classList.remove('sending'); body.focus(); });
    });
  }

  // ---- photo lightbox
  log.addEventListener('click', function (e) {
    var a = e.target.closest('[data-lightbox]');
    if (!a || !lightbox) return;
    e.preventDefault();
    lightbox.querySelector('img').src = a.getAttribute('href');
    lightbox.hidden = false;
  });
  if (lightbox) lightbox.addEventListener('click', function () { lightbox.hidden = true; });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && lightbox) lightbox.hidden = true; });

  log.querySelectorAll('.m-photo img').forEach(function (im) { im.addEventListener('load', function () { if (nearBottom()) toBottom(); }); });
  toBottom();

  // ---- live channel: WebSocket when the server offers it, polling every 3 s otherwise (and as a safety net every 30 s)
  var ws = null, wsOk = false, retry = 1000, typingTimer = null, lastTypingSent = 0;
  var typingBox = document.getElementById('chat-typing'), typingText = document.getElementById('chat-typing-text'), liveBadge = document.getElementById('chat-live');
  function wsSend(o) { if (wsOk) try { ws.send(JSON.stringify(o)); } catch (e) {} }
  function showTyping(name) {
    if (!typingBox) return;
    typingText.textContent = d.tTyping.replace('@', name);
    typingBox.hidden = false;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(function () { typingBox.hidden = true; }, 3500);
  }
  function connect() {
    if (!d.ws || !window.WebSocket) return;
    try { ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + d.ws); } catch (e) { return; }
    ws.onopen = function () { wsOk = true; retry = 1000; if (liveBadge) liveBadge.hidden = false; poll(); };
    ws.onmessage = function (e) {
      var j; try { j = JSON.parse(e.data); } catch (x) { return; }
      if (j.t === 'msg') {
        render(j.m);
        if (typingBox) typingBox.hidden = true;
        if (!j.m.mine && !document.hidden) wsSend({ t: 'read', upto: j.m.id });
      } else if (j.t === 'read') applyReads(j.upto);
      else if (j.t === 'typing') showTyping(j.name);
      else if (j.t === 'presence') applyPresence(j);
      else if (j.t === 'deleted') { var row = log.querySelector('.m-row[data-id="' + j.id + '"]'); if (row && !row.querySelector('.m-del')) markDeleted(row); }
    };
    ws.onclose = function (e) {
      wsOk = false; if (liveBadge) liveBadge.hidden = true;
      if (e.code === 4403 || e.code === 4404) return;  // not allowed here: stay on polling
      setTimeout(connect, retry); retry = Math.min(retry * 2, 30000);
    };
  }
  if (body) body.addEventListener('input', function () {
    var now = Date.now();
    if (now - lastTypingSent > 2000) { lastTypingSent = now; wsSend({ t: 'typing' }); }
  });
  setInterval(function () { if (!wsOk) poll(); }, 3000);
  setInterval(function () { if (wsOk) { wsSend({ t: 'ping' }); poll(); } }, 30000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { poll(); var lr = lastRow(); if (lr) wsSend({ t: 'read', upto: +lr.dataset.id }); } });
  connect();
})();
