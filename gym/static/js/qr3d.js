/* Member card: the QR's dark modules become isometric blocks that grow out of a base slab, breathe gently, and rise
   under the pointer. Three colour themes. Purely decorative: the flat 2D code (the default tab) is the one to scan. */
(function () {
  var cv = document.getElementById('qr3d');
  if (!cv) return;
  var rows = (cv.dataset.modules || '').split(',').filter(Boolean);
  var n = rows.length;
  if (!n) return;
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var THEMES = {
    fire: { top: '#ff6a4d', left: '#c0261a', right: '#8f1c13', floor: '#f6efe6', slabL: '#e2d7c7', slabR: '#cfc3b2', glow: 'rgba(240,80,61,.35)' },
    gold: { top: '#f6dc8a', left: '#c99a2e', right: '#8a6a1f', floor: '#f7f1e3', slabL: '#e6dcc4', slabR: '#d3c7aa', glow: 'rgba(226,184,74,.4)' },
    ice:  { top: '#c9ecff', left: '#5aa9e6', right: '#2f6fa8', floor: '#eef6fb', slabL: '#d6e5ef', slabR: '#bcd0de', glow: 'rgba(90,169,230,.35)' }
  };
  var theme = THEMES.fire;
  var dpr = Math.min(2, window.devicePixelRatio || 1), W = 520, H = 420;
  cv.width = W * dpr; cv.height = H * dpr;
  var ctx = cv.getContext('2d'); ctx.scale(dpr, dpr);
  var a = Math.min(220 / n, 9), ox = W / 2, oy = 70, slab = 10;
  var cells = [], c0 = (n - 1) / 2;
  for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
    var dark = rows[y][x] === '1';
    var hash = Math.abs(Math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1;
    var d = Math.hypot(x - c0, y - c0);
    cells.push({ x: x, y: y, dark: dark, target: dark ? 8 + hash * 16 + Math.max(0, 10 - d) : 0, delay: d * 38 + hash * 120 });
  }
  cells.sort(function (p, q) { return (p.x + p.y) - (q.x + q.y) || p.x - q.x; });  // painter's order: back to front

  function P(x, y, z) { return [ox + (x - y) * a, oy + (x + y) * a / 2 - z]; }
  function poly(pts, fill) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
  function easeBack(t) { var s = 1.7; t -= 1; return t * t * ((s + 1) * t + s) + 1; }

  var mouse = null, t0 = null, running = false;
  cv.addEventListener('pointermove', function (e) {
    var r = cv.getBoundingClientRect(), mx = (e.clientX - r.left) * W / r.width - ox, my = (e.clientY - r.top) * H / r.height - oy;
    mouse = { x: (mx / a + my / (a / 2)) / 2, y: (my / (a / 2) - mx / a) / 2 };
  });
  cv.addEventListener('pointerleave', function () { mouse = null; });

  function draw(now) {
    if (t0 === null) t0 = now;
    var el = calm ? 1e9 : now - t0;
    ctx.clearRect(0, 0, W, H);
    // soft glow under the slab
    var g = ctx.createRadialGradient(ox, oy + n * a / 2 + 40, 10, ox, oy + n * a / 2 + 40, n * a);
    g.addColorStop(0, theme.glow); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // base slab
    poly([P(0, n, 0), P(n, n, 0), P(n, n, -slab), P(0, n, -slab)], theme.slabL);
    poly([P(n, 0, 0), P(n, n, 0), P(n, n, -slab), P(n, 0, -slab)], theme.slabR);
    poly([P(0, 0, 0), P(n, 0, 0), P(n, n, 0), P(0, n, 0)], theme.floor);
    for (var i = 0; i < cells.length; i++) {
      var c = cells[i];
      if (!c.dark) continue;
      var k = Math.max(0, Math.min(1, (el - c.delay) / 700));
      var h = c.target * (k < 1 ? easeBack(k) : 1);
      if (k >= 1 && !calm) h += Math.sin(el / 650 + (c.x + c.y) / 3) * 1.4;
      if (mouse && !calm) { var dd = (c.x + .5 - mouse.x) * (c.x + .5 - mouse.x) + (c.y + .5 - mouse.y) * (c.y + .5 - mouse.y); h += 14 * Math.exp(-dd / 5); }
      if (h <= .2) continue;
      var x = c.x, y = c.y;
      poly([P(x, y + 1, h), P(x + 1, y + 1, h), P(x + 1, y + 1, 0), P(x, y + 1, 0)], theme.left);
      poly([P(x + 1, y, h), P(x + 1, y + 1, h), P(x + 1, y + 1, 0), P(x + 1, y, 0)], theme.right);
      poly([P(x, y, h), P(x + 1, y, h), P(x + 1, y + 1, h), P(x, y + 1, h)], theme.top);
    }
    if (running && !calm) requestAnimationFrame(draw);
  }

  function start() { if (running) return; running = true; t0 = null; requestAnimationFrame(draw); }
  function stop() { running = false; }

  document.querySelectorAll('.qr-mode [data-mode]').forEach(function (b) {
    b.addEventListener('click', function () {
      var m = b.dataset.mode;
      document.querySelectorAll('.qr-mode [data-mode]').forEach(function (x) { x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
      document.querySelectorAll('[data-view]').forEach(function (v) { v.hidden = v.dataset.view !== m; });
      if (m === '3d') start(); else stop();
    });
  });
  document.querySelectorAll('.qr-themes [data-theme]').forEach(function (b) {
    b.addEventListener('click', function () {
      theme = THEMES[b.dataset.theme] || THEMES.fire;
      document.querySelectorAll('.qr-themes [data-theme]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      t0 = null;  // grow again in the new colours
      if (calm || !running) { running = true; requestAnimationFrame(draw); if (calm) running = false; }
    });
  });
})();
