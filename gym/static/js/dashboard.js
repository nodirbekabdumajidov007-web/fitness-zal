/* Member dashboard: numbers count up, the next class counts down. */
(function () {
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('.db-num[data-count]').forEach(function (el) {
    var to = +el.getAttribute('data-count') || 0, t0 = null;
    if (calm || to < 2) return;
    (function step(t) { t0 = t0 || t; var k = Math.min(1, (t - t0) / 900); el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); })(performance.now());
  });

  // next class countdown
  var cd = document.querySelector('[data-countdown]');
  if (cd && cd.dataset.countdown) {
    var at = new Date(cd.dataset.countdown).getTime(), labels = (cd.dataset.labels || 'd,h,m,s').split(',');
    (function tick() {
      var s = Math.max(0, Math.floor((at - Date.now()) / 1000));
      if (!s) { cd.textContent = cd.dataset.now; return; }
      var d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60), sec = s % 60;
      cd.innerHTML = '';
      [d, h, m, sec].forEach(function (val, i) {
        if (i === 0 && !d) return;
        var b = document.createElement('span'); b.className = 'cd-box';
        var v = document.createElement('b'); v.textContent = String(val).padStart(2, '0');
        var l = document.createElement('small'); l.textContent = labels[i] || '';
        b.appendChild(v); b.appendChild(l); cd.appendChild(b);
      });
      setTimeout(tick, 1000);
    })();
  }
})();
