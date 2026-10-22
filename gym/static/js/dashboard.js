/* Member dashboard: numbers count up, the water glass fills without a page reload, the next class counts down. */
(function () {
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('.db-num[data-count]').forEach(function (el) {
    var to = +el.getAttribute('data-count') || 0, t0 = null;
    if (calm || to < 2) return;
    (function step(t) { t0 = t0 || t; var k = Math.min(1, (t - t0) / 900); el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); })(performance.now());
  });

  // water: +/− without reloading; a little splash, and confetti when the daily goal is reached
  var box = document.querySelector('[data-water]');
  if (box) {
    var n = box.querySelector('[data-water-n]'), fill = box.querySelector('.water-glass i'), goal = +box.dataset.goal || 8;
    var tok = (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || '';
    box.querySelectorAll('form').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var fd = new FormData(f);
        fetch(box.dataset.url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': tok, 'X-Requested-With': 'fetch' } })
          .then(function (r) { return r.json(); }).then(function (j) {
            if (!j.ok) return;
            var before = +n.textContent;
            n.textContent = j.glasses;
            fill.style.setProperty('--w', Math.min(100, Math.round(j.glasses / goal * 100)));
            box.classList.remove('splash'); void box.offsetWidth; box.classList.add('splash');
            if (before < goal && j.glasses >= goal && window.fzConfetti && !calm) window.fzConfetti();
          }).catch(function () { f.submit(); });
      });
    });
  }

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
