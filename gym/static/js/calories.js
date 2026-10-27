/* Calorie tracker: food search over the built-in table (no network), per-portion preview, AI estimate via fetch. */
(function () {
  'use strict';
  var data = document.getElementById('calFoods');
  var search = document.getElementById('calSearch');
  var list = document.getElementById('calResults');
  var hidden = document.getElementById('calFood');
  var grams = document.getElementById('calGrams');
  var prev = document.getElementById('calPrev');
  var custom = document.getElementById('calCustom');
  var form = document.getElementById('calForm');
  if (!data || !search || !form) return;
  var foods = JSON.parse(data.textContent);
  var picked = null;

  function norm(s) { return (s || '').toLowerCase().replace(/[ʻʼ’`']/g, ''); }
  function clear() { list.hidden = true; list.innerHTML = ''; }

  function showPreview() {
    if (!picked) { prev.hidden = true; return; }
    prev.hidden = false;
    prev.textContent = prev.getAttribute('data-tpl').replace('%k', picked.kcal).replace('%p', picked.p).replace('%f', picked.f).replace('%c', picked.c);
  }

  function pick(f) {
    picked = f; hidden.value = f.i; search.value = f.name; clear(); showPreview();
    if (custom) custom.open = false;
    grams.focus(); grams.select();
  }

  function render(q) {
    var n = norm(q);
    var rows = foods.filter(function (f) { return !n || norm(f.name).indexOf(n) !== -1; }).slice(0, 12);
    list.innerHTML = '';
    rows.forEach(function (f) {
      var li = document.createElement('li');
      li.setAttribute('role', 'option');
      var a = document.createElement('span'); a.textContent = f.name;
      var b = document.createElement('small'); b.textContent = f.kcal + ' kcal / 100 g';
      li.appendChild(a); li.appendChild(b);
      li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(f); });
      list.appendChild(li);
    });
    list.hidden = !rows.length;
  }

  search.addEventListener('input', function () { picked = null; hidden.value = ''; showPreview(); render(search.value); });
  search.addEventListener('focus', function () { render(search.value); });
  search.addEventListener('blur', function () { setTimeout(clear, 120); });
  search.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !list.hidden && list.firstChild) { e.preventDefault(); list.firstChild.dispatchEvent(new MouseEvent('mousedown')); }
    if (e.key === 'Escape') clear();
  });
  grams.addEventListener('input', showPreview);

  form.addEventListener('submit', function (e) {
    // a food from the list needs no typed numbers; without one the custom block must be open and filled
    if (!picked && custom) {
      custom.open = true;
      var nm = form.elements['name'], kc = form.elements['kcal'];
      if (!nm.value.trim() || kc.value === '') { e.preventDefault(); (nm.value.trim() ? kc : nm).focus(); }
    }
  });
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
      fetch(ai.action, { method: 'POST', body: new FormData(ai), credentials: 'same-origin',
        headers: { 'X-CSRFToken': ai.querySelector('[name=csrfmiddlewaretoken]').value, 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (j) { if (j.ok) location.reload(); else fail(j.error); })
        .catch(function () { fail(); });
    });
  }
})();
