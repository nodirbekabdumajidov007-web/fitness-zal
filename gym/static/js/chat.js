/* Messenger: live over WebSocket (falls back to polling every 3 s), photos, replies, reactions, edits, search, pins, @mentions,
   read ticks, typing, presence, day chips and grouped bubbles. Everything a member typed is inserted with textContent, never as HTML. */
(function () {
  var log = document.getElementById('chat-log');
  if (!log) return;
  var d = log.dataset;
  var form = document.getElementById('chat-form'), body = document.getElementById('chat-body'), err = document.getElementById('chat-err'), note = document.getElementById('chat-note');
  var file = document.getElementById('chat-file'), preview = document.getElementById('chat-preview'), drop = document.getElementById('chat-drop');
  var statusEl = document.getElementById('m-status'), lightbox = document.getElementById('chat-lightbox'), section = log.closest('.messenger');
  var last = parseInt(d.last || '0', 10), firstId = parseInt(d.first || '0', 10), hasMore = !!d.more, since = parseFloat(d.since) || 0, rxHash = '';
  var busy = false, sending = false, picked = null, loadingOlder = false;
  var direct = d.kind === 'direct', room = !direct, me = parseInt(d.me, 10), canPin = !!d.canPin;
  var EMOJIS = (d.emojis || '').split(' ').filter(Boolean), months = (d.tMonths || '').split(','), editMs = (parseInt(d.editMin, 10) || 15) * 60000;
  var skew = since ? since * 1000 - Date.now() : 0;  // server clock minus ours, so "can still edit" matches the server
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function csrf() { return (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || ''; }
  function post(url, data) {
    var opts = { method: 'POST', credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch', 'X-CSRFToken': csrf() } };
    if (data instanceof FormData) opts.body = data;
    else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(data || {}); }
    return fetch(url, opts).then(function (r) { return r.json().then(function (j) { j._ok = r.ok; return j; }, function () { return { _ok: false }; }); });
  }
  function getJSON(url) {
    return fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }
  function url(tpl, id) { return tpl.replace('/0/', '/' + id + '/'); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function say(text, isErr) {
    var box = isErr ? err : note;
    if (!box) return;
    (isErr ? note : err).textContent = '';
    box.textContent = text || '';
    if (!isErr && text) setTimeout(function () { if (box.textContent === text) box.textContent = ''; }, 6000);
  }

  // ---- report dialog: a small dialog asks why (required), then the report is sent without leaving the chat
  var dlg = document.getElementById('report-dlg'), repForm = dlg && dlg.querySelector('[data-report-form]');
  var repErr = dlg && dlg.querySelector('[data-report-err]'), repUrl = '', repBtn = null;
  function openReport(u, btn) {
    if (!dlg) return;
    repUrl = u; repBtn = btn; repForm.reset(); repErr.hidden = true;
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
  }
  if (dlg) {
    dlg.querySelector('[data-report-cancel]').addEventListener('click', function () { dlg.close(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
    repForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var kind = (repForm.querySelector('input[name=kind]:checked') || {}).value || '', detail = repForm.elements.detail.value.trim();
      if (!kind || (kind === 'other' && !detail)) { repErr.textContent = d.tReportReason; repErr.hidden = false; return; }
      post(repUrl, { kind: kind, detail: detail }).then(function (j) {
        if (j._ok) { dlg.close(); say(d.tReported); }
        else { repErr.textContent = j.error || d.tReportReason; repErr.hidden = false; }
      });
    });
  }

  // ---- layout helpers
  function nearBottom() { return log.scrollHeight - log.scrollTop - log.clientHeight < 120; }
  function toBottom(smooth) { if (smooth && !reduce && log.scrollTo) log.scrollTo({ top: log.scrollHeight, behavior: 'smooth' }); else log.scrollTop = log.scrollHeight; }
  function byId(id) { return log.querySelector('.m-row[data-id="' + id + '"]'); }
  function dayLabel(iso) {
    var t = new Date(), y = new Date(Date.now() - 864e5);
    var f = function (x) { return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0'); };
    if (iso === f(t)) return d.tToday;
    if (iso === f(y)) return d.tYesterday;
    var p = iso.split('-'), s = (d.tDayfmt || '@d @m').replace('@d', parseInt(p[2], 10)).replace('@m', months[parseInt(p[1], 10) - 1] || p[1]);
    return parseInt(p[0], 10) === t.getFullYear() ? s : s + ' ' + p[0];
  }
  function makeChip(iso) { var c = el('div', 'm-day'); c.dataset.day = iso; c.appendChild(el('span', '', dayLabel(iso))); return c; }
  function dividerBefore(row) { var p = row.previousElementSibling; return p && p.id === 'chat-new' ? p : null; }
  function chipBefore(row) {
    var p = row.previousElementSibling;
    if (p && p.id === 'chat-new') p = p.previousElementSibling;
    return p && p.classList.contains('m-day') ? p : null;
  }
  // re-derive day chips and group edges (first/last bubble of a run from one person) from the rows in the DOM
  function regroup() {
    var list = [].slice.call(log.querySelectorAll('.m-row'));
    list.forEach(function (row, i) {
      var prev = list[i - 1], next = list[i + 1];
      var chip = chipBefore(row), needChip = !prev || prev.dataset.day !== row.dataset.day;
      if (needChip && !chip) log.insertBefore(makeChip(row.dataset.day), dividerBefore(row) || row);
      else if (!needChip && chip) chip.remove();
      row.classList.toggle('first', needChip || !!dividerBefore(row) || prev.dataset.sender !== row.dataset.sender);
      row.classList.toggle('last', !next || next.dataset.day !== row.dataset.day || next.dataset.sender !== row.dataset.sender || !!dividerBefore(next));
    });
  }

  // ---- building one message
  function fillText(box, text, names) {
    if (!names || !names.length || text.indexOf('@') < 0) { box.textContent = text; return; }
    var esc = names.slice().sort(function (a, b) { return b.length - a.length; }).map(function (n) { return '@' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
    text.split(new RegExp('(' + esc.join('|') + ')', 'i')).forEach(function (p, i) {
      if (!p) return;
      if (i % 2) box.appendChild(el('mark', 'm-mention', p)); else box.appendChild(document.createTextNode(p));
    });
  }
  function renderChips(box, list) {
    box.textContent = '';
    (list || []).forEach(function (r) {
      var b = el('button', 'm-chip' + (r.mine ? ' mine' : '')); b.type = 'button'; b.dataset.e = r.e;
      b.appendChild(el('span', '', r.e)); b.appendChild(el('b', 'num', String(r.n)));
      box.appendChild(b);
    });
    box.hidden = !(list && list.length);
  }
  function svgBtn(act, label, paths) {
    var b = el('button', 'm-hb'); b.type = 'button'; b.dataset.act = act; b.setAttribute('aria-haspopup', 'menu'); b.setAttribute('aria-label', label);
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + paths + '</svg>';  // static markup, no member text
    return b;
  }
  function buildRow(m) {
    var row = el('div', 'm-row' + (m.mine ? ' mine' : '') + (m.mentioned_me ? ' mentioned' : ''));
    row.dataset.id = m.id; row.dataset.sender = m.sender; row.dataset.day = m.day; row.dataset.name = m.name; row.dataset.ts = m.ts || 0;
    if (room && !m.mine) { var av = el('span', 'm-ava', m.initials); av.style.setProperty('--h', m.hue); row.appendChild(av); }
    var col = el('div', 'm-col'), b = el('div', 'm-bubble' + (m.image && !m.body ? ' photo-only' : ''));
    if (room && !m.mine) { var nm = el('div', 'm-name', m.name); nm.style.setProperty('--h', m.hue); b.appendChild(nm); }
    if (m.deleted) b.appendChild(el('i', 'm-del', d.tDeleted));
    else {
      if (m.reply) {
        var q = el('button', 'm-quote'); q.type = 'button'; q.dataset.jump = m.reply.id;
        q.appendChild(el('b', '', m.reply.name));
        q.appendChild(el('span', '', m.reply.deleted ? d.tDeleted : (m.reply.text || d.tPhoto)));
        if (m.reply.image) { var qi = el('img'); qi.src = m.reply.image; qi.alt = ''; qi.loading = 'lazy'; q.appendChild(qi); }
        b.appendChild(q);
      }
      if (m.image) {
        var a = el('a', 'm-photo'); a.href = m.image; a.target = '_blank'; a.rel = 'noopener'; a.setAttribute('data-lightbox', '');
        var im = el('img'); im.src = m.image; im.alt = d.tPhoto;
        im.addEventListener('load', function () { if (stickLoad) toBottom(); }); a.appendChild(im); b.appendChild(a);
      }
      if (m.body) { var tx = el('div', 'm-text'); fillText(tx, m.body, m.mentions); b.appendChild(tx); }
    }
    var meta = el('div', 'm-meta');
    if (m.edited) meta.appendChild(el('span', 'm-edited', d.tEdited));
    meta.appendChild(el('span', 'num', m.time));
    if (m.mine && direct && !m.deleted) meta.appendChild(el('span', 'm-tick' + (m.read ? ' read' : ''), m.read ? '✓✓' : '✓'));
    b.appendChild(meta);
    col.appendChild(b);
    var rx = el('div', 'm-rx'); renderChips(rx, m.deleted ? [] : m.reactions); col.appendChild(rx);
    if (!m.deleted) {
      var hov = el('div', 'm-hov');
      hov.appendChild(svgBtn('react', d.tReact, '<circle cx="12" cy="12" r="9"/><path d="M8.5 14a4 4 0 0 0 7 0"/><path d="M9 9.5h.01M15 9.5h.01"/>'));
      hov.appendChild(svgBtn('menu', d.tMenu, '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>'));
      col.appendChild(hov);
    }
    row.appendChild(col);
    return row;
  }
  var stickLoad = false;

  function render(m) {
    if (byId(m.id)) return;
    var empty = document.getElementById('chat-empty'); if (empty) empty.remove();
    var stick = nearBottom() || m.mine;
    var row = buildRow(m);
    log.appendChild(row); regroup();
    stickLoad = stick;
    if (stick) toBottom(); else if (!m.mine) bump();
    if (m.id > last) last = m.id;
  }
  function replaceRow(m) {  // an edited message: same place, new content
    var old = byId(m.id); if (!old) return;
    var row = buildRow(m);
    row.className = row.className.replace(/\b(first|last)\b/g, '') + (old.classList.contains('first') ? ' first' : '') + (old.classList.contains('last') ? ' last' : '');
    old.parentNode.replaceChild(row, old);
  }
  function setReactions(id, list) { var row = byId(id); if (row) renderChips(row.querySelector('.m-rx'), list); }
  function markDeleted(row) {
    var b = row.querySelector('.m-bubble');
    b.querySelectorAll('.m-photo,.m-text,.m-quote,.m-tick,.m-edited').forEach(function (x) { x.remove(); });
    if (!b.querySelector('.m-del')) b.insertBefore(el('i', 'm-del', d.tDeleted), b.querySelector('.m-meta'));
    b.classList.remove('photo-only');
    var rx = row.querySelector('.m-rx'); if (rx) { rx.textContent = ''; rx.hidden = true; }
    var hov = row.querySelector('.m-hov'); if (hov) hov.remove();
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
  function setStats(s) {
    var box = document.getElementById('m-stats');
    if (!box || !s) return;
    box.textContent = d.tMembers.replace('@n', s.members) + ' · ';
    box.appendChild(el('span', 'on', d.tOnlineN.replace('@n', s.online)));
  }
  var pinBar = document.getElementById('chat-pin'), pinText = document.getElementById('chat-pin-text');
  function setPin(p) {
    if (!pinBar) return;
    pinBar.hidden = !p;
    if (!p) { delete pinBar.dataset.id; pinText.textContent = ''; return; }
    pinBar.dataset.id = p.id; pinText.textContent = '';
    pinText.appendChild(el('b', '', p.name)); pinText.appendChild(document.createTextNode(' ' + (p.text || d.tPhoto)));
  }

  // ---- unread counter + "scroll to bottom" button
  var fab = document.getElementById('chat-fab'), fabN = document.getElementById('chat-fab-n'), unseen = 0;
  function bump() { unseen++; updateFab(); }
  function updateFab() {
    if (!fab) return;
    var away = !nearBottom();
    fab.hidden = !away;
    fabN.hidden = !(away && unseen); fabN.textContent = unseen > 99 ? '99+' : String(unseen);
  }
  if (fab) fab.addEventListener('click', function () { unseen = 0; toBottom(true); updateFab(); });

  // ---- older messages (infinite scroll up) and jumping to a message
  function loadOlder(target) {
    if (loadingOlder || !hasMore) return Promise.resolve();
    loadingOlder = true; log.setAttribute('aria-busy', 'true');
    return getJSON(d.history + '?before=' + firstId + (target ? '&target=' + target : '')).then(function (j) {
      if (j && j.messages.length) {
        var h = log.scrollHeight, top = log.scrollTop, anchor = log.firstElementChild, added = 0;
        j.messages.forEach(function (m) {
          if (byId(m.id)) return;
          log.insertBefore(buildRow(m), anchor); added++;
        });
        regroup();
        if (added) log.scrollTop = top + (log.scrollHeight - h);  // keep what the reader was looking at in place
        firstId = j.messages[0].id;
      }
      hasMore = !!(j && j.has_more);
    }).then(function () { loadingOlder = false; log.removeAttribute('aria-busy'); });
  }
  function highlight(row) {
    if (row.scrollIntoView) row.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' });
    row.classList.add('hl'); setTimeout(function () { row.classList.remove('hl'); }, 1800);
  }
  function jumpTo(id) {
    id = parseInt(id, 10);
    var row = byId(id);
    if (row) return highlight(row);
    (function step(n) {
      if (!hasMore || n > 15) return say(d.tJumpFail, true);
      loadOlder(id).then(function () { var r = byId(id); if (r) highlight(r); else step(n + 1); });
    })(0);
  }
  log.addEventListener('scroll', function () {
    if (nearBottom()) unseen = 0;
    updateFab();
    if (log.scrollTop < 80 && hasMore) loadOlder();
  });

  // ---- message action menu: reactions + reply / copy / edit / pin / delete / report (touch-hold, right-click, hover buttons, keyboard)
  var menu = el('div', 'm-menu'); menu.setAttribute('role', 'menu'); menu.hidden = true; document.body.appendChild(menu);
  var menuRow = null, menuTrigger = null, armed = null;
  function closeMenu(refocus) {
    if (menu.hidden) return;
    menu.hidden = true; menu.textContent = ''; armed = null;
    if (refocus && menuTrigger && menuTrigger.focus) menuTrigger.focus();
    menuRow = menuTrigger = null;
  }
  function rowText(row) { var t = row.querySelector('.m-text'); return t ? t.textContent : ''; }
  function canEditRow(row) {
    return row.classList.contains('mine') && !!row.querySelector('.m-text') && (Date.now() + skew - (parseInt(row.dataset.ts, 10) || 0) * 1000) < editMs;
  }
  function mi(label, fn, cls) {
    var b = el('button', 'm-mi' + (cls ? ' ' + cls : ''), label); b.type = 'button'; b.setAttribute('role', 'menuitem');
    b.addEventListener('click', function () { fn(b); }); return b;
  }
  function react(row, emoji) {
    post(url(d.react, row.dataset.id), { emoji: emoji }).then(function (j) {
      if (j._ok) setReactions(row.dataset.id, j.reactions); else say(j.error || '!', true);
    });
  }
  function copyText(text) {
    var done = function () { say(d.tCopied); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
    else { var t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); done(); } catch (e) {} t.remove(); }
  }
  function openMenu(row, full, trigger) {
    closeMenu();
    if (!row || row.querySelector('.m-del')) return;
    menuRow = row; menuTrigger = trigger || row.querySelector('.m-hb[data-act="menu"]');
    var mine = row.classList.contains('mine'), id = row.dataset.id, text = rowText(row);
    var bar = el('div', 'm-mrx'); bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', d.tReact);
    var cur = (row.querySelector('.m-chip.mine') || {}).dataset;
    EMOJIS.forEach(function (e) {
      var b = el('button', 'm-mi m-emo' + (cur && cur.e === e ? ' on' : ''), e); b.type = 'button'; b.setAttribute('role', 'menuitem');
      b.addEventListener('click', function () { closeMenu(true); react(row, e); });
      bar.appendChild(b);
    });
    menu.appendChild(bar);
    if (full) {
      var acts = [];
      if (form) acts.push(mi(d.tReply, function () { closeMenu(); setCtx('reply', row); }));
      if (text) acts.push(mi(d.tCopy, function () { closeMenu(); copyText(text); }));
      if (form && canEditRow(row)) acts.push(mi(d.tEdit, function () { closeMenu(); setCtx('edit', row); }));
      if (canPin && room) {
        var pinned = pinBar && pinBar.dataset.id === id;
        acts.push(mi(pinned ? d.tUnpin : d.tPin, function () { closeMenu(); post(d.pin, { id: pinned ? 0 : +id }).then(function (j) { if (j._ok) setPin(j.pin); }); }));
      }
      if (mine) acts.push(mi(d.tDelete, function (b) {
        if (armed !== b) { armed = b; b.textContent = d.tSure; b.classList.add('armed'); return; }
        closeMenu();
        post(url(d.delete, id)).then(function (j) { if (j._ok) markDeleted(row); });
      }, 'danger'));
      else acts.push(mi(d.tReport, function () { closeMenu(); openReport(url(d.report, id), null); }));
      var list = el('div', 'm-mlist'); acts.forEach(function (a) { list.appendChild(a); }); menu.appendChild(list);
    }
    menu.style.visibility = 'hidden'; menu.hidden = false;
    var anchor = row.querySelector('.m-bubble').getBoundingClientRect(), w = menu.offsetWidth, h = menu.offsetHeight;
    var x = Math.max(8, Math.min(mine ? anchor.right - w : anchor.left, window.innerWidth - w - 8));
    var y = anchor.bottom + 6; if (y + h > window.innerHeight - 8) y = Math.max(8, anchor.top - h - 6);
    menu.style.left = x + 'px'; menu.style.top = y + 'px'; menu.style.visibility = '';
    var first = menu.querySelector('.m-mi'); if (first) first.focus();
  }
  menu.addEventListener('keydown', function (e) {
    var items = [].slice.call(menu.querySelectorAll('.m-mi')), i = items.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
    else if (e.key === 'Home') { e.preventDefault(); items[0].focus(); }
    else if (e.key === 'End') { e.preventDefault(); items[items.length - 1].focus(); }
    else if (e.key === 'Tab') closeMenu(true);
  });
  document.addEventListener('mousedown', function (e) { if (!menu.hidden && !menu.contains(e.target)) closeMenu(); });
  window.addEventListener('resize', function () { closeMenu(); });
  log.addEventListener('scroll', function () { closeMenu(); });

  log.addEventListener('click', function (e) {
    var t = e.target;
    var hb = t.closest('.m-hb');
    if (hb) { openMenu(hb.closest('.m-row'), hb.dataset.act === 'menu', hb); return; }
    var chip = t.closest('.m-chip');
    if (chip) { showWho(chip.closest('.m-row').dataset.id); return; }
    var q = t.closest('.m-quote');
    if (q) { jumpTo(q.dataset.jump); return; }
    var a = t.closest('[data-lightbox]');
    if (a && lightbox) { e.preventDefault(); lightbox.querySelector('img').src = a.getAttribute('href'); lightbox.hidden = false; }
  });
  log.addEventListener('contextmenu', function (e) {
    var bub = e.target.closest('.m-bubble');
    if (!bub) return;
    e.preventDefault(); openMenu(bub.closest('.m-row'), true, null);
  });

  // reaction details: who reacted with what
  var rxDlg = document.getElementById('rx-dlg'), rxList = document.getElementById('rx-list');
  function showWho(id) {
    if (!rxDlg) return;
    getJSON(url(d.reactions, id)).then(function (j) {
      if (!j) return;
      rxList.textContent = '';
      j.groups.forEach(function (g) {
        var line = el('p', 'rx-line'); line.appendChild(el('span', 'rx-e', g.e)); line.appendChild(el('span', '', g.names.join(', '))); rxList.appendChild(line);
      });
      if (rxDlg.showModal) rxDlg.showModal(); else rxDlg.setAttribute('open', '');
    });
  }
  if (rxDlg) {
    document.getElementById('rx-close').addEventListener('click', function () { rxDlg.close(); });
    rxDlg.addEventListener('click', function (e) { if (e.target === rxDlg) rxDlg.close(); });
  }

  // touch: hold a bubble for the menu, swipe a message to the right to reply
  var hold = null, sw = null;
  log.addEventListener('touchstart', function (e) {
    var row = e.target.closest('.m-row');
    if (!row || e.touches.length !== 1 || e.target.closest('.m-chip,.m-hb,.m-quote,a')) { hold = sw = null; return; }
    var p = e.touches[0];
    sw = { row: row, x: p.clientX, y: p.clientY, dx: 0, on: false, dead: false };
    clearTimeout(hold);
    hold = setTimeout(function () {
      if (sw && !sw.on) { var r = sw.row; sw = null; if (navigator.vibrate) try { navigator.vibrate(12); } catch (x) {} openMenu(r, true, null); }
    }, 480);
  }, { passive: true });
  log.addEventListener('touchmove', function (e) {
    if (!sw || sw.dead) return;
    var p = e.touches[0], dx = p.clientX - sw.x, dy = p.clientY - sw.y;
    if (!sw.on) {
      if (Math.abs(dx) > 8 || Math.abs(dy) > 8) clearTimeout(hold);
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { sw.dead = true; return; }
      if (dx > 12 && dx > Math.abs(dy) * 1.5) sw.on = true; else return;
    }
    e.preventDefault();
    sw.dx = Math.max(0, Math.min(dx, 72));
    sw.row.querySelector('.m-col').style.transform = 'translateX(' + sw.dx + 'px)';
    sw.row.classList.toggle('swipe-ready', sw.dx >= 56);
  }, { passive: false });
  function endTouch() {
    clearTimeout(hold);
    if (!sw) return;
    var col = sw.row.querySelector('.m-col'), ready = sw.on && sw.dx >= 56, row = sw.row;
    col.style.transform = ''; row.classList.remove('swipe-ready'); sw = null;
    if (ready && form && !row.querySelector('.m-del')) setCtx('reply', row);
  }
  log.addEventListener('touchend', endTouch);
  log.addEventListener('touchcancel', endTouch);

  // ---- composer: reply / edit bar, photo pick / paste / drop, preview, auto-grow, Enter to send
  var ctxBar = document.getElementById('chat-ctx'), ctxTitle = document.getElementById('ctx-title'), ctxText = document.getElementById('ctx-text'), attach = document.getElementById('chat-attach');
  var ctx = null;
  function snip(s) { s = (s || '').replace(/\s+/g, ' ').trim(); return s.length > 90 ? s.slice(0, 89) + '…' : s; }
  function grow() { body.style.height = 'auto'; body.style.height = Math.min(body.scrollHeight, 160) + 'px'; }
  function setCtx(mode, row) {
    if (!form) return;
    clearCtx();
    ctx = { mode: mode, id: parseInt(row.dataset.id, 10) };
    var text = rowText(row);
    ctxTitle.textContent = mode === 'reply' ? d.tReplying.replace('@', row.dataset.name) : d.tEditing;
    ctxText.textContent = snip(text) || d.tPhoto;
    ctxBar.hidden = false;
    if (mode === 'edit') { body.value = text; setPicked(null); if (attach) attach.hidden = true; grow(); }
    body.focus();
  }
  function clearCtx() {
    if (ctx && ctx.mode === 'edit') { body.value = ''; grow(); }
    ctx = null;
    if (ctxBar) ctxBar.hidden = true;
    if (attach) attach.hidden = false;
  }
  var ctxX = document.getElementById('ctx-x'); if (ctxX) ctxX.addEventListener('click', function () { clearCtx(); body.focus(); });

  function setPicked(f) {
    if (f && !/^image\/(jpeg|png|webp)$/.test(f.type)) { say(form.dataset.badImage || '!', true); return; }
    picked = f || null;
    if (!preview) return;
    if (picked) { preview.querySelector('img').src = URL.createObjectURL(picked); preview.hidden = false; }
    else { preview.hidden = true; preview.querySelector('img').removeAttribute('src'); if (file) file.value = ''; }
  }

  // @mention autocomplete (public room): suggestions come from people who wrote in the room lately
  var suggest = document.getElementById('chat-suggest'), sugTimer = null, sugItems = [], sugIdx = -1, sugToken = null;
  function closeSuggest() { if (suggest) { suggest.hidden = true; suggest.textContent = ''; } sugItems = []; sugIdx = -1; sugToken = null; }
  function pickSuggest(i) {
    var m = sugItems[i]; if (!m || !sugToken) return;
    var v = body.value, before = v.slice(0, sugToken.start), after = v.slice(sugToken.end);
    body.value = before + '@' + m.name + ' ' + after;
    var pos = (before + '@' + m.name + ' ').length; body.setSelectionRange(pos, pos);
    closeSuggest(); grow(); body.focus();
  }
  function markSuggest() {
    [].forEach.call(suggest.children, function (li, i) { li.setAttribute('aria-selected', i === sugIdx ? 'true' : 'false'); li.classList.toggle('on', i === sugIdx); });
  }
  function checkMention() {
    if (!room || !suggest) return;
    var pos = body.selectionStart, m = /(^|\s)@([^\s@]{0,20})$/.exec(body.value.slice(0, pos));
    if (!m) { closeSuggest(); return; }
    var q = m[2]; sugToken = { start: pos - q.length - 1, end: pos };
    clearTimeout(sugTimer);
    sugTimer = setTimeout(function () {
      getJSON(d.members + '?q=' + encodeURIComponent(q)).then(function (j) {
        if (!j || !sugToken) return;
        sugItems = j.members; sugIdx = sugItems.length ? 0 : -1;
        suggest.textContent = '';
        sugItems.forEach(function (p, i) {
          var li = el('li'); li.setAttribute('role', 'option');
          var av = el('span', 'm-ava', p.initials); av.style.setProperty('--h', p.hue); li.appendChild(av); li.appendChild(el('span', '', p.name));
          li.addEventListener('mousedown', function (ev) { ev.preventDefault(); pickSuggest(i); });
          suggest.appendChild(li);
        });
        suggest.hidden = !sugItems.length; markSuggest();
      });
    }, 150);
  }

  if (form) {
    form.dataset.badImage = d.tBadImage || '';
    if (file) file.addEventListener('change', function () { setPicked(file.files[0]); });
    var x = document.getElementById('chat-preview-x'); if (x) x.addEventListener('click', function () { setPicked(null); });
    body.addEventListener('input', function () { grow(); checkMention(); });
    body.addEventListener('click', checkMention);
    body.addEventListener('blur', function () { setTimeout(closeSuggest, 120); });
    body.addEventListener('keydown', function (e) {
      if (suggest && !suggest.hidden && sugItems.length) {
        if (e.key === 'ArrowDown') { e.preventDefault(); sugIdx = (sugIdx + 1) % sugItems.length; markSuggest(); return; }
        if (e.key === 'ArrowUp') { e.preventDefault(); sugIdx = (sugIdx - 1 + sugItems.length) % sugItems.length; markSuggest(); return; }
        if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); pickSuggest(sugIdx < 0 ? 0 : sugIdx); return; }
        if (e.key === 'Escape') { e.preventDefault(); closeSuggest(); return; }
      }
      if (e.key === 'Escape' && ctx) { e.preventDefault(); clearCtx(); return; }
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
    });
    body.addEventListener('paste', function (e) {
      var item = [].slice.call((e.clipboardData || {}).items || []).find(function (i) { return i.type.indexOf('image/') === 0; });
      if (item && !(ctx && ctx.mode === 'edit')) { e.preventDefault(); setPicked(item.getAsFile()); }
    });
    ['dragenter', 'dragover'].forEach(function (t) { section.addEventListener(t, function (e) { if ([].slice.call(e.dataTransfer.types).indexOf('Files') > -1) { e.preventDefault(); drop.hidden = false; } }); });
    ['dragleave', 'drop'].forEach(function (t) { section.addEventListener(t, function (e) { if (t === 'drop' || e.target === drop) drop.hidden = true; }); });
    section.addEventListener('drop', function (e) { e.preventDefault(); if (e.dataTransfer.files[0] && !(ctx && ctx.mode === 'edit')) setPicked(e.dataTransfer.files[0]); });

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = body.value;
      if (sending || (!text.trim() && !picked)) return;
      say('', true); say('');
      sending = true; form.classList.add('sending');
      var req;
      if (ctx && ctx.mode === 'edit') req = post(url(d.edit, ctx.id), { body: text });
      else {
        var fd = new FormData(); fd.append('body', text); if (picked) fd.append('image', picked, picked.name || 'photo.png');
        if (ctx && ctx.mode === 'reply') fd.append('reply_to', ctx.id);
        req = post(d.send, fd);
      }
      var wasEdit = ctx && ctx.mode === 'edit';
      req.then(function (j) {
        if (j._ok) {
          if (wasEdit) replaceRow(j.message); else render(j.message);
          ctx = null; if (ctxBar) ctxBar.hidden = true; if (attach) attach.hidden = false;
          body.value = ''; grow(); setPicked(null); closeSuggest();
          if (!wasEdit) toBottom();
          if (j.notice) say(j.notice);
        } else say(j.error || '!', true);
      }).catch(function () { say('!', true); }).then(function () { sending = false; form.classList.remove('sending'); body.focus(); });
    });
  }
  if (lightbox) lightbox.addEventListener('click', function () { lightbox.hidden = true; });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && lightbox) lightbox.hidden = true; });

  // ---- header: in-chat search, mute
  var sBtn = document.getElementById('chat-search-btn'), sBox = document.getElementById('chat-search'), sQ = document.getElementById('chat-search-q'), sRes = document.getElementById('chat-results'), sTimer = null;
  if (sBtn) {
    sBtn.addEventListener('click', function () {
      var open = sBox.hidden; sBox.hidden = !open; sBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) sQ.focus(); else { sRes.textContent = ''; sQ.value = ''; }
    });
    sQ.addEventListener('keydown', function (e) { if (e.key === 'Escape') sBtn.click(); });
    sQ.addEventListener('input', function () {
      clearTimeout(sTimer);
      sTimer = setTimeout(function () {
        var q = sQ.value.trim(); sRes.textContent = '';
        if (q.length < 2) return;
        getJSON(d.search + '?q=' + encodeURIComponent(q)).then(function (j) {
          if (!j) return;
          if (!j.results.length) { sRes.appendChild(el('li', 'm-none', d.tNone)); return; }
          j.results.forEach(function (r) {
            var li = el('li'), b = el('button', 'm-res'); b.type = 'button';
            b.appendChild(el('b', '', r.name)); b.appendChild(el('small', 'num', r.date + ' ' + r.time)); b.appendChild(el('span', '', r.text));
            b.addEventListener('click', function () { sBtn.click(); jumpTo(r.id); });
            li.appendChild(b); sRes.appendChild(li);
          });
        });
      }, 300);
    });
  }
  var muteBtn = document.getElementById('chat-mute');
  if (muteBtn) muteBtn.addEventListener('click', function () {
    post(d.mute).then(function (j) {
      if (!j._ok) return;
      muteBtn.classList.toggle('on', j.muted); muteBtn.setAttribute('aria-pressed', j.muted ? 'true' : 'false');
      var l = j.muted ? d.tUnmute : d.tMute; muteBtn.setAttribute('aria-label', l); muteBtn.title = l;
    });
  });
  var pinGo = document.getElementById('chat-pin-go'), pinX = document.getElementById('chat-pin-x');
  if (pinGo) pinGo.addEventListener('click', function () { if (pinBar.dataset.id) jumpTo(pinBar.dataset.id); });
  if (pinX) pinX.addEventListener('click', function () { post(d.pin, { id: 0 }).then(function (j) { if (j._ok) setPin(null); }); });

  // ---- polling (the fallback, and a safety net while the socket is up)
  function poll() {
    if (busy || document.hidden) return;
    busy = true;
    fetch(d.poll + '?after=' + last + '&since=' + since + '&rxh=' + rxHash, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        j.messages.forEach(render);
        (j.edited || []).forEach(replaceRow);
        if (j.rx) Object.keys(j.rx).forEach(function (id) { setReactions(id, j.rx[id]); });
        if (j.rxh) rxHash = j.rxh;
        if (j.now) since = j.now;
        applyReads(j.read_upto);
        applyPresence(j.presence);
        setStats(j.stats);
        if (pinBar && 'pin' in j) setPin(j.pin);
        if (j.typing && j.typing.length) showTyping(j.typing.join(', '));
        (j.deleted || []).forEach(function (id) { var row = byId(id); if (row && !row.querySelector('.m-del')) markDeleted(row); });
      })
      .catch(function () {})
      .then(function () { busy = false; });
  }

  // ---- live channel: WebSocket when the server offers it, polling every 3 s otherwise (and as a safety net every 30 s)
  var ws = null, wsOk = false, retry = 1000, typingTimer = null, lastTypingSent = 0;
  var typingBox = document.getElementById('chat-typing'), typingText = document.getElementById('chat-typing-text');
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
    ws.onopen = function () { wsOk = true; retry = 1000; poll(); };
    ws.onmessage = function (e) {
      var j; try { j = JSON.parse(e.data); } catch (x) { return; }
      if (j.t === 'msg') {
        render(j.m);
        if (typingBox) typingBox.hidden = true;
        if (!j.m.mine && !document.hidden) wsSend({ t: 'read', upto: j.m.id });
      } else if (j.t === 'read') applyReads(j.upto);
      else if (j.t === 'typing') showTyping(j.name);
      else if (j.t === 'presence') applyPresence(j);
      else if (j.t === 'reaction') setReactions(j.id, j.reactions);
      else if (j.t === 'edit') replaceRow(j.m);
      else if (j.t === 'pin') setPin(j.pin);
      else if (j.t === 'deleted') { var row = byId(j.id); if (row && !row.querySelector('.m-del')) markDeleted(row); }
    };
    ws.onclose = function (e) {
      wsOk = false;
      if (e.code === 4403 || e.code === 4404) return;  // not allowed here: stay on polling
      setTimeout(connect, retry); retry = Math.min(retry * 2, 30000);
    };
  }
  if (body) body.addEventListener('input', function () {
    var now = Date.now();
    if (now - lastTypingSent > 2500 && body.value.trim() && !(ctx && ctx.mode === 'edit')) {
      lastTypingSent = now;
      if (wsOk) wsSend({ t: 'typing' }); else post(d.typing);  // no socket: the typing mark goes over HTTP and polling clients pick it up
    }
  });
  setInterval(function () { if (!wsOk) poll(); }, 3000);
  setInterval(function () { if (wsOk) { wsSend({ t: 'ping' }); poll(); } }, 30000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { poll(); var rows = log.querySelectorAll('.m-row'); if (rows.length) wsSend({ t: 'read', upto: +rows[rows.length - 1].dataset.id }); } });

  // ---- first paint: jump to the first unread message (if any), otherwise to the newest
  log.querySelectorAll('.m-photo img').forEach(function (im) { im.addEventListener('load', function () { if (stickLoad) toBottom(); }); });
  var divider = document.getElementById('chat-new');
  if (divider) { stickLoad = false; divider.scrollIntoView({ block: 'start' }); } else { stickLoad = true; toBottom(); }
  updateFab();
  connect();
})();
