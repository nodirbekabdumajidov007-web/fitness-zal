/* Ready-made programs: client-side filters (remembered in localStorage) and the details dialog. */
(function () {
  var KEY = 'gym.programFilters', box = document.querySelector('[data-pfilters]'), grid = document.querySelector('[data-prog-grid]');
  if (!grid) return;
  var cards = [].slice.call(grid.querySelectorAll('.prog')), none = document.querySelector('[data-pf-none]');
  var count = document.querySelector('[data-pf-count]'), reset = document.querySelector('[data-pf-reset]');
  var state = { goal: '', level: '', days: '', place: '' };
  try { var saved = JSON.parse(localStorage.getItem(KEY) || '{}'); Object.keys(state).forEach(function (k) { if (typeof saved[k] === 'string') state[k] = saved[k]; }); } catch (e) {}

  function apply() {
    var shown = 0;
    cards.forEach(function (c) {
      var ok = Object.keys(state).every(function (k) { return !state[k] || c.dataset[k] === state[k]; });
      c.hidden = !ok; if (ok) shown++;
    });
    if (count) count.textContent = shown;
    if (none) none.hidden = shown > 0;
    if (reset) reset.hidden = !Object.keys(state).some(function (k) { return state[k]; });
    if (box) box.querySelectorAll('[data-pf]').forEach(function (g) {
      g.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.v === state[g.dataset.pf] ? 'true' : 'false'); });
    });
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }
  if (box) {
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-pf] button'); if (b) { state[b.parentNode.dataset.pf] = b.dataset.v; apply(); }
    });
    if (reset) reset.addEventListener('click', function () { Object.keys(state).forEach(function (k) { state[k] = ''; }); apply(); });
  }
  apply();

  grid.addEventListener('click', function (ev) {
    var open = ev.target.closest('[data-prog-open]');
    if (open) { var d = document.getElementById(open.dataset.progOpen); if (d && d.showModal) d.showModal(); return; }
    if (ev.target.closest('[data-prog-close]')) { var dlg = ev.target.closest('dialog'); if (dlg) dlg.close(); return; }
    if (ev.target.tagName === 'DIALOG') ev.target.close(); // a click on the backdrop
  });
})();
