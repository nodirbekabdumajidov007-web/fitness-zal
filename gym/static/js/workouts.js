/* Workout page: a rest timer between sets (ring countdown, a soft beep and a vibration at the end). */
(function () {
  var box = document.querySelector('[data-timer]');
  if (!box) return;
  var left = box.querySelector('[data-tm-left]'), prog = box.querySelector('.tm-prog'), startBtn = box.querySelector('[data-tm-start]');
  var total = 90, remain = 90, timer = null, startLabel = startBtn.textContent;
  function fmt(s) { return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
  function draw() { left.textContent = fmt(remain); prog.style.strokeDashoffset = String(100 - remain / total * 100); }
  function beep() {
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)();
      [0, .25, .5].forEach(function (t) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
        g.gain.setValueAtTime(.0001, ctx.currentTime + t); g.gain.exponentialRampToValueAtTime(.3, ctx.currentTime + t + .02);
        g.gain.exponentialRampToValueAtTime(.0001, ctx.currentTime + t + .2);
        o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + .22);
      });
    } catch (e) {}
    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
  }
  function stop() { clearInterval(timer); timer = null; startBtn.textContent = startLabel; box.classList.remove('running'); }
  function start() {
    if (timer) { stop(); return; }
    if (!remain) remain = total;
    box.classList.add('running'); startBtn.textContent = '❚❚';
    timer = setInterval(function () {
      remain -= 1; draw();
      if (remain <= 0) { stop(); box.classList.add('ring'); setTimeout(function () { box.classList.remove('ring'); }, 1600); beep(); remain = total; draw(); }
    }, 1000);
  }
  box.querySelectorAll('[data-sec]').forEach(function (b) {
    b.addEventListener('click', function () {
      stop(); total = remain = +b.dataset.sec; draw();
      box.querySelectorAll('[data-sec]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
    });
  });
  startBtn.addEventListener('click', start);
  box.querySelector('[data-tm-reset]').addEventListener('click', function () { stop(); remain = total; draw(); });
  draw();
})();
