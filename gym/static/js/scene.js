/* Sign-in pages: the night-city layers drift with the mouse (or slowly by themselves on phones), the glass card tilts toward
   the pointer with a moving glare, and pressing the button "walks through" it: the card and the city rush toward you before
   the form is sent. Without this file the page is a normal form on a still picture. */
(function () {
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scene = document.querySelector('[data-scene]');
  var tilt = document.querySelector('[data-tilt]');
  if (!scene || reduce) return;
  var layers = [].slice.call(scene.querySelectorAll('[data-depth]'));
  var card = tilt && tilt.querySelector('.glass');
  var glare = card && card.querySelector('.glare');
  var tx = 0, ty = 0, x = 0, y = 0, lastMove = 0;

  function aim(nx, ny) { tx = Math.max(-1, Math.min(1, nx)); ty = Math.max(-1, Math.min(1, ny)); lastMove = performance.now(); }
  addEventListener('pointermove', function (e) {
    if (e.pointerType === 'touch') return;
    aim(e.clientX / innerWidth * 2 - 1, e.clientY / innerHeight * 2 - 1);
  }, { passive: true });
  addEventListener('deviceorientation', function (e) {  // phones that allow it without asking (most Android)
    if (e.gamma == null) return;
    aim(e.gamma / 25, (e.beta - 45) / 25);
  }, { passive: true });

  function frame(t) {
    if (t - lastMove > 2500) { tx = Math.sin(t / 3200) * 0.45; ty = Math.cos(t / 4100) * 0.25; }  // idle: a slow breathing drift
    x += (tx - x) * 0.07; y += (ty - y) * 0.07;
    for (var i = 0; i < layers.length; i++) {
      var d = +layers[i].getAttribute('data-depth');
      layers[i].style.transform = 'translate3d(' + (-x * d * 40).toFixed(2) + 'px,' + (-y * d * 18).toFixed(2) + 'px,0)';
    }
    if (card && !card.classList.contains('warp')) {
      card.style.transform = 'rotateY(' + (x * 9).toFixed(2) + 'deg) rotateX(' + (-y * 7).toFixed(2) + 'deg)';
      if (glare) { glare.style.left = (50 + x * 45).toFixed(1) + '%'; glare.style.top = (30 + y * 40).toFixed(1) + '%'; }
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

})();

/* Sign-in forms (outside the motion block, so it works with reduced motion too): the form is sent at once, the button shows a
   spinner and ignores a second press. No artificial delay: signing in should feel instant. */
(function () {
  document.querySelectorAll('form[data-warp]').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      if (f.dataset.sent) { e.preventDefault(); return; }
      f.dataset.sent = '1';
      var btn = e.submitter || f.querySelector('.portal');
      if (btn && btn.classList.contains('portal')) btn.classList.add('loading');
    });
  });
  // back to the page with the browser's Back button: the button is usable again
  addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    document.querySelectorAll('form[data-warp]').forEach(function (f) { delete f.dataset.sent; });
    document.querySelectorAll('.portal.loading').forEach(function (b) { b.classList.remove('loading'); });
  });
})();
