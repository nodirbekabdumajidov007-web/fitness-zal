/* Front desk: tabs over the work queues (remembered between visits) and a live clock. Without JS every queue is simply shown. */
(function () {
  var tabs = document.querySelector('[data-tabs]');
  if (tabs) {
    var panels = document.querySelectorAll('[data-panel]');
    function pick(name) {
      tabs.querySelectorAll('[data-tab]').forEach(function (b) { b.setAttribute('aria-selected', b.dataset.tab === name ? 'true' : 'false'); });
      panels.forEach(function (p) { p.hidden = p.dataset.panel !== name; });
      try { localStorage.setItem('fz-desk-tab', name); } catch (e) {}
      var on = tabs.querySelector('[aria-selected="true"]');
      if (on && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = on.offsetLeft - (tabs.clientWidth - on.offsetWidth) / 2;
    }
    document.querySelectorAll('[data-goto]').forEach(function (k) {
      k.addEventListener('click', function () {
        var t = tabs.querySelector('[data-tab="' + k.dataset.goto + '"]');
        if (t) { t.click(); tabs.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
    tabs.addEventListener('click', function (e) { var b = e.target.closest('[data-tab]'); if (b) pick(b.dataset.tab); });
    var saved = null;
    try { saved = localStorage.getItem('fz-desk-tab'); } catch (e) {}
    // open the first queue that needs attention, unless the receptionist chose one before
    var hot = tabs.querySelector('[data-tab] i.hot');
    pick(saved && tabs.querySelector('[data-tab="' + saved + '"]') ? saved : (hot ? hot.parentNode.dataset.tab : 'pay'));
  }
  var clock = document.querySelector('[data-clock]');
  if (clock) setInterval(function () { var d = new Date(); clock.textContent = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }, 10000);
})();
