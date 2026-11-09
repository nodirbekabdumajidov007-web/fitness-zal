/* AI Analitika page: KPI cards with sparklines, SVG charts (line/area, donuts, bars, heatmap), insights and the bulk reminder.
   Data arrives as JSON (first paint from the page itself, later from /analytics/api/all/). All text goes in with textContent. */
(function () {
  'use strict';
  var root = document.getElementById('an');
  if (!root) return;
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var data = JSON.parse(document.getElementById('an-data').textContent);
  var period = JSON.parse(document.getElementById('an-period').textContent);
  var COLORS = ['var(--an-1)', 'var(--an-2)', 'var(--an-3)', 'var(--an-4)', 'var(--an-5)', 'var(--an-6)'];
  var KPI_COLORS = { revenue: 1, new_members: 3, active: 4, visits: 5, avg_check: 2, shop: 6, renewal: 3, frozen: 4 };
  var ICONS = {
    trend: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>', alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    wallet: '<path d="M19 7V5a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    'user-plus': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/>',
    login: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5M15 12H3"/>', star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>', dumbbell: '<path d="M6.5 6.5v11M17.5 6.5v11M3 9v6M21 9v6M6.5 12h11"/>',
    package: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
    'shield-x': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="m9.5 9.5 5 5M14.5 9.5l-5 5"/>', bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    bag: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18M16 10a4 4 0 0 1-8 0"/>',
    'user-check': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m16 11 2 2 4-4"/>',
    check: '<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/>', arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>', send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
    sparkles: '<path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>'
  };

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function s(tag, attrs) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }
  function icon(name) { var w = h('span'); w.innerHTML = '<svg class="ai" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || ICONS.sparkles) + '</svg>'; return w.firstChild; }
  function fmt(n) { return String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  function short(n) { n = n || 0; if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace('.0', '') + ' mln'; if (n >= 1e3) return Math.round(n / 1e3) + ' ming'; return String(Math.round(n * 10) / 10); }
  function el(id) { return document.getElementById(id); }
  function body(id) { return el(id).querySelector('.an-body'); }
  function csrf() { var t = root.querySelector('[name=csrfmiddlewaretoken]'); return t ? t.value : ''; }
  function empty(box, msg) { box.textContent = ''; box.appendChild(h('div', 'an-empty', msg || "Bu davrda ma'lumot yo'q.")); }

  // ---------- tooltip (hover on desktop, tap on phones) ----------
  var tip = h('div', 'an-tip'); tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip);
  function tipShow(t, x, y) {
    tip.textContent = '';
    String(t.dataset.tip).split('\n').forEach(function (line, i) {
      var d = i === 0 ? h('b') : h('div'); var c = t.dataset.c;
      if (i > 0 && line.charAt(0) === '*' && c) { var sw = h('i'); sw.style.setProperty('--c', c); d.appendChild(sw); line = line.slice(1); }
      d.appendChild(document.createTextNode(line)); tip.appendChild(d);
    });
    var r = tip.getBoundingClientRect(), nx = Math.min(window.innerWidth - r.width - 8, Math.max(8, x + 14)), ny = y - r.height - 12;
    if (ny < 8) ny = y + 18;
    tip.style.left = nx + 'px'; tip.style.top = ny + 'px'; tip.classList.add('on');
  }
  function tipHide() { tip.classList.remove('on'); }
  root.addEventListener('pointermove', function (e) { var t = e.target.closest('[data-tip]'); if (t && e.pointerType !== 'touch') tipShow(t, e.clientX, e.clientY); else if (e.pointerType !== 'touch') tipHide(); });
  root.addEventListener('pointerleave', tipHide);
  root.addEventListener('click', function (e) { var t = e.target.closest('[data-tip]'); if (t && (e.pointerType === 'touch' || !window.matchMedia('(hover:hover)').matches)) tipShow(t, e.clientX, e.clientY); else if (!t) tipHide(); });
  window.addEventListener('scroll', tipHide, { passive: true });

  // ---------- accessible table fallback ----------
  function fallback(box, cols, rows, title) {
    var d = h('details', 'an-fallback'), sm = h('summary', '', title || 'Jadval ko\'rinishi');
    var wrap = h('div', 'an-fallback-wrap'), t = h('table'), hd = h('tr');
    cols.forEach(function (c) { var th = h('th', '', c); th.scope = 'col'; hd.appendChild(th); });
    t.appendChild(hd);
    rows.forEach(function (r) { var tr = h('tr'); r.forEach(function (c) { tr.appendChild(h('td', '', c)); }); t.appendChild(tr); });
    wrap.appendChild(t); d.appendChild(sm); d.appendChild(wrap); box.appendChild(d);
  }

  // ---------- sparkline ----------
  function spark(values, color) {
    var box = h('div', 'an-spark');
    if (!values || values.length < 2 || !values.some(function (v) { return v > 0; })) return box;
    var w = 100, hh = 36, max = Math.max.apply(null, values), min = Math.min.apply(null, values), span = max - min || 1;
    var pts = values.map(function (v, i) { return [i / (values.length - 1) * w, hh - 4 - (v - min) / span * (hh - 10)]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join('');
    var svg = s('svg', { viewBox: '0 0 100 36', preserveAspectRatio: 'none', 'aria-hidden': 'true' });
    svg.appendChild(s('path', { d: d + 'L100 36L0 36Z', fill: color, 'fill-opacity': '.14', class: 'an-area' }));
    var line = s('path', { d: d, fill: 'none', stroke: color, 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' });
    svg.appendChild(line); box.appendChild(svg); return box;
  }

  // ---------- KPI cards ----------
  function countUp(node, to, f) {
    if (reduce || to == null || to === 0) { node.textContent = f(to); return; }
    var t0 = null, dur = 700;
    function step(t) { if (t0 == null) t0 = t; var k = Math.min(1, (t - t0) / dur); k = 1 - Math.pow(1 - k, 3); node.textContent = f(to * k); if (k < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  function deltaChip(c) {
    var chip = h('span', 'an-delta');
    if (c.delta == null) {
      if (c.value && !c.prev && c.delta_kind === 'pct') { chip.textContent = 'yangi'; chip.title = "Oldingi davrda yo'q edi"; } else { chip.textContent = '—'; chip.title = "Solishtirish uchun ma'lumot yo'q"; }
      return chip;
    }
    var up = c.delta > 0, zero = c.delta === 0, unit = c.delta_kind === 'pp' ? ' p.p.' : '%';
    chip.textContent = (zero ? '' : up ? '▲ +' : '▼ ') + (zero ? '0' : String(c.delta).replace('.', ',')) + unit;
    if (!zero && c.up_is_good !== null) chip.classList.add((up === !!c.up_is_good) ? 'up' : 'down');
    chip.title = 'Oldingi davrga nisbatan';
    chip.setAttribute('aria-label', (zero ? "o'zgarmagan" : up ? "oshgan" : "kamaygan") + ' ' + String(Math.abs(c.delta)).replace('.', ',') + unit);
    return chip;
  }
  function renderKpis() {
    var box = el('an-kpis'); box.textContent = '';
    data.kpis.cards.forEach(function (c, i) {
      var card = h('article', 'an-kpi'); card.style.setProperty('--i', i); card.style.setProperty('--c', COLORS[(KPI_COLORS[c.key] || 1) - 1]);
      var top = h('div', 'an-kpi-top'); top.appendChild(h('span', 'an-kpi-label', c.label)); top.appendChild(deltaChip(c)); card.appendChild(top);
      var val = h('div', 'an-kpi-val'), num = h('span'); val.appendChild(num);
      if (c.value == null) num.textContent = '—'; else countUp(num, c.value, function (v) { return c.fmt === 'pct' ? Math.round(v) + '%' : fmt(v); });
      if (c.unit && c.fmt === 'money') val.appendChild(h('small', '', c.unit));
      card.appendChild(val);
      card.appendChild(spark(c.spark, COLORS[(KPI_COLORS[c.key] || 1) - 1]));
      var foot = c.prev == null ? c.hint : 'Oldingi: ' + (c.fmt === 'pct' ? c.prev + '%' : fmt(c.prev)) + (c.unit && c.fmt === 'money' ? ' ' + c.unit : '');
      card.appendChild(h('div', 'an-kpi-foot', foot)); card.title = c.hint;
      box.appendChild(card);
    });
  }

  // ---------- insights ----------
  function renderInsights() {
    var box = el('an-insights'); box.textContent = '';
    data.insights.rows.forEach(function (it, i) {
      var c = h('div', 'an-ins ' + it.tone); c.style.setProperty('--i', i);
      var ic = h('span', 'an-ins-ic'); ic.appendChild(icon(it.icon)); c.appendChild(ic);
      c.appendChild(h('b', '', it.title)); c.appendChild(h('p', '', it.text));
      if (it.cta && it.cta.url) { var a = h('a', 'an-cta', it.cta.label); a.href = it.cta.url; a.appendChild(icon('arrow')); c.appendChild(a); }
      else if (it.action && it.action.name === 'remind') { var b = h('button', 'an-cta', it.action.label); b.type = 'button'; b.appendChild(icon('send')); b.addEventListener('click', function () { remind(null, b); }); c.appendChild(b); }
      box.appendChild(c);
    });
  }

  // ---------- revenue: stacked area with hover crosshair ----------
  function renderRevenue() {
    var box = body('c-revenue'), d = data.revenue; box.textContent = '';
    if (!d.total) return empty(box, "Bu davrda to'langan to'lov yo'q.");
    var rows = d.rows, W = Math.max(280, box.clientWidth || 640), H = W < 480 ? 220 : 270, m = { l: 46, r: 12, t: 12, b: 26 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
    var max = Math.max.apply(null, rows.map(function (r) { return r.total; })) || 1, n = rows.length;
    var top = niceMax(max), x = function (i) { return m.l + (n === 1 ? iw / 2 : i / (n - 1) * iw); }, y = function (v) { return m.t + ih - v / top * ih; };
    var svg = s('svg', { class: 'an-chart', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': "Tushum dinamikasi: jami " + fmt(d.total) + " so'm" });
    for (var g = 0; g <= 4; g++) { var gv = top / 4 * g, gy = y(gv); svg.appendChild(s('line', { x1: m.l, x2: W - m.r, y1: gy, y2: gy, class: 'g' })); var tx = s('text', { x: m.l - 6, y: gy + 4, 'text-anchor': 'end' }); tx.textContent = short(gv); svg.appendChild(tx); }
    var step = Math.ceil(n / Math.max(2, Math.floor(iw / 56)));
    rows.forEach(function (r, i) { if (i % step === 0) { var t = s('text', { x: x(i), y: H - 6, 'text-anchor': 'middle' }); t.textContent = r.label; svg.appendChild(t); } });
    function path(vals) { return vals.map(function (v, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); }).join(''); }
    var mem = rows.map(function (r) { return r.membership; }), tot = rows.map(function (r) { return r.total; });
    var base = 'L' + x(n - 1).toFixed(1) + ' ' + y(0) + 'L' + x(0).toFixed(1) + ' ' + y(0) + 'Z';
    svg.appendChild(s('path', { d: path(tot) + base, fill: COLORS[1], 'fill-opacity': '.22', class: 'an-area' }));
    svg.appendChild(s('path', { d: path(mem) + base, fill: COLORS[0], 'fill-opacity': '.28', class: 'an-area' }));
    [[tot, COLORS[1]], [mem, COLORS[0]]].forEach(function (p) {
      var l = s('path', { d: path(p[0]), fill: 'none', stroke: p[1], 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', class: 'an-line', pathLength: 1 }); l.style.setProperty('--len', 1); svg.appendChild(l);
    });
    var cross = s('line', { y1: m.t, y2: m.t + ih, stroke: 'var(--fz-muted)', 'stroke-dasharray': '3 3', opacity: 0 }); svg.appendChild(cross);
    var dot = s('circle', { r: 4.5, fill: COLORS[1], stroke: 'var(--fz-card)', 'stroke-width': 2, opacity: 0 }); svg.appendChild(dot);
    var hit = s('rect', { x: m.l, y: m.t, width: iw, height: ih, fill: 'transparent' }); svg.appendChild(hit);
    function at(clientX) {
      var rect = svg.getBoundingClientRect(), px = (clientX - rect.left) * (W / rect.width), i = Math.max(0, Math.min(n - 1, Math.round(n === 1 ? 0 : (px - m.l) / iw * (n - 1))));
      return i;
    }
    function hover(e) {
      var i = at(e.clientX), r = rows[i]; cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('opacity', 1); dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(r.total)); dot.setAttribute('opacity', 1);
      hit.dataset.tip = r.label + '\n*Abonement: ' + fmt(r.membership) + " so'm\n*Do'kon: " + fmt(r.shop) + " so'm\n*Jami: " + fmt(r.total) + " so'm"; hit.dataset.c = COLORS[1];
    }
    hit.addEventListener('pointermove', hover); hit.addEventListener('pointerdown', hover);
    hit.addEventListener('pointerleave', function () { cross.setAttribute('opacity', 0); dot.setAttribute('opacity', 0); });
    box.appendChild(svg);
    var leg = h('ul', 'an-leg'); [['Abonement', 0, d.membership], ["Do'kon", 1, d.shop]].forEach(function (a) { var li = h('li'), i = h('i'); i.style.setProperty('--c', COLORS[a[1]]); li.appendChild(i); li.appendChild(document.createTextNode(a[0] + ': ' + fmt(a[2]) + " so'm")); leg.appendChild(li); });
    box.appendChild(leg);
    fallback(box, ['Sana', 'Abonement', "Do'kon", 'Jami'], rows.map(function (r) { return [r.label, fmt(r.membership), fmt(r.shop), fmt(r.total)]; }));
  }
  function niceMax(v) { var p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }

  // ---------- donut ----------
  function donut(id, rows, unit, centerLabel, fmtv) {
    var box = body(id); box.textContent = '';
    var total = rows.reduce(function (a, r) { return a + r.value; }, 0);
    if (!total) return empty(box);
    var R = 52, C = 2 * Math.PI * R, off = 0, wrap = h('div', 'an-donut');
    var svg = s('svg', { viewBox: '0 0 140 140', role: 'img', 'aria-label': centerLabel + ': ' + fmtv(total) });
    svg.appendChild(s('circle', { cx: 70, cy: 70, r: R, fill: 'none', stroke: 'var(--an-cell)', 'stroke-width': 18 }));
    var list = h('ul', 'an-rows');
    rows.forEach(function (r, i) {
      var len = r.value / total * C, col = COLORS[i % COLORS.length], pct = Math.round(r.value / total * 100);
      var arc = s('circle', { cx: 70, cy: 70, r: R, fill: 'none', stroke: col, 'stroke-width': 18, 'stroke-dasharray': Math.max(0, len - (rows.length > 1 ? 1.5 : 0)) + ' ' + C, 'stroke-dashoffset': -off, transform: 'rotate(-90 70 70)', class: 'an-arc', 'data-tip': r.label + '\n*' + fmtv(r.value) + (unit ? ' ' + unit : '') + ' · ' + pct + '%', 'data-c': col });
      arc.style.setProperty('--i', i); arc.style.setProperty('--d', len); svg.appendChild(arc); off += len;
      var li = h('li'), sw = h('i'); sw.style.setProperty('--c', col); li.dataset.tip = r.label + '\n*' + fmtv(r.value) + ' · ' + pct + '%'; li.dataset.c = col;
      li.appendChild(sw); li.appendChild(h('span', '', r.label)); var b = h('b', '', fmtv(r.value)); b.appendChild(h('em', '', pct + '%')); li.appendChild(b); list.appendChild(li);
    });
    var t1 = s('text', { x: 70, y: 72, 'text-anchor': 'middle', class: 'an-donut-c' }); t1.textContent = total >= 100000 ? short(total) : fmt(total);
    var t2 = s('text', { x: 70, y: 88, 'text-anchor': 'middle', class: 'an-donut-s' }); t2.textContent = centerLabel;
    svg.appendChild(t1); svg.appendChild(t2); wrap.appendChild(svg); wrap.appendChild(list); box.appendChild(wrap);
    fallback(box, ['Nomi', 'Qiymat', 'Ulushi'], rows.map(function (r) { return [r.label, fmtv(r.value), Math.round(r.value / total * 100) + '%']; }));
  }

  // ---------- vertical bars ----------
  function bars(id, rows, color, unit, ariaLabel) {
    var box = body(id); box.textContent = '';
    if (!rows.some(function (r) { return r.value > 0; })) return empty(box);
    var W = Math.max(240, box.clientWidth || 320), H = 200, m = { l: 34, r: 6, t: 10, b: 26 }, iw = W - m.l - m.r, ih = H - m.t - m.b, n = rows.length;
    var top = niceMax(Math.max.apply(null, rows.map(function (r) { return r.value; })) || 1), bw = iw / n;
    var svg = s('svg', { class: 'an-chart', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': ariaLabel });
    for (var g = 0; g <= 4; g++) { var gy = m.t + ih - ih * g / 4; svg.appendChild(s('line', { x1: m.l, x2: W - m.r, y1: gy, y2: gy, class: 'g' })); var tx = s('text', { x: m.l - 5, y: gy + 4, 'text-anchor': 'end' }); tx.textContent = short(top / 4 * g); svg.appendChild(tx); }
    var step = Math.ceil(n / Math.max(2, Math.floor(iw / 30)));
    rows.forEach(function (r, i) {
      var bh = r.value / top * ih, bx = m.l + i * bw + bw * .17;
      var rect = s('rect', { x: bx, y: m.t + ih - bh, width: bw * .66, height: Math.max(r.value ? 2 : 0, bh), rx: 4, fill: color, class: 'an-bar', 'data-tip': (r.full || r.label) + '\n*' + fmt(r.value) + ' ' + unit, 'data-c': color });
      rect.style.setProperty('--i', i); svg.appendChild(rect);
      if (i % step === 0) { var t = s('text', { x: bx + bw * .33, y: H - 8, 'text-anchor': 'middle' }); t.textContent = r.label; svg.appendChild(t); }
    });
    box.appendChild(svg);
    fallback(box, ['Nomi', 'Soni'], rows.map(function (r) { return [r.full || r.label, fmt(r.value)]; }));
  }

  // ---------- heatmap ----------
  function renderHeat() {
    var box = body('c-heat'), hm = data.visits.heatmap; box.textContent = '';
    if (!hm.max) return empty(box, "Bu davrda tashrif yo'q.");
    var wrap = h('div', 'an-heat-wrap'), grid = h('div', 'an-heat'); grid.style.setProperty('--n', hm.hours.length); grid.setAttribute('role', 'img'); grid.setAttribute('aria-label', 'Tashriflar issiqlik xaritasi: soat va hafta kuni');
    var head = h('div', 'row'); head.appendChild(h('span', 'lab')); hm.hours.forEach(function (x, i) { head.appendChild(h('span', 'lab', i % 2 === 0 ? x : '')); }); grid.appendChild(head);
    hm.days.forEach(function (d, di) {
      var row = h('div', 'row'); row.appendChild(h('span', 'lab', d));
      hm.matrix[di].forEach(function (v, hi) { var c = h('span', 'an-cell'); c.style.setProperty('--v', v ? (0.12 + 0.88 * v / hm.max).toFixed(2) : 0); c.dataset.tip = d + ', ' + hm.hours[hi] + ':00\n' + v + ' tashrif'; row.appendChild(c); });
      grid.appendChild(row);
    });
    wrap.appendChild(grid); box.appendChild(wrap);
    var lg = h('div', 'an-heat-leg'); lg.appendChild(document.createTextNode('Kam')); lg.appendChild(h('i')); lg.appendChild(document.createTextNode("Ko'p (eng ko'pi: " + hm.max + ')')); box.appendChild(lg);
    fallback(box, ['Kun'].concat(hm.hours.map(function (x) { return x + ':00'; })), hm.days.map(function (d, i) { return [d].concat(hm.matrix[i]); }));
  }

  // ---------- lists ----------
  function renderProducts() {
    var box = body('c-products'), rows = data.products.rows; box.textContent = '';
    if (!rows.length) return empty(box, "Bu davrda sotuv yo'q.");
    var top = Math.max.apply(null, rows.map(function (r) { return r.revenue; })) || 1, list = h('div', 'an-hb');
    rows.forEach(function (r, i) {
      var it = h('div', 'it'), t = h('div', 'top'), name = r.url ? h('a', '', r.label) : h('span', '', r.label); if (r.url) name.href = r.url;
      t.appendChild(name); t.appendChild(h('b', '', fmt(r.revenue) + " so'm · " + r.value + ' dona')); it.appendChild(t);
      var tr = h('div', 'an-track'), bar = h('i'); bar.style.setProperty('--w', Math.max(3, Math.round(r.revenue / top * 100)) + '%'); bar.style.setProperty('--i', i); tr.appendChild(bar); it.appendChild(tr);
      it.dataset.tip = r.label + '\n*' + fmt(r.revenue) + " so'm\n*" + r.value + ' dona'; it.dataset.c = COLORS[1]; list.appendChild(it);
    });
    box.appendChild(list);
    fallback(box, ['Mahsulot', 'Dona', "Tushum (so'm)"], rows.map(function (r) { return [r.label, r.value, fmt(r.revenue)]; }));
  }
  function renderStock() {
    var box = body('c-stock'), rows = data.stock.rows; box.textContent = '';
    if (!rows.length) return empty(box, 'Hamma mahsulot yetarli. Tugayotgani yo\'q.');
    var ul = h('ul', 'an-list');
    rows.forEach(function (r) {
      var li = h('li'), left = h('div'), a = h('a', '', r.label); a.href = r.url; left.appendChild(a); left.appendChild(document.createElement('br')); left.appendChild(h('small', '', 'Olib kelish tavsiyasi: ' + r.need + ' dona'));
      li.appendChild(left); li.appendChild(h('span', 'an-pill' + (r.stock === 0 ? ' bad' : ''), r.stock === 0 ? 'Tugadi' : 'Qoldi: ' + r.stock)); ul.appendChild(li);
    });
    var sc = h('div', 'an-scroll'); sc.appendChild(ul); box.appendChild(sc);
  }
  var selected = {};
  function renderExpiring() {
    var box = body('c-expiring'), d = data.expiring; box.textContent = ''; selected = {};
    if (!d.rows.length) return empty(box, "7 kun ichida tugaydigan abonement yo'q.");
    var bulk = h('div', 'an-bulk'), lab = h('label'), all = h('input'); all.type = 'checkbox'; all.checked = true; lab.appendChild(all); lab.appendChild(document.createTextNode(' Hammasini tanlash · jami ' + d.total + ' ta'));
    var btn = h('button', 'an-btn primary'); btn.type = 'button'; btn.appendChild(icon('send')); var bt = h('span'); btn.appendChild(bt);
    bulk.appendChild(lab); bulk.appendChild(btn); box.appendChild(bulk);
    var ul = h('ul', 'an-list'), boxes = [];
    d.rows.forEach(function (r) {
      selected[r.id] = true;
      var li = h('li', 'an-exp'), cb = h('input'); cb.type = 'checkbox'; cb.checked = true; cb.setAttribute('aria-label', r.label + ' tanlash'); boxes.push(cb);
      cb.addEventListener('change', function () { selected[r.id] = cb.checked; sync(); });
      var left = h('div'), a = h('a', '', r.label); a.href = r.url; left.appendChild(a); left.appendChild(document.createElement('br')); left.appendChild(h('small', '', (r.phone || 'telefon yo\'q') + ' · ' + r.until));
      li.appendChild(cb); li.appendChild(left); li.appendChild(h('span', 'an-pill', r.days === 0 ? 'Bugun' : r.days + ' kun')); ul.appendChild(li);
    });
    function sync() { var n = Object.keys(selected).filter(function (k) { return selected[k]; }).length; bt.textContent = 'Eslatma yuborish (' + n + ')'; btn.disabled = !n; all.checked = n === d.rows.length; }
    all.addEventListener('change', function () { boxes.forEach(function (c, i) { c.checked = all.checked; selected[d.rows[i].id] = all.checked; }); sync(); });
    btn.addEventListener('click', function () { remind(Object.keys(selected).filter(function (k) { return selected[k]; }).map(Number), btn); });
    sync(); var sc = h('div', 'an-scroll'); sc.appendChild(ul); box.appendChild(sc);
    if (d.total > d.rows.length) box.appendChild(h('p', 'an-sub', 'Ro\'yxatda dastlabki ' + d.rows.length + ' ta ko\'rsatilgan. Barcha ' + d.total + ' taga yuborish uchun yuqoridagi xulosa tugmasidan foydalaning.'));
  }

  // ---------- actions ----------
  var toastT;
  function toast(msg) { var t = el('an-toast'); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(function () { t.hidden = true; }, 5000); }
  function remind(ids, btn) {
    if (btn) btn.disabled = true;
    fetch(root.dataset.remind, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' }, body: JSON.stringify({ ids: ids }) })
      .then(function (r) { return r.json(); }).then(function (j) { toast(j.ok ? j.message : (j.error || 'Xatolik')); })
      .catch(function () { toast("Aloqa yo'q. Qayta urinib ko'ring."); }).then(function () { if (btn) btn.disabled = false; });
  }

  // ---------- render all ----------
  var drawn = false;
  function renderCharts() {
    renderRevenue();
    donut('c-plans', data.plans.rows, 'ta', 'abonement', fmt);
    donut('c-methods', data.methods.rows, "so'm", "so'm", function (v) { return fmt(v) + " so'm"; });
    bars('c-weekday', data.visits.weekday, COLORS[3], 'tashrif', 'Hafta kunlari bo\'yicha tashriflar');
    bars('c-members', data.members.rows, COLORS[2], "ta a'zo", "Yangi a'zolar dinamikasi");
    renderHeat(); renderProducts(); renderStock(); renderExpiring();
    requestAnimationFrame(function () { requestAnimationFrame(function () { root.classList.add('in'); }); });
  }
  function renderAll() {
    root.classList.remove('in');
    el('an-range').textContent = period.label + (period.days > 1 ? ' (' + period.days + ' kun)' : '') + " · oldingi davr bilan solishtirma";
    renderInsights(); renderKpis(); renderCharts(); drawn = true;
  }

  // ---------- period switching without a reload ----------
  function setActive(key) {
    root.querySelectorAll('.an-seg a, .an-seg button').forEach(function (n) { n.classList.toggle('on', n.dataset.period === key || (key === 'custom' && n.hasAttribute('data-custom-toggle'))); });
  }
  function load(params) {
    var q = new URLSearchParams(params).toString(), err = el('an-error');
    root.classList.add('loading'); err.hidden = true;
    fetch(root.dataset.base + '?' + q, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: "Server javobi tushunarsiz." }; }); })
      .then(function (j) {
        if (!j.ok) throw new Error(j.error || 'Xatolik');
        data = j.data; period = j.period; setActive(period.key); renderAll();
        el('an-csv').href = root.dataset.csv + '?' + q;
        history.replaceState(null, '', root.dataset.page + '?' + q);
      })
      .catch(function (e) { err.textContent = (e && e.message ? e.message : 'Xatolik') + " — qayta urinib ko'ring."; err.hidden = false; })
      .then(function () { root.classList.remove('loading'); });
  }
  root.querySelectorAll('.an-seg a[data-period]').forEach(function (a) { a.addEventListener('click', function (e) { e.preventDefault(); el('an-custom').hidden = true; load({ period: a.dataset.period }); }); });
  var tgl = root.querySelector('[data-custom-toggle]');
  tgl.addEventListener('click', function () { var f = el('an-custom'); f.hidden = !f.hidden; tgl.setAttribute('aria-expanded', String(!f.hidden)); });
  el('an-custom').addEventListener('submit', function (e) { e.preventDefault(); var f = e.target; load({ period: 'custom', from: f.from.value, to: f.to.value }); });

  var rt;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { if (!drawn) return; root.classList.add('in'); renderRevenue(); bars('c-weekday', data.visits.weekday, COLORS[3], 'tashrif', 'Hafta kunlari bo\'yicha tashriflar'); bars('c-members', data.members.rows, COLORS[2], "ta a'zo", "Yangi a'zolar dinamikasi"); }, 200); });

  renderAll();
})();
