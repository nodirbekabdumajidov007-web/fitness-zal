/* /yordam/: the same support conversation as the floating widget, on a full page. It talks to the same endpoints (the signed-in member's own
   thread, or the guest thread named by the fz_support cookie), so what is written here shows up in the widget and the other way round.
   Server text is always put in with textContent. Polls every ~6 s while the tab is visible (new replies + "seen" marks). */
(function () {
  'use strict';
  var root = document.getElementById('hc'), cfgEl = document.getElementById('sw-config');
  if (!root || !cfgEl) return;
  var C;
  try { C = JSON.parse(cfgEl.textContent); } catch (e) { return; }
  var T = function (k) { return (C.t && C.t[k.replace(/_/g, '-')]) || ''; };
  var $ = function (id) { return document.getElementById(id); };
  var POLL_MS = 6000, HIDDEN_MS = 60000;
  var list = $('sw-list'), text = $('sw-text'), form = $('sw-form'), errBox = $('sw-err'), contact = $('sw-contact'), fileIn = $('sw-file'), chip = $('sw-chip');
  var state = { lastId: 0, thread: null, sending: false, photo: null, timer: null, polling: false, readUpto: 0, stick: true };

  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function csrf() { var i = root.querySelector('[name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  function clock(iso) { var d = new Date(iso); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function api(url, opts) {
    opts = opts || {};
    var h = { 'X-Requested-With': 'fetch' };
    if (opts.method === 'POST') h['X-CSRFToken'] = csrf();
    if (opts.json) { h['Content-Type'] = 'application/json'; opts.body = JSON.stringify(opts.json); }
    return fetch(url, { method: opts.method || 'GET', body: opts.body, headers: h, credentials: 'same-origin' })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: T('sw_err_net') }; }); })
      .catch(function () { return { ok: false, error: T('sw_err_net') }; });
  }
  function avatar(src, initials) {
    var a = el('span', 'sw-ava sw-ava-s');
    if (src) { var i = el('img'); i.src = src; i.alt = ''; i.loading = 'lazy'; i.onerror = function () { a.textContent = initials || ''; i.remove(); }; a.appendChild(i); }
    else a.textContent = initials || '';
    return a;
  }
  function showErr(msg) { errBox.textContent = msg || ''; errBox.hidden = !msg; }
  function nearBottom() { return list.scrollHeight - list.scrollTop - list.clientHeight < 120; }
  function toBottom() { list.scrollTop = list.scrollHeight; }

  function bubble(m) {
    var row = el('div', 'sw-b hc-b ' + (m.staff ? 'staff' : 'mine'));
    row.setAttribute('data-id', m.id);
    if (m.staff) row.appendChild(avatar(m.avatar, m.initials));
    var box = el('div', 'sw-b-box');
    if (m.staff) box.appendChild(el('small', 'sw-b-name', m.name));
    if (m.image) {
      var a = el('a', 'sw-b-img'); a.href = m.image; a.target = '_blank'; a.rel = 'noopener noreferrer';
      var im = el('img'); im.src = m.image; im.alt = T('sw_photo'); im.loading = 'lazy'; im.addEventListener('load', function () { if (state.stick) toBottom(); });
      a.appendChild(im); box.appendChild(a);
    }
    if (m.text) box.appendChild(el('p', null, m.text));
    box.appendChild(el('small', 'sw-b-time', clock(m.at) + (!m.staff && m.read ? ' · ' + T('sw_seen') : '')));
    if (!m.staff && m.read) row.classList.add('seen');
    row.appendChild(box);
    return row;
  }
  function appendMessages(msgs) {
    if (!msgs.length) return;
    state.stick = nearBottom();
    var empty = list.querySelector('.sw-empty'); if (empty) empty.remove();
    msgs.forEach(function (m) {
      if (list.querySelector('[data-id="' + m.id + '"]')) return;
      list.appendChild(bubble(m));
      state.lastId = Math.max(state.lastId, m.id);
    });
    if (state.stick) toBottom();
  }
  function markSeen(upto) {  // read receipts: older "mine" bubbles get their "Seen" mark when staff open them
    state.readUpto = Math.max(state.readUpto, upto);
    list.querySelectorAll('.sw-b.mine:not(.seen)').forEach(function (row) {
      if (parseInt(row.getAttribute('data-id'), 10) > state.readUpto) return;
      row.classList.add('seen');
      var tm = row.querySelector('.sw-b-time');
      if (tm) tm.textContent += ' · ' + T('sw_seen');
    });
  }
  function paintThread(t) {
    state.thread = t;
    contact.hidden = !!(C.auth || t);
    $('sw-closed').hidden = !(t && t.status === 'closed');
    var st = $('sw-status');
    st.textContent = t ? T('sw_status_' + t.status) : '';
    st.hidden = !t;
  }
  function clearBadge() {
    document.querySelectorAll('[data-support-badge]').forEach(function (b) { b.hidden = true; });
  }
  function markRead() { api(C.urls.read, { method: 'POST' }).then(clearBadge); }

  function load() {
    return api(C.urls.thread).then(function (d) {
      if (!d.ok) { showErr(d.error); return; }
      clear(list);
      state.lastId = 0;
      paintThread(d.thread);
      if (!d.messages.length) list.appendChild(el('p', 'sw-empty', T('sw_empty_thread') + (C.auth ? '' : ' ' + T('sw_guest_intro'))));
      state.stick = true;
      appendMessages(d.messages);
      toBottom();
      if (d.read_upto) markSeen(d.read_upto);
      if (d.unread) markRead();
    });
  }
  function poll() {
    if (state.polling || document.hidden) return Promise.resolve();
    state.polling = true;
    return api(C.urls.thread + '?after=' + state.lastId).then(function (d) {
      state.polling = false;
      if (!d.ok) return;
      if (d.thread) paintThread(d.thread);
      if (d.messages && d.messages.length) appendMessages(d.messages);
      if (d.read_upto) markSeen(d.read_upto);
      if (d.unread) markRead();
    });
  }
  function schedule() {
    clearTimeout(state.timer);
    state.timer = setTimeout(function () { poll().then(schedule); }, document.hidden ? HIDDEN_MS : POLL_MS);
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { poll(); schedule(); } });

  function grow() { text.style.height = 'auto'; text.style.height = Math.min(text.scrollHeight, 140) + 'px'; }
  text.addEventListener('input', grow);
  text.addEventListener('keydown', function (e) {
    var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    if (e.key === 'Enter' && !e.shiftKey && !coarse && !e.isComposing) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { cancelable: true })); }
  });
  $('sw-attach').addEventListener('click', function () { fileIn.click(); });
  function clearPhoto() { state.photo = null; fileIn.value = ''; chip.hidden = true; clear(chip); }
  fileIn.addEventListener('change', function () {
    var f = fileIn.files && fileIn.files[0];
    clearPhoto();
    if (!f) return;
    state.photo = f;
    var im = el('img'); im.alt = ''; try { im.src = URL.createObjectURL(f); } catch (e) {}
    chip.appendChild(im);
    chip.appendChild(el('span', null, f.name));
    var x = el('button', 'sw-chip-x'); x.type = 'button'; x.setAttribute('aria-label', T('sw_remove_photo')); x.textContent = '×';
    x.addEventListener('click', clearPhoto);
    chip.appendChild(x);
    chip.hidden = false;
  });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (state.sending) return;
    var v = text.value.trim();
    showErr('');
    if (!v && !state.photo) { showErr(T('sw_err_empty')); return; }
    if (v.length > C.max) { showErr(T('sw_err_long')); return; }
    var fd = new FormData();
    fd.append('text', v);
    if (state.photo) fd.append('image', state.photo);
    if (!C.auth && !state.thread) {
      var nm = $('sw-name').value.trim(), ph = $('sw-phone').value.trim();
      if (nm.length < 2 || ph.replace(/\D/g, '').length < 9) { showErr(T('sw_err_contact')); return; }
      fd.append('name', nm); fd.append('phone', ph); fd.append('email', $('sw-email').value.trim());
    }
    fd.append('website', $('sw-hp').value);
    state.sending = true;
    var btn = $('sw-send'); btn.disabled = true;
    api(C.urls.send, { method: 'POST', body: fd }).then(function (d) {
      state.sending = false; btn.disabled = false;
      if (!d.ok) { showErr(d.error); return; }
      text.value = ''; grow(); clearPhoto();
      if (d.message) {
        state.stick = true;
        appendMessages([d.message]);
        toBottom();
        paintThread(d.thread);
      }
      schedule();
    });
  });

  // ---- FAQ search in the aside: the assistant's answer + matching questions (each opens its answer on demand)
  var res = $('hc-res'), top = $('hc-top'), q = $('hc-q'), seq = 0, timer = null;
  function faqItem(it) {
    var d = el('details', 'hc-q');
    d.appendChild(el('summary', null, it.q));
    var body = el('p', null, T('sw_loading'));
    d.appendChild(body);
    var done = false;
    d.addEventListener('toggle', function () {
      if (!d.open || done) return;
      done = true;
      api(C.urls.faqBase + it.id + '/').then(function (r) { body.textContent = r.ok ? r.a : r.error; body.className = 'hc-ans'; });
    });
    return d;
  }
  function search(term) {
    var mine = ++seq;
    clear(res);
    if (!term) { res.hidden = true; top.hidden = false; return; }
    top.hidden = true; res.hidden = false;
    res.appendChild(el('p', 'sw-muted', T('sw_loading')));
    api(C.urls.search + '?q=' + encodeURIComponent(term)).then(function (d) {
      if (mine !== seq) return;
      clear(res);
      if (!d.ok) { res.appendChild(el('p', 'sw-err-t', d.error)); return; }
      if (d.assistant) {
        var card = el('div', 'sw-ans');
        card.appendChild(el('small', null, T('sw_assistant_says')));
        card.appendChild(el('p', null, d.assistant.answer));
        (d.assistant.links || []).forEach(function (l) {
          if (String(l.url).charAt(0) !== '/') return;
          var a = el('a', 'sw-link', l.label); a.href = l.url; card.appendChild(a);
        });
        res.appendChild(card);
      }
      (d.faq || []).forEach(function (it) { res.appendChild(faqItem(it)); });
      if (!d.assistant && !(d.faq || []).length) res.appendChild(el('p', 'sw-muted', T('sw_no_results')));
    });
  }
  q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { search(q.value.trim()); }, 300); });
  $('hc-search').addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); search(q.value.trim()); });

  load().then(schedule);
})();
