/* Support widget: one round button -> a panel with three tabs (Home, Messages, Help).
   Strings and URLs come from <script type="application/json" id="sw-config"> (not executable, so the CSP allows it).
   Everything the server sends is put in with textContent, never innerHTML. Polling: ~8 s while the panel is open, slow while it is closed,
   paused while the browser tab is hidden. The voice assistant keeps its own panel (voice.js); its button lives in the Help tab. */
(function () {
  'use strict';
  var cfgEl = document.getElementById('sw-config'), fab = document.getElementById('sw-fab'), panel = document.getElementById('sw-panel');
  if (!cfgEl || !fab || !panel) return;
  var C;
  try { C = JSON.parse(cfgEl.textContent); } catch (e) { return; }
  var T = function (k) { return (C.t && C.t[k.replace(/_/g, '-')]) || ''; };
  var $ = function (id) { return document.getElementById(id); };
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var OPEN_MS = 8000, IDLE_MS = 45000, HIDDEN_MS = 90000;

  var views = { home: $('sw-v-home'), msgs: $('sw-v-msgs'), help: $('sw-v-help') };
  var tabs = panel.querySelectorAll('[data-sw-tab]');
  var state = { hoursText: (C.status && C.status.hours_answer) || '', readUpto: 0, tab: 'home', open: false, unread: C.unread || 0, lastId: 0, thread: null, known: !!C.auth || (C.unread || 0) > 0, loadedMsgs: false,
                loadedHome: false, loadedFaq: false, sending: false, photo: null, helpBack: null, pollTimer: null, polling: false };

  // ---------------------------------------------------------------- helpers
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function fmt(s, o) { return String(s || '').replace(/\{(\w+)\}/g, function (m, k) { return o && o[k] != null ? o[k] : m; }); }
  function csrf() { var i = panel.querySelector('[name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }
  function ago(iso) {
    var s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 60) return T('sw_just_now');
    if (s < 3600) return fmt(T('sw_min_ago'), { n: Math.floor(s / 60) });
    if (s < 86400) return fmt(T('sw_hour_ago'), { n: Math.floor(s / 3600) });
    return fmt(T('sw_day_ago'), { n: Math.floor(s / 86400) });
  }
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
  function avatar(src, initials, cls) {
    var a = el('span', 'sw-ava' + (cls ? ' ' + cls : ''));
    if (src) { var i = el('img'); i.src = src; i.alt = ''; i.loading = 'lazy'; i.onerror = function () { a.textContent = initials || ''; i.remove(); }; a.appendChild(i); }
    else a.textContent = initials || '';
    return a;
  }

  // ---------------------------------------------------------------- unread badges
  function setUnread(n) {
    state.unread = n || 0;
    [$('sw-fab-badge'), $('sw-tab-badge')].forEach(function (b) {
      if (!b) return;
      b.hidden = !state.unread;
      b.textContent = state.unread > 9 ? '9+' : String(state.unread);
    });
    fab.setAttribute('data-unread', state.unread ? '1' : '0');
  }
  setUnread(state.unread);

  // ---------------------------------------------------------------- open / close / tabs
  function focusables() {
    return Array.prototype.filter.call(panel.querySelectorAll('a[href],button,input,textarea,select,[tabindex]:not([tabindex="-1"])'), function (n) {
      return !n.disabled && !n.closest('[hidden]') && n.offsetParent !== null && n.type !== 'hidden';
    });
  }
  function showTab(name, focus) {
    if (!views[name]) name = 'home';
    state.tab = name;
    Object.keys(views).forEach(function (k) { views[k].hidden = k !== name; });
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-sw-tab') === name;
      t.setAttribute('aria-current', on ? 'true' : 'false');
      t.classList.toggle('on', on);
    });
    store('fz_sw_tab', name);
    if (name === 'home') loadHome();
    if (name === 'msgs') openMessages();
    if (name === 'help') loadFaq();
    if (focus) {
      var f = name === 'msgs' ? $('sw-text') : name === 'help' ? $('sw-q') : null;
      if (f && !(f.offsetParent === null)) { try { f.focus({ preventScroll: true }); } catch (e) {} }
    }
    schedule();
  }
  function open(tab) {
    if (state.open) { if (tab) showTab(tab, true); return; }
    state.open = true;
    panel.hidden = false;
    void panel.offsetWidth;  // lets the transition start from the closed state
    panel.classList.add('open');
    fab.setAttribute('aria-expanded', 'true');
    document.documentElement.classList.add('sw-lock');
    showTab(tab || store('fz_sw_tab') || 'home', false);
    var first = panel.querySelector('.sw-x');
    if (first) { try { first.focus({ preventScroll: true }); } catch (e) {} }
  }
  function close(noFocus) {
    if (!state.open) return;
    state.open = false;
    panel.classList.remove('open');
    fab.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('sw-lock');
    var done = function () { if (!state.open) panel.hidden = true; };
    if (reduce) done(); else setTimeout(done, 220);
    if (!noFocus) { try { fab.focus({ preventScroll: true }); } catch (e) {} }
    schedule();
  }
  fab.addEventListener('click', function () { if (state.open) close(); else open(); });
  panel.querySelector('.sw-x').addEventListener('click', function () { close(); });
  tabs.forEach(function (t) { t.addEventListener('click', function () { showTab(t.getAttribute('data-sw-tab'), true); }); });
  panel.querySelectorAll('[data-sw-go]').forEach(function (b) { b.addEventListener('click', function () { showTab(b.getAttribute('data-sw-go'), true); }); });
  document.addEventListener('keydown', function (e) {
    if (!state.open) return;
    if (e.key === 'Escape') { var vp = $('vpanel'); if (vp && !vp.hidden) return; e.preventDefault(); close(); return; }
    if (e.key !== 'Tab') return;
    var f = focusables();
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (!panel.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  // the voice assistant has its own panel: the widget makes room for it and hands the focus back when it closes
  var vmic = $('vmic'), vpanel = $('vpanel');
  if (vmic) vmic.addEventListener('click', function () { close(true); });
  if (vpanel && window.MutationObserver) {
    new MutationObserver(function () { if (vpanel.hidden && !state.open) { try { fab.focus({ preventScroll: true }); } catch (e) {} } }).observe(vpanel, { attributes: true, attributeFilter: ['hidden'] });
  }

  // ---------------------------------------------------------------- home tab
  function staffFaces(list) {
    var box = $('sw-faces');
    clear(box);
    (list || []).slice(0, 3).forEach(function (p) {
      var a = avatar(p.src, p.initials, 'sw-face' + (p.online ? ' online' : ''));
      if (p.online) a.title = T('sw_online');
      box.appendChild(a);
    });
  }
  function paintStatus(st) {  // real opening hours: open now, or closed until the opening time
    if (!st) return;
    var box = $('sw-st'), tx = $('sw-st-text');
    if (tx) tx.textContent = st.text;
    if (box) box.classList.toggle('on', !!st.open);
    state.hoursText = st.hours_answer || '';
  }
  function paintMember(m) {
    var box = $('sw-mem');
    if (!box) return;
    if (!m) { box.hidden = true; return; }
    box.hidden = false;
    $('sw-mem-text').textContent = m.text;
    var a = $('sw-mem-link');
    a.textContent = T(m.active ? 'sw_ms_extend' : 'sw_ms_buy');
    box.classList.toggle('warn', !m.active || m.days <= 3);
  }
  function faqRow(item, onPick) {
    var b = el('button', 'sw-row');
    b.type = 'button';
    b.appendChild(el('span', 'sw-row-t', item.q));
    b.appendChild(chev());
    b.addEventListener('click', function () { onPick(item); });
    return b;
  }
  function chev() {
    var s = el('span', 'sw-chev');
    s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>';  // fixed markup, no server data
    return s;
  }
  function renderLast(last) {
    var card = $('sw-last');
    if (!last) { card.hidden = true; return; }
    card.hidden = false;
    clear(card.querySelector('.sw-last-body'));
    var body = card.querySelector('.sw-last-body');
    body.appendChild(avatar(last.avatar, last.initials, 'sw-ava-s'));
    var mid = el('span', 'sw-last-mid');
    var who = last.staff ? last.name : T('sw_you');
    var top = el('span', 'sw-last-top');
    top.appendChild(el('b', null, who));
    top.appendChild(el('small', null, ago(last.at)));
    mid.appendChild(top);
    mid.appendChild(el('span', 'sw-last-prev', last.preview || (last.photo ? T('sw_photo') : '')));
    body.appendChild(mid);
    if (last.unread) { var d = el('i', 'sw-dot'); d.setAttribute('aria-label', T('sw_unread')); body.appendChild(d); }
  }
  function renderTop(list) {
    var box = $('sw-top');
    clear(box);
    (list || []).forEach(function (it) { box.appendChild(faqRow(it, function (x) { showTab('help'); openArticle(x.id, 'list'); })); });
  }
  function loadHome() {
    api(C.urls.home).then(function (d) {
      if (!d.ok) return;
      state.loadedHome = true;
      staffFaces(d.staff);
      paintStatus(d.status);
      paintMember(d.member);
      renderLast(d.last);
      renderTop(d.top);
      if (d.thread) state.known = true;
      setUnread(d.unread);
      schedule();
    });
  }
  $('sw-last').addEventListener('click', function () { showTab('msgs', true); });
  $('sw-new').addEventListener('click', function () { showTab('msgs', true); });
  // "Ask the assistant" on the home tab: the answer appears right here; a link continues in the Help tab
  var inline = $('sw-inline'), askSeq = 0;
  function inlineCard(extra) {  // fills the inline box: a card with the text, optional links, and the "continue in Help" button
    clear(inline);
    inline.hidden = false;
    return extra;
  }
  function askHome(term) {
    var mine = ++askSeq;
    inlineCard();
    inline.appendChild(el('p', 'sw-muted', T('sw_loading')));
    api(C.urls.search + '?q=' + encodeURIComponent(term)).then(function (d) {
      if (mine !== askSeq) return;
      clear(inline);
      if (!d.ok) { inline.appendChild(el('p', 'sw-err-t', d.error)); return; }
      if (d.assistant) {
        var card = el('div', 'sw-ans');
        card.appendChild(el('small', null, T('sw_assistant_says')));
        card.appendChild(el('p', null, d.assistant.answer));
        (d.assistant.links || []).forEach(function (l) {
          if (String(l.url).charAt(0) !== '/') return;
          var a = el('a', 'sw-link', l.label); a.href = l.url; card.appendChild(a);
        });
        inline.appendChild(card);
      }
      (d.faq || []).slice(0, 3).forEach(function (it) { inline.appendChild(faqRow(it, function (x) { showTab('help'); openArticle(x.id, 'main'); })); });
      if (!d.assistant && !(d.faq || []).length) inline.appendChild(el('p', 'sw-muted', T('sw_no_results')));
      var more = el('button', 'sw-pill sw-more', T('sw_continue')); more.type = 'button';
      more.addEventListener('click', function () { showTab('help', true); $('sw-q').value = term; runSearch(term); });
      inline.appendChild(more);
      if (!d.assistant && !(d.faq || []).length) {
        var go = el('button', 'sw-btn', T('sw_send_us')); go.type = 'button';
        go.addEventListener('click', function () { showTab('msgs', true); });
        inline.appendChild(go);
      }
    });
  }
  $('sw-hsearch').addEventListener('submit', function (e) {
    e.preventDefault();
    var qv = $('sw-hq').value.trim();
    if (!qv) { inline.hidden = true; return; }
    askHome(qv);
  });
  var hoursBtn = $('sw-qa-hours');
  if (hoursBtn) hoursBtn.addEventListener('click', function () {  // opening hours answered on the spot from the settings
    ++askSeq;
    inlineCard();
    var card = el('div', 'sw-ans');
    card.appendChild(el('small', null, T('sw_qa_hours')));
    card.appendChild(el('p', null, state.hoursText));
    inline.appendChild(card);
    hoursBtn.setAttribute('aria-expanded', 'true');
    inline.scrollIntoView({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' });
  });

  // ---------------------------------------------------------------- messages tab
  var list = $('sw-list'), text = $('sw-text'), form = $('sw-form'), errBox = $('sw-err'), contact = $('sw-contact'), fileIn = $('sw-file'), chip = $('sw-chip');
  function showErr(msg) { errBox.textContent = msg || ''; errBox.hidden = !msg; }
  function nearBottom() { return list.scrollHeight - list.scrollTop - list.clientHeight < 90; }
  function toBottom() { list.scrollTop = list.scrollHeight; }
  function bubble(m) {
    var row = el('div', 'sw-b ' + (m.staff ? 'staff' : 'mine'));
    row.setAttribute('data-id', m.id);
    if (m.staff) row.appendChild(avatar(m.avatar, m.initials, 'sw-ava-s'));
    var box = el('div', 'sw-b-box');
    if (m.staff) box.appendChild(el('small', 'sw-b-name', m.name));
    if (m.image) {
      var a = el('a', 'sw-b-img'); a.href = m.image; a.target = '_blank'; a.rel = 'noopener noreferrer';
      var im = el('img'); im.src = m.image; im.alt = T('sw_photo'); im.loading = 'lazy'; im.addEventListener('load', function () { if (state.stick) toBottom(); });
      a.appendChild(im); box.appendChild(a);
    }
    if (m.text) box.appendChild(el('p', null, m.text));
    var meta = el('small', 'sw-b-time', clock(m.at) + (!m.staff && m.read ? ' · ' + T('sw_seen') : ''));
    box.appendChild(meta);
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
  function markSeen(upto) {  // "Seen" on my own bubbles that staff have read (the poll only brings new messages, so older bubbles are updated here)
    state.readUpto = Math.max(state.readUpto, upto);
    list.querySelectorAll('.sw-b.mine:not(.seen)').forEach(function (row) {
      if (parseInt(row.getAttribute('data-id'), 10) > state.readUpto) return;
      row.classList.add('seen');
      var tm = row.querySelector('.sw-b-time');
      if (tm && tm.textContent.indexOf(T('sw_seen')) === -1) tm.textContent += ' · ' + T('sw_seen');
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
  function loadThread() {
    return api(C.urls.thread).then(function (d) {
      state.loadedMsgs = true;
      if (!d.ok) { showErr(d.error); return; }
      clear(list);
      state.lastId = 0;
      paintThread(d.thread);
      if (d.thread) state.known = true;
      if (!d.messages.length) list.appendChild(el('p', 'sw-empty', T('sw_empty_thread') + (C.auth ? '' : ' ' + T('sw_guest_intro'))));
      state.stick = true;
      appendMessages(d.messages);
      toBottom();
      if (d.read_upto) markSeen(d.read_upto);
      if (d.unread) markRead();
    });
  }
  function markRead() {
    api(C.urls.read, { method: 'POST' }).then(function () { setUnread(0); });
  }
  function openMessages() {
    if (!state.loadedMsgs) loadThread(); else if (state.unread) markRead();
  }
  function poll() {
    if (state.polling || !state.known) return Promise.resolve();
    state.polling = true;
    return api(C.urls.thread + '?after=' + state.lastId).then(function (d) {
      state.polling = false;
      if (!d.ok) return;
      if (d.thread) paintThread(d.thread);
      if (d.read_upto) markSeen(d.read_upto);
      var viewing = state.open && state.tab === 'msgs';
      if (d.messages && d.messages.length && state.loadedMsgs) appendMessages(d.messages);
      if (viewing) { if (d.unread) markRead(); }
      else setUnread(d.unread);
      if (!viewing && state.open && state.tab === 'home' && d.messages && d.messages.length) loadHome();
    });
  }
  function schedule() {
    clearTimeout(state.pollTimer);
    var ms = document.hidden ? HIDDEN_MS : (state.open ? OPEN_MS : IDLE_MS);
    state.pollTimer = setTimeout(function () { (document.hidden ? Promise.resolve() : poll()).then(schedule); }, ms);
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { poll(); schedule(); } });

  function grow() { text.style.height = 'auto'; text.style.height = Math.min(text.scrollHeight, 120) + 'px'; }
  text.addEventListener('input', grow);
  text.addEventListener('keydown', function (e) {
    var coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    if (e.key === 'Enter' && !e.shiftKey && !coarse && !e.isComposing) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { cancelable: true })); }
  });
  $('sw-attach').addEventListener('click', function () { fileIn.click(); });
  fileIn.addEventListener('change', function () {
    var f = fileIn.files && fileIn.files[0];
    clearPhoto();
    if (!f) return;
    state.photo = f;
    clear(chip);
    var im = el('img'); im.alt = ''; try { im.src = URL.createObjectURL(f); } catch (e) {}
    chip.appendChild(im);
    chip.appendChild(el('span', null, f.name));
    var x = el('button', 'sw-chip-x'); x.type = 'button'; x.setAttribute('aria-label', T('sw_remove_photo')); x.textContent = '×';
    x.addEventListener('click', function () { clearPhoto(); });
    chip.appendChild(x);
    chip.hidden = false;
  });
  function clearPhoto() { state.photo = null; fileIn.value = ''; chip.hidden = true; clear(chip); }
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
        state.known = true;
        state.stick = true;
        appendMessages([d.message]);
        toBottom();
        paintThread(d.thread);
        state.loadedHome = false;
      }
      setUnread(0);
      schedule();
    });
  });

  // ---------------------------------------------------------------- help tab
  var q = $('sw-q'), results = $('sw-results'), cats = $('sw-cats'), article = $('sw-article'), helpMain = $('sw-help-main'), timer = null;
  function showHelp(which) {  // 'main' (search + categories) or 'article'
    helpMain.hidden = which !== 'main';
    article.hidden = which !== 'article';
  }
  function loadFaq() {
    if (state.loadedFaq) return;
    api(C.urls.faq).then(function (d) {
      if (!d.ok) return;
      state.loadedFaq = true;
      clear(cats);
      d.categories.forEach(function (c) {
        var sec = el('section', 'sw-cat');
        sec.appendChild(el('h3', null, c.label));
        c.items.forEach(function (it) { sec.appendChild(faqRow(it, function (x) { openArticle(x.id, 'main'); })); });
        cats.appendChild(sec);
      });
    });
  }
  function runSearch(term) {
    clear(results);
    if (!term) { results.hidden = true; cats.hidden = false; $('sw-hint').hidden = false; return; }
    cats.hidden = true; $('sw-hint').hidden = true; results.hidden = false;
    results.appendChild(el('p', 'sw-muted', T('sw_loading')));
    api(C.urls.search + '?q=' + encodeURIComponent(term)).then(function (d) {
      if (q.value.trim() !== term) return;  // a newer search is on its way
      clear(results);
      if (!d.ok) { results.appendChild(el('p', 'sw-err-t', d.error)); return; }
      if (d.assistant) {
        var card = el('div', 'sw-ans');
        card.appendChild(el('small', null, T('sw_assistant_says')));
        card.appendChild(el('p', null, d.assistant.answer));
        (d.assistant.links || []).forEach(function (l) {
          if (String(l.url).charAt(0) !== '/') return;
          var a = el('a', 'sw-link', l.label); a.href = l.url; card.appendChild(a);
        });
        results.appendChild(card);
      }
      if (d.faq.length) {
        results.appendChild(el('h3', null, T('sw_results')));
        d.faq.forEach(function (it) { results.appendChild(faqRow(it, function (x) { openArticle(x.id, 'main'); })); });
      }
      if (!d.faq.length && !d.assistant) {
        results.appendChild(el('p', 'sw-muted', T('sw_no_results')));
        var go = el('button', 'sw-btn', T('sw_send_us')); go.type = 'button';
        go.addEventListener('click', function () { showTab('msgs', true); });
        results.appendChild(go);
      }
    });
  }
  q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { runSearch(q.value.trim()); }, 300); });
  $('sw-hsearch2').addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(timer); runSearch(q.value.trim()); });
  function openArticle(id, back) {
    state.helpBack = back;
    showHelp('article');
    clear($('sw-art-body'));
    $('sw-art-body').appendChild(el('p', 'sw-muted', T('sw_loading')));
    $('sw-fb').hidden = true;
    api(C.urls.faqBase + id + '/').then(function (d) {
      var body = $('sw-art-body');
      clear(body);
      if (!d.ok) { body.appendChild(el('p', 'sw-err-t', d.error)); return; }
      body.appendChild(el('h3', null, d.q));
      body.appendChild(el('p', 'sw-art-text', d.a));
      var fb = $('sw-fb');
      fb.hidden = false; fb.setAttribute('data-id', d.id);
      $('sw-fb-ask').hidden = d.voted !== null; $('sw-fb-yes').hidden = d.voted !== null; $('sw-fb-no').hidden = d.voted !== null;
      $('sw-fb-thanks').hidden = d.voted === null;
    });
  }
  function vote(helpful) {
    var id = $('sw-fb').getAttribute('data-id');
    api(C.urls.faqBase + id + '/feedback/', { method: 'POST', json: { helpful: helpful } }).then(function (d) {
      if (!d.ok) return;
      $('sw-fb-ask').hidden = $('sw-fb-yes').hidden = $('sw-fb-no').hidden = true;
      $('sw-fb-thanks').hidden = false;
      if (!helpful) $('sw-fb-more').hidden = false;
    });
  }
  $('sw-fb-yes').addEventListener('click', function () { vote(true); });
  $('sw-fb-no').addEventListener('click', function () { vote(false); });
  $('sw-fb-more').addEventListener('click', function () { showTab('msgs', true); });
  $('sw-art-back').addEventListener('click', function () { showHelp('main'); $('sw-fb-more').hidden = true; });

  // ---------------------------------------------------------------- start
  try {
    var m = /[?&]support=(messages|help|home)\b/.exec(location.search);
    if (m) {
      open(m[1] === 'messages' ? 'msgs' : m[1]);
      var u = new URL(location.href); u.searchParams.delete('support');
      history.replaceState(null, '', u.pathname + (u.search || '') + u.hash);
    }
  } catch (e) {}
  schedule();
})();
