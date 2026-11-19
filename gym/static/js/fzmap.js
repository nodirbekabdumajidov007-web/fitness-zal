/* A small map without a library (the site's CSP allows only its own scripts): OpenStreetMap tiles as <img>, an SVG line for the road, HTML markers.
   var m = FZMap(el, {labels: {gym, client, courier}});  m.set({gym:[lat,lng], client:[lat,lng], courier:[lat,lng]|null, route:[[lat,lng],...]});
   Drag to move, +/- to zoom; fit() frames every point. Tiles carry the origin as referrer (the tile server asks for one). */
(function () {
  var TILE = 256, MAXZ = 18;
  function world(lat, lng, z) {
    var s = TILE * Math.pow(2, z), r = lat * Math.PI / 180;
    return [(lng + 180) / 360 * s, (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * s];
  }
  function unworld(x, y, z) {
    var s = TILE * Math.pow(2, z), n = Math.PI - 2 * Math.PI * y / s;
    return [180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))), x / s * 360 - 180];
  }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function svg(tag) { return document.createElementNS('http://www.w3.org/2000/svg', tag); }

  window.FZMap = function (box, opts) {
    opts = opts || {};
    var L = opts.labels || {};
    var st = { z: 13, c: [41.3, 69.25], pts: {}, route: null };
    box.classList.add('fzmap'); box.textContent = '';
    var tiles = el('div', 'fzm-tiles'), line = svg('svg'), pins = el('div', 'fzm-pins'), ctl = el('div', 'fzm-ctl');
    line.setAttribute('class', 'fzm-line');
    var plus = el('button', null, '+'), minus = el('button', null, '−'), fitb = el('button', null, '⤢');
    [plus, minus, fitb].forEach(function (b) { b.type = 'button'; ctl.appendChild(b); });
    plus.setAttribute('aria-label', '+'); minus.setAttribute('aria-label', '-'); fitb.setAttribute('aria-label', 'fit');
    var attr = el('a', 'fzm-attr', '© OpenStreetMap'); attr.href = 'https://www.openstreetmap.org/copyright'; attr.target = '_blank'; attr.rel = 'noopener noreferrer';
    [tiles, line, pins, ctl, attr].forEach(function (n) { box.appendChild(n); });

    function size() { return [box.clientWidth || 300, box.clientHeight || 240]; }
    function px(lat, lng, o) { var p = world(lat, lng, st.z); return [p[0] - o[0], p[1] - o[1]]; }

    function draw() {
      var sz = size(), cw = world(st.c[0], st.c[1], st.z), o = [cw[0] - sz[0] / 2, cw[1] - sz[1] / 2], n = Math.pow(2, st.z);
      tiles.textContent = '';
      var x0 = Math.floor(o[0] / TILE), x1 = Math.floor((o[0] + sz[0]) / TILE), y0 = Math.floor(o[1] / TILE), y1 = Math.floor((o[1] + sz[1]) / TILE);
      for (var ty = y0; ty <= y1; ty++) {
        if (ty < 0 || ty >= n) continue;
        for (var tx = x0; tx <= x1; tx++) {
          var im = document.createElement('img');
          im.alt = ''; im.draggable = false; im.decoding = 'async'; im.referrerPolicy = 'origin';
          im.src = 'https://tile.openstreetmap.org/' + st.z + '/' + (((tx % n) + n) % n) + '/' + ty + '.png';
          im.style.left = (tx * TILE - o[0]) + 'px'; im.style.top = (ty * TILE - o[1]) + 'px';
          tiles.appendChild(im);
        }
      }
      line.setAttribute('width', sz[0]); line.setAttribute('height', sz[1]); line.textContent = '';
      if (st.route && st.route.length > 1) {
        var pl = svg('polyline');
        pl.setAttribute('points', st.route.map(function (p) { var q = px(p[0], p[1], o); return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' '));
        pl.setAttribute('class', 'fzm-route' + (st.dashed ? ' dashed' : ''));
        line.appendChild(pl);
      }
      pins.textContent = '';
      ['gym', 'client', 'courier'].forEach(function (k) {
        var p = st.pts[k]; if (!p) return;
        var q = px(p[0], p[1], o), d = el('div', 'fzm-pin ' + k); d.style.left = q[0] + 'px'; d.style.top = q[1] + 'px';
        d.appendChild(el('span', null, L[k] || k)); pins.appendChild(d);
      });
    }

    function fit() {
      var list = [st.pts.gym, st.pts.client, st.pts.courier].filter(Boolean);
      if (!list.length) return;
      var sz = size();
      if (list.length === 1) { st.c = list[0]; st.z = 15; draw(); return; }
      var z = MAXZ - 1;
      for (; z > 2; z--) {
        var xs = list.map(function (p) { return world(p[0], p[1], z)[0]; }), ys = list.map(function (p) { return world(p[0], p[1], z)[1]; });
        if (Math.max.apply(null, xs) - Math.min.apply(null, xs) < sz[0] - 90 && Math.max.apply(null, ys) - Math.min.apply(null, ys) < sz[1] - 90) break;
      }
      var X = list.map(function (p) { return world(p[0], p[1], z)[0]; }), Y = list.map(function (p) { return world(p[0], p[1], z)[1]; });
      st.z = z; st.c = unworld((Math.max.apply(null, X) + Math.min.apply(null, X)) / 2, (Math.max.apply(null, Y) + Math.min.apply(null, Y)) / 2, z);
      draw();
    }

    function zoom(d) { st.z = Math.max(3, Math.min(MAXZ, st.z + d)); draw(); }
    plus.addEventListener('click', function () { zoom(1); });
    minus.addEventListener('click', function () { zoom(-1); });
    fitb.addEventListener('click', fit);
    var drag = null;
    box.addEventListener('pointerdown', function (e) { if (e.target.closest('.fzm-ctl')) return; drag = { x: e.clientX, y: e.clientY, c: world(st.c[0], st.c[1], st.z) }; box.setPointerCapture(e.pointerId); });
    box.addEventListener('pointermove', function (e) {
      if (!drag) return;
      st.c = unworld(drag.c[0] - (e.clientX - drag.x), drag.c[1] - (e.clientY - drag.y), st.z); draw();
    });
    ['pointerup', 'pointercancel'].forEach(function (n) { box.addEventListener(n, function () { drag = null; }); });
    if (window.ResizeObserver) new ResizeObserver(function () { draw(); }).observe(box);

    return {
      set: function (o) {
        var refit = false;  // a new gym / client / road frames the map again; a moving courier only redraws (so the member's own panning stays)
        if ('gym' in o) { st.pts.gym = o.gym || null; refit = true; }
        if ('client' in o) { st.pts.client = o.client || null; refit = true; }
        if ('courier' in o) { var first = !st.pts.courier; st.pts.courier = o.courier || null; refit = refit || (first && !!o.courier); }
        if ('route' in o) { st.route = o.route; st.dashed = !!o.dashed; refit = true; }
        if (refit) fit(); else draw();
      },
      fit: fit
    };
  };
})();
