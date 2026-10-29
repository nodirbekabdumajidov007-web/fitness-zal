/* Calorie tracker: food search (server side: ~600 built-in foods in uz/ru/en plus the member's own), live preview for the entered grams,
   own foods (create / edit / delete) and free-text recognition. No external services. */
(function () {
  'use strict';
  var root = document.getElementById('add');
  var data = document.getElementById('calFoods');
  var search = document.getElementById('calSearch');
  var list = document.getElementById('calResults');
  var hidden = document.getElementById('calFood');
  var grams = document.getElementById('calGrams');
  var prev = document.getElementById('calPrev');
  var custom = document.getElementById('calCustom');
  var form = document.getElementById('calForm');
  var errBox = document.getElementById('calErr');
  var newBox = document.getElementById('calNew');
  var foodForm = document.getElementById('calFoodForm');
  var foodErr = document.getElementById('calFoodErr');
  var cancelBtn = document.getElementById('calFoodCancel');
  var mineUl = document.getElementById('calMine');
  if (!root || !search || !form || !data) return;
  var mine = [];
  try { mine = JSON.parse(data.textContent) || []; } catch (e) { mine = []; }
  var picked = null, active = -1, seq = 0, timer = 0, ctl = null, cache = {};

  function T(k) { return root.getAttribute('data-i18n-' + k) || ''; }
  function fill(tpl, o) { return tpl.replace(/%([gkpfc])/g, function (m, c) { return o[c]; }); }
  function num(v) { return Number((Math.round(v * 10) / 10).toFixed(1)); }
  function csrf() { return form.querySelector('[name=csrfmiddlewaretoken]').value; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function show(box, msg, ok) { box.textContent = msg || ''; box.hidden = !msg; box.className = 'cal-err' + (ok ? ' ok' : ''); }

  // ---------------------------------------------------------------- live preview
  function showPreview() {
    if (!picked) { prev.hidden = true; return; }
    var g = parseInt(grams.value, 10);
    prev.hidden = false;
    if (!(g > 0)) { prev.textContent = fill(T('row'), { k: num(picked.kcal) }); return; }
    var m = g / 100;
    prev.textContent = fill(T('live'), { g: g, k: num(picked.kcal * m), p: num(picked.p * m), f: num(picked.f * m), c: num(picked.c * m) });
  }

  function pick(f) {
    picked = f; hidden.value = f.id; search.value = f.name; clear(); show(errBox, '');
    grams.value = f.portion || 100;
    if (custom) custom.open = false;
    showPreview();
    grams.focus(); grams.select();
  }

  // ---------------------------------------------------------------- results list
  function clear() {
    list.hidden = true; list.textContent = ''; active = -1;
    search.setAttribute('aria-expanded', 'false'); search.removeAttribute('aria-activedescendant');
  }

  function openCreate(name) {
    clear(); newBox.open = true;
    var f = foodForm.elements;
    if (!f.pk.value) f.name.value = name || '';
    (f.name.value ? f.kcal : f.name).focus();
    newBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function setActive(i) {
    var opts = list.children;
    if (!opts.length) return;
    active = (i + opts.length) % opts.length;
    [].forEach.call(opts, function (li, k) { li.setAttribute('aria-selected', k === active ? 'true' : 'false'); });
    search.setAttribute('aria-activedescendant', opts[active].id);
    opts[active].scrollIntoView({ block: 'nearest' });
  }

  function render(items, q) {
    list.textContent = ''; active = -1;
    items.forEach(function (f, i) {
      var li = el('li'); li.id = 'calOpt' + i; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
      var a = el('span', 'cal-opt-name'); a.appendChild(document.createTextNode(f.name));
      if (f.mine) a.appendChild(el('em', 'cal-badge', T('mine')));
      var portion = f.portion || 100;
      var b = el('small', null, fill(T('row'), { k: num(f.kcal) }) + ' · ' + fill(T('portion'), { g: portion, k: num(f.kcal * portion / 100) }));
      li.appendChild(a); li.appendChild(b);
      li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(f); });
      li.addEventListener('mousemove', function () { if (active !== i) setActive(i); });
      list.appendChild(li);
    });
    if (!items.length && q.trim()) {
      var li = el('li', 'cal-none'); li.id = 'calOptNone'; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
      li.appendChild(el('span', null, T('none')));
      li.appendChild(el('small', null, '＋ ' + q.trim().slice(0, 60)));
      li.addEventListener('mousedown', function (e) { e.preventDefault(); openCreate(q.trim()); });
      list.appendChild(li);
    }
    list.hidden = !list.children.length;
    search.setAttribute('aria-expanded', list.hidden ? 'false' : 'true');
  }

  function query(q) {
    var key = q.trim().toLowerCase();
    if (cache[key]) { render(cache[key], q); return; }
    var mySeq = ++seq;
    if (ctl && ctl.abort) ctl.abort();
    ctl = window.AbortController ? new AbortController() : null;
    fetch(root.getAttribute('data-search') + '?q=' + encodeURIComponent(q.trim()), {
      credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' }, signal: ctl ? ctl.signal : undefined })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (mySeq !== seq || document.activeElement !== search) return;
        if (!j.ok) { show(errBox, j.error || T('net')); return; }
        show(errBox, '');
        if (Object.keys(cache).length > 60) cache = {};
        cache[key] = j.items; render(j.items, q);
      })
      .catch(function (e) { if (e && e.name === 'AbortError') return; if (mySeq === seq) show(errBox, T('net')); });
  }

  search.addEventListener('input', function () {
    picked = null; hidden.value = ''; showPreview();
    clearTimeout(timer);
    if (!search.value.trim()) { query(''); return; }
    timer = setTimeout(function () { query(search.value); }, 140);
  });
  search.addEventListener('focus', function () { if (!picked) query(search.value); });
  search.addEventListener('blur', function () { setTimeout(clear, 150); });
  search.addEventListener('keydown', function (e) {
    var open = !list.hidden && list.children.length;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!open) { query(search.value); return; }
      e.preventDefault(); setActive(active < 0 ? (e.key === 'ArrowDown' ? 0 : -1) : active + (e.key === 'ArrowDown' ? 1 : -1));
    } else if (e.key === 'Enter' && open) {
      e.preventDefault();
      list.children[active < 0 ? 0 : active].dispatchEvent(new MouseEvent('mousedown', { cancelable: true }));
    } else if (e.key === 'Escape') { clear(); }
  });
  grams.addEventListener('input', showPreview);

  form.addEventListener('submit', function (e) {
    // a food from the list needs no typed numbers; without one the quick-add block must have a name and calories
    if (picked) return;
    var nm = form.elements['name'], kc = form.elements['kcal'];
    if (nm.value.trim() && kc.value !== '') return;
    e.preventDefault();
    if (custom && custom.open) { (nm.value.trim() ? kc : nm).focus(); return; }
    show(errBox, T('pick'));
    search.focus();
  });

  // ---------------------------------------------------------------- the member's own foods
  function renderMine() {
    mine.sort(function (a, b) { return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1; });
    mineUl.textContent = '';
    var delBase = root.getAttribute('data-del');
    mine.forEach(function (f) {
      var li = el('li'); li.setAttribute('data-pk', f.pk);
      var box = el('span'); box.appendChild(el('b', null, f.name));
      box.appendChild(el('small', 'muted num', fill(T('row'), { k: num(f.kcal) }) + ' · ' + f.p + '/' + f.f + '/' + f.c + ' · ' + f.portion + ' g'));
      var ed = el('button', 'btn small', T('edit')); ed.type = 'button'; ed.setAttribute('data-edit', f.pk);
      var del = el('form'); del.method = 'post'; del.action = delBase.replace('/0/', '/' + f.pk + '/');
      var tok = el('input'); tok.type = 'hidden'; tok.name = 'csrfmiddlewaretoken'; tok.value = csrf();
      var x = el('button', 'cal-x', '×'); x.type = 'submit'; x.setAttribute('aria-label', T('remove')); x.title = T('remove');
      del.appendChild(tok); del.appendChild(x);
      li.appendChild(box); li.appendChild(ed); li.appendChild(del); mineUl.appendChild(li);
    });
    document.getElementById('calMineN').textContent = mine.length;
    document.getElementById('calMineEmpty').hidden = mine.length > 0;
    cache = {};
  }

  mineUl.addEventListener('click', function (e) {
    var b = e.target.closest('[data-edit]');
    if (!b) return;
    var f = mine.filter(function (m) { return String(m.pk) === b.getAttribute('data-edit'); })[0];
    if (!f) return;
    var fe = foodForm.elements;
    fe.pk.value = f.pk; fe.name.value = f.name; fe.kcal.value = f.kcal; fe.protein.value = f.p; fe.fat.value = f.f; fe.carbs.value = f.c;
    fe.portion_g.value = f.portion;
    cancelBtn.hidden = false; show(foodErr, ''); newBox.open = true;
    newBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); fe.name.focus();
  });
  mineUl.addEventListener('submit', function (e) { if (!window.confirm(T('confirm'))) e.preventDefault(); });

  function resetFoodForm() { foodForm.reset(); foodForm.elements.pk.value = ''; cancelBtn.hidden = true; }
  cancelBtn.addEventListener('click', function () { resetFoodForm(); show(foodErr, ''); newBox.open = false; });

  foodForm.addEventListener('submit', function (e) {
    e.preventDefault();
    var btn = foodForm.querySelector('button[type=submit]'); btn.disabled = true; show(foodErr, '');
    fetch(foodForm.action, { method: 'POST', body: new FormData(foodForm), credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        btn.disabled = false;
        if (!j.ok) { show(foodErr, j.error || T('net')); return; }
        mine = mine.filter(function (m) { return m.pk !== j.food.pk; }); mine.push(j.food); renderMine();
        resetFoodForm(); newBox.open = false; pick(j.food);
        show(errBox, j.message, true);
      })
      .catch(function () { btn.disabled = false; show(foodErr, T('net')); });
  });
  renderMine();

  var aiMeal = document.getElementById('calAiMeal');
  [].forEach.call(form.querySelectorAll('input[name=meal]'), function (r) {
    r.addEventListener('change', function () { if (aiMeal) aiMeal.value = r.value; });
  });

  var ai = document.getElementById('calAi');
  if (ai) {
    ai.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = ai.querySelector('button'), err = document.getElementById('calAiErr'), label = btn.textContent;
      btn.disabled = true; btn.textContent = btn.getAttribute('data-busy'); err.hidden = true;
      function fail(msg) { err.textContent = msg || 'Error'; err.hidden = false; btn.disabled = false; btn.textContent = label; }
      var token = ai.querySelector('[name=csrfmiddlewaretoken]').value, found = document.getElementById('calAiFound');
      function reset() { btn.disabled = false; btn.textContent = label; }
      fetch(ai.action, { method: 'POST', body: new FormData(ai), credentials: 'same-origin',
        headers: { 'X-CSRFToken': token, 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.ok) return fail(j.error);
          // show what was recognised (grams can be edited), then add each item through the normal add endpoint
          found.hidden = false; found.textContent = '';
          var h = document.createElement('b'); h.textContent = ai.getAttribute('data-found'); found.appendChild(h);
          var rows = j.items.map(function (it) {
            var row = document.createElement('div'); row.className = 'cal-found-row';
            var name = document.createElement('span'); name.textContent = it.name + ' \u00b7 ' + it.kcal + ' kcal';
            var g = document.createElement('input'); g.type = 'number'; g.min = 1; g.max = 5000; g.value = it.grams; g.setAttribute('aria-label', 'g');
            row.appendChild(name); row.appendChild(g); found.appendChild(row);
            return { it: it, input: g };
          });
          var add = document.createElement('button'); add.type = 'button'; add.className = 'btn primary'; add.textContent = ai.getAttribute('data-addall');
          add.addEventListener('click', function () {
            add.disabled = true;
            var meal = ai.querySelector('[name=meal]').value, day = ai.querySelector('[name=d]').value;
            rows.reduce(function (p, r) {
              return p.then(function () {
                var body = new FormData(); body.append('food', r.it.idx); body.append('grams', r.input.value); body.append('meal', meal); body.append('d', day);
                return fetch(ai.getAttribute('data-add'), { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': token, 'X-Requested-With': 'fetch' } });
              });
            }, Promise.resolve()).then(function () { location.reload(); }).catch(function () { add.disabled = false; fail(); });
          });
          found.appendChild(add); reset();
        })
        .catch(function () { fail(); });
    });
  }
})();
