/* Transfer page: the gym's card tilts toward the pointer with a moving glare and flips to its back (where the transfer comment
   is) when you reach for the comment; your own card's last 4 digits fill in live; "I've paid" spins, ticks, then sends. */
(function () {
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var stage = document.querySelector('[data-card3d]');
  var card = stage && stage.querySelector('.bankcard');
  var glare = card && card.querySelector('.bc-glare');
  function flip(on) { if (card) card.classList.toggle('flipped', on === undefined ? !card.classList.contains('flipped') : on); }
  document.querySelectorAll('[data-flip]').forEach(function (b) { b.addEventListener('click', function () { flip(); }); });
  document.querySelectorAll('[data-show-back]').forEach(function (el) {
    el.addEventListener('focus', function () { flip(true); });
    el.addEventListener('click', function () { flip(true); });
  });
  ['card-no', 'amount-no', 'sl4'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('focus', function () { flip(false); });
  });
  if (stage && card && !calm) {
    stage.addEventListener('pointermove', function (e) {
      var r = stage.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      stage.style.setProperty('--rx', (-y * 14).toFixed(2) + 'deg');
      stage.style.setProperty('--ry', (x * 18).toFixed(2) + 'deg');
      if (glare) { glare.style.left = (50 + x * 90) + '%'; glare.style.top = (50 + y * 90) + '%'; }
    });
    stage.addEventListener('pointerleave', function () { stage.style.setProperty('--rx', '0deg'); stage.style.setProperty('--ry', '0deg'); });
  }

  // your card: last 4 digits appear as you type
  var sl4 = document.getElementById('sl4'), view = document.getElementById('sl4-view');
  if (sl4 && view) sl4.addEventListener('input', function () {
    sl4.value = sl4.value.replace(/\D/g, '').slice(0, 4);
    view.textContent = (sl4.value + '····').slice(0, 4);
    view.parentNode.parentNode.classList.toggle('full', sl4.value.length === 4);
  });

  // the satisfying part: spinner, then a tick, then the form goes
  var f = document.querySelector('form[data-pay]');
  if (f) f.addEventListener('submit', function (e) {
    if (f.dataset.sent || !f.checkValidity()) return;
    var b = f.querySelector('.paybtn');
    if (!b || calm) return;
    e.preventDefault();
    f.dataset.sent = '1';
    b.classList.add('paying'); b.disabled = true;
    setTimeout(function () { b.classList.remove('paying'); b.classList.add('paid'); }, 900);
    setTimeout(function () { f.submit(); }, 1500);
  });
})();
