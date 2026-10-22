/* Home page motion: the hero clip plays once and freezes, the headline rises word by word, the hero sinks into a card
   as you scroll, sections slide in and numbers count up. Without this file (or with reduced motion) everything is simply shown. */
(function () {
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('[data-cine]');
  if (!hero) return;

  // headline: one span per word so each can rise on its own
  var h = hero.querySelector('[data-split]');
  if (h && !reduce) {
    var words = h.textContent.trim().split(/\s+/);
    h.textContent = '';
    words.forEach(function (w, i) {
      var o = document.createElement('span'); o.className = 'w';
      var s = document.createElement('span'); s.textContent = w; s.style.animationDelay = (0.25 + i * 0.12) + 's';
      o.appendChild(s); h.appendChild(o); h.appendChild(document.createTextNode(' '));
    });
  }

  // the clip: no loop, so it stops on its last frame; then the side cards come in
  var v = hero.querySelector('video');
  function landed() { hero.classList.add('landed'); }
  if (v) {
    v.addEventListener('ended', landed);
    v.addEventListener('error', landed);
    var p = v.play && v.play();
    if (p && p.catch) p.catch(landed);  // autoplay blocked: show the first frame as a still
    setTimeout(landed, 12000);
  } else {
    setTimeout(landed, reduce ? 0 : 1600);
  }

  // scroll: the hero shrinks into a rounded card and the giant word drifts
  if (!reduce) {
    var ticking = false;
    function onScroll() {
      if (ticking) return; ticking = true;
      requestAnimationFrame(function () {
        var p = Math.min(1, Math.max(0, window.scrollY / (hero.offsetHeight * 0.8)));
        hero.style.setProperty('--p', p.toFixed(3));
        ticking = false;
      });
    }
    addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }

  // sections slide in when they reach the screen (only those still below it, so nothing visible ever blinks)
  var items = [].slice.call(document.querySelectorAll('.reveal'));
  if ('IntersectionObserver' in window && !reduce) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.remove('pre'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el, i) {
      if (el.getBoundingClientRect().top > innerHeight) { el.classList.add('pre'); el.style.transitionDelay = (i % 3) * 0.08 + 's'; io.observe(el); }
    });
  }

  // numbers count up once
  var nums = [].slice.call(document.querySelectorAll('[data-count]'));
  function count(el) {
    var to = +el.getAttribute('data-count') || 0, t0 = null;
    if (reduce || to < 2) return;
    function step(t) { t0 = t0 || t; var k = Math.min(1, (t - t0) / 1200); el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  if ('IntersectionObserver' in window) {
    var co = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { count(e.target); co.unobserve(e.target); } }); });
    nums.forEach(function (n) { co.observe(n); });
  }
})();
