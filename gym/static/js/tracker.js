/* Fitness tracker (/progress/): period picker, inline SVG charts drawn from /progress/data/, a table under every chart, before/after
   comparison and the goal form. Vanilla JS, no libraries. */
(function () {
  var root = document.querySelector('[data-tk]');
  if (!root) return;
  var L = {};
  try { L = JSON.parse(document.getElementById('tkLabels').textContent); } catch (e) {}
  var NS = 'http://www.w3.org/2000/svg';
  var COLORS = ['var(--accent)', 'var(--focus)', 'var(--good)', 'var(--warn)', 'var(--muted)', 'var(--bad)', '#8b5cf6'];
  var data = null, hidden = {}, strengthPick = '';

  function t(k) { return L[k.replace(/_/g, '')] || k; }
  function el(name, attrs, parent, text) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function html(tag, cls, parent, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function day(iso) { var p = iso.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 864e5; }
  function fmtDay(n) { var d = new Date(n * 864e5); return String(d.getUTCDate()).padStart(2, '0') + '.' + String(d.getUTCMonth() + 1).padStart(2, '0'); }
  function fmtIso(iso) { var p = iso.split('-'); return p[2] + '.' + p[1] + '.' + p[0]; }
  function num(v) { return Math.round(v * 10) / 10; }
  function section(name) { return root.querySelector('[data-chart="' + name + '"]'); }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function empty(plot) { clear(plot); html('p', 'muted tk-empty', plot, t('ftr_no_data')); }

  /* ---- generic line chart: series = [{name, color, pts:[[x, y]], dash, dots, width}], hlines = [{y, color, label}] */
  function line(plot, series, o) {
    o = o || {};
    clear(plot);
    var all = [];
    series.forEach(function (s) { all = all.concat(s.pts); });
    (o.hlines || []).forEach(function (h) { all.push([null, h.y]); });
    var xs = all.filter(function (p) { return p[0] != null; }).map(function (p) { return p[0]; });
    if (!xs.length) { empty(plot); return; }
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    if (x1 === x0) { x0 -= 1; x1 += 1; }
    var ys = all.map(function (p) { return p[1]; });
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    var pad = (y1 - y0) * .12 || Math.max(1, Math.abs(y1) * .05);
    y0 -= pad; y1 += pad;
    var W = 640, H = o.h || 240, ML = 44, MR = 12, MT = 12, MB = 26;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, 'class': 'chart tk-svg', role: 'img', 'aria-label': o.label || '' }, plot);
    function X(v) { return ML + (v - x0) / (x1 - x0) * (W - ML - MR); }
    function Y(v) { return H - MB - (v - y0) / (y1 - y0) * (H - MT - MB); }
    for (var i = 0; i <= 3; i++) {
      var yv = y0 + (y1 - y0) * i / 3;
      el('line', { 'class': 'grid-l', x1: ML, x2: W - MR, y1: Y(yv), y2: Y(yv) }, svg);
      el('text', { x: ML - 6, y: Y(yv) + 4, 'text-anchor': 'end' }, svg, String(num(yv)));
    }
    for (var j = 0; j <= 3; j++) {
      var xv = x0 + (x1 - x0) * j / 3;
      el('text', { x: X(xv), y: H - 8, 'text-anchor': j === 0 ? 'start' : j === 3 ? 'end' : 'middle' }, svg, fmtDay(Math.round(xv)));
    }
    (o.hlines || []).forEach(function (h) {
      el('line', { x1: ML, x2: W - MR, y1: Y(h.y), y2: Y(h.y), stroke: h.color, 'stroke-dasharray': '6 4', 'stroke-width': 1.5 }, svg);
      el('text', { x: W - MR - 2, y: Y(h.y) - 4, 'text-anchor': 'end', fill: h.color }, svg, h.label);
    });
    series.forEach(function (s) {
      if (s.pts.length > 1) {
        el('polyline', { points: s.pts.map(function (p) { return X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }).join(' '), style: 'stroke:' + s.color + ';stroke-width:' + (s.width || 2.5) + ';stroke-dasharray:' + (s.dash || 'none'), 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, svg);
      }
      if (s.dots !== false) {
        s.pts.forEach(function (p) {
          var c = el('circle', { cx: X(p[0]).toFixed(1), cy: Y(p[1]).toFixed(1), r: s.pts.length > 60 ? 1.8 : 3.5, style: 'fill:' + s.color }, svg);
          el('title', {}, c, s.name + ' · ' + fmtDay(p[0]) + ': ' + num(p[1]));
        });
      }
    });
  }

  /* ---- grouped bar chart: items = [{label, vals:[...]}] */
  function bars(plot, items, colors, o) {
    o = o || {};
    clear(plot);
    if (!items.length) { empty(plot); return; }
    var max = Math.max.apply(null, items.map(function (i) { return Math.max.apply(null, i.vals); }).concat([o.line || 0, 1]));
    var W = 640, H = 220, ML = 44, MR = 12, MT = 12, MB = 26, n = items.length, k = colors.length;
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, 'class': 'chart tk-svg', role: 'img', 'aria-label': o.label || '' }, plot);
    function Y(v) { return H - MB - v / max * (H - MT - MB); }
    for (var i = 0; i <= 3; i++) {
      var yv = max * i / 3;
      el('line', { 'class': 'grid-l', x1: ML, x2: W - MR, y1: Y(yv), y2: Y(yv) }, svg);
      el('text', { x: ML - 6, y: Y(yv) + 4, 'text-anchor': 'end' }, svg, String(Math.round(yv)));
    }
    var slot = (W - ML - MR) / n, bw = Math.max(1.5, Math.min(26, slot * .8 / k));
    items.forEach(function (it, idx) {
      var cx = ML + slot * (idx + .5);
      it.vals.forEach(function (v, j) {
        var h = Math.max(v > 0 ? 1.5 : 0, H - MB - Y(v));
        var color = it.colors ? it.colors[j] : colors[j];
        var r = el('rect', { x: (cx - bw * k / 2 + bw * j).toFixed(1), y: (H - MB - h).toFixed(1), width: bw.toFixed(1), height: h.toFixed(1), fill: color, rx: 1.5 }, svg);
        el('title', {}, r, it.label + ': ' + v);
      });
      if (n <= 14 || idx % Math.ceil(n / 8) === 0) el('text', { x: cx, y: H - 8, 'text-anchor': 'middle' }, svg, it.label);
    });
    if (o.line) {
      el('line', { x1: ML, x2: W - MR, y1: Y(o.line), y2: Y(o.line), stroke: 'var(--good)', 'stroke-dasharray': '6 4', 'stroke-width': 1.5 }, svg);
      el('text', { x: W - MR - 2, y: Y(o.line) - 4, 'text-anchor': 'end', fill: 'var(--good)' }, svg, t('ftr_target') + ' ' + o.line);
    }
  }

  function legend(box, entries) {
    clear(box);
    entries.forEach(function (e) { var s = html('span', 'tk-key', box); html('i', '', s).style.background = e.color; s.appendChild(document.createTextNode(e.name)); });
  }
  function table(box, head, rows) {
    clear(box);
    if (!rows.length) { html('p', 'muted', box, t('ftr_no_data')); return; }
    var wrap = html('div', 'tbl', box), tb = html('table', '', wrap), tr = html('tr', '', html('thead', '', tb));
    head.forEach(function (h) { html('th', '', tr, h); });
    var body = html('tbody', '', tb);
    rows.forEach(function (r) { var row = html('tr', '', body); r.forEach(function (c) { html('td', 'num', row, c == null ? '—' : String(c)); }); });
  }
  function xy(list) { return list.map(function (p) { return [day(p.d), p.v]; }); }

  /* ---- the charts */
  function drawWeight(d) {
    var s = section('weight'), w = d.weight, plot = s.querySelector('[data-plot]');
    var delta = s.querySelector('[data-delta]');
    if (w.points.length > 1) { var dv = num(w.points[w.points.length - 1].v - w.points[0].v); delta.textContent = (dv > 0 ? '+' : '') + dv + ' kg'; delta.hidden = false; } else delta.hidden = true;
    var series = [{ name: t('ftr_weight'), color: 'var(--muted)', pts: xy(w.points), width: 1.5 }, { name: t('ftr_ma7'), color: 'var(--accent)', pts: xy(w.ma), dots: false, width: 3 }];
    var ent = [{ name: t('ftr_weight'), color: 'var(--muted)' }, { name: t('ftr_ma7'), color: 'var(--accent)' }];
    var hl = [];
    if (w.goal) { hl.push({ y: w.goal.target, color: 'var(--good)', label: t('ftr_goal') + ' ' + w.goal.target }); ent.push({ name: t('ftr_goal'), color: 'var(--good)' }); }
    if (w.projection) { series.push({ name: t('ftr_projection'), color: 'var(--focus)', dash: '6 5', dots: false, pts: [[day(w.projection.d0), w.projection.v0], [day(w.projection.d1), w.projection.v1]] }); ent.push({ name: t('ftr_projection'), color: 'var(--focus)' }); }
    legend(s.querySelector('[data-legend]'), ent);
    if (!w.points.length) empty(plot); else line(plot, series, { hlines: hl, label: t('ftr_weight') });
    var ma = {};
    w.ma.forEach(function (p) { ma[p.d] = p.v; });
    table(s.querySelector('[data-table]'), [t('ftr_date'), t('ftr_weight'), t('ftr_ma7')], w.points.map(function (p) { return [fmtIso(p.d), p.v, ma[p.d]]; }));
  }

  function drawMeasures(d) {
    var s = section('measures'), ser = d.measures.series, keys = Object.keys(ser), plot = s.querySelector('[data-plot]'), lg = s.querySelector('[data-legend]');
    clear(lg);
    keys.forEach(function (k, i) {
      var lab = html('label', 'tk-key', lg), cb = html('input', '', lab);
      cb.type = 'checkbox'; cb.checked = !hidden[k];
      cb.addEventListener('change', function () { hidden[k] = !cb.checked; drawMeasures(d); });
      html('i', '', lab).style.background = COLORS[i % COLORS.length];
      lab.appendChild(document.createTextNode(t('ftr_m_' + k)));
    });
    var series = keys.filter(function (k) { return !hidden[k]; }).map(function (k) { return { name: t('ftr_m_' + k), color: COLORS[keys.indexOf(k) % COLORS.length], pts: xy(ser[k]) }; });
    if (!keys.length || !series.length) empty(plot); else line(plot, series, { label: t('ftr_measures') });
    var dates = {};
    keys.forEach(function (k) { ser[k].forEach(function (p) { (dates[p.d] = dates[p.d] || {})[k] = p.v; }); });
    table(s.querySelector('[data-table]'), [t('ftr_date')].concat(keys.map(function (k) { return t('ftr_m_' + k); })),
      Object.keys(dates).sort().map(function (dd) { return [fmtIso(dd)].concat(keys.map(function (k) { return dates[dd][k]; })); }));
  }

  function drawFat(d) {
    var s = section('body_fat'), plot = s.querySelector('[data-plot]'), f = d.body_fat.points, h = d.resting_hr.points;
    clear(plot);
    legend(s.querySelector('[data-legend]'), [{ name: t('ftr_body_fat') + ' (%)', color: 'var(--accent)' }, { name: t('ftr_resting_hr') + ' (bpm)', color: 'var(--focus)' }]);
    if (!f.length && !h.length) { empty(plot); } else {
      if (f.length) line(html('div', '', plot), [{ name: t('ftr_body_fat'), color: 'var(--accent)', pts: xy(f) }], { h: 180, label: t('ftr_body_fat') });
      if (h.length) line(html('div', '', plot), [{ name: t('ftr_resting_hr'), color: 'var(--focus)', pts: xy(h) }], { h: 180, label: t('ftr_resting_hr') });
    }
    var m = {};
    f.forEach(function (p) { (m[p.d] = m[p.d] || {}).f = p.v; });
    h.forEach(function (p) { (m[p.d] = m[p.d] || {}).h = p.v; });
    table(s.querySelector('[data-table]'), [t('ftr_date'), t('ftr_body_fat'), t('ftr_resting_hr')], Object.keys(m).sort().map(function (k) { return [fmtIso(k), m[k].f, m[k].h]; }));
  }

  function drawStrength(d) {
    var s = section('strength'), sel = s.querySelector('[data-picker]'), plot = s.querySelector('[data-plot]'), names = d.strength.exercises;
    if (!names.length) { sel.hidden = true; empty(plot); table(s.querySelector('[data-table]'), [], []); return; }
    sel.hidden = false;
    if (names.indexOf(strengthPick) < 0) strengthPick = names[0];
    clear(sel);
    names.forEach(function (n) { var o = html('option', '', sel, n); o.value = n; o.selected = n === strengthPick; });
    var pts = d.strength.series[strengthPick] || [];
    line(plot, [{ name: strengthPick, color: 'var(--accent)', pts: xy(pts) }], { label: t('ftr_strength') + ': ' + strengthPick });
    table(s.querySelector('[data-table]'), [t('ftr_date'), t('ftr_est1rm') + ' (kg)'], pts.map(function (p) { return [fmtIso(p.d), p.v]; }));
  }

  function drawVolume(d) {
    var s = section('volume');
    bars(s.querySelector('[data-plot]'), d.volume.map(function (w) { return { label: fmtDay(day(w.w)), vals: [w.v] }; }), ['var(--accent)'], { label: t('ftr_volume') });
    table(s.querySelector('[data-table]'), [t('ftr_week'), t('ftr_volume') + ' (kg)'], d.volume.map(function (w) { return [fmtIso(w.w), w.v]; }));
  }

  function drawActivity(d) {
    var s = section('activity');
    legend(s.querySelector('[data-legend]'), [{ name: t('ftr_workouts'), color: 'var(--accent)' }, { name: t('ftr_visits'), color: 'var(--focus)' }]);
    bars(s.querySelector('[data-plot]'), d.activity.map(function (w) { return { label: fmtDay(day(w.w)), vals: [w.workouts, w.visits] }; }), ['var(--accent)', 'var(--focus)'], { label: t('ftr_activity') });
    table(s.querySelector('[data-table]'), [t('ftr_week'), t('ftr_workouts'), t('ftr_visits')], d.activity.map(function (w) { return [fmtIso(w.w), w.workouts, w.visits]; }));
  }

  function drawCalories(d) {
    var s = section('calories'), c = d.calories, badge = s.querySelector('[data-adherence]');
    badge.textContent = c.adherence == null ? '' : t('ftr_adherence').replace('{pct}', c.adherence).replace('{n}', c.within_days).replace('{total}', c.logged_days);
    badge.hidden = c.adherence == null;
    legend(s.querySelector('[data-legend]'), [{ name: t('ftr_calories') + ' (±10%)', color: 'var(--good)' }, { name: t('ftr_calories'), color: 'var(--warn)' }]);
    var items = c.days.map(function (x) {
      var ok = Math.abs(x.kcal - x.target) <= x.target * .1;
      return { label: fmtDay(day(x.d)), vals: [x.kcal], colors: [ok ? 'var(--good)' : 'var(--warn)'] };
    });
    bars(s.querySelector('[data-plot]'), items, ['var(--warn)'], { line: c.target, label: t('ftr_calories') });
    table(s.querySelector('[data-table]'), [t('ftr_date'), 'kcal', t('ftr_target')], c.days.map(function (x) { return [fmtIso(x.d), x.kcal, x.target]; }));
  }

  function drawAll(d) {
    data = d;
    drawWeight(d); drawMeasures(d); drawFat(d); drawStrength(d); drawVolume(d); drawActivity(d); drawCalories(d);
    var st = root.querySelector('[data-streak]');
    st.textContent = t('ftr_streak').replace('{d}', d.streak.days).replace('{w}', d.streak.weeks);
  }

  function load(period) {
    root.setAttribute('aria-busy', 'true');
    fetch(root.dataset.url + '?period=' + encodeURIComponent(period), { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json(); }).then(drawAll)
      .catch(function () {}).then(function () { root.removeAttribute('aria-busy'); });
  }

  root.querySelectorAll('[data-period]').forEach(function (b) {
    b.addEventListener('click', function () {
      root.querySelectorAll('[data-period]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      try { history.replaceState(null, '', '?period=' + b.dataset.period); } catch (e) {}
      load(b.dataset.period);
    });
  });
  var pick = section('strength').querySelector('[data-picker]');
  pick.addEventListener('change', function () { strengthPick = pick.value; if (data) drawStrength(data); });

  /* ---- before / after */
  var cmp = root.querySelector('[data-compare]');
  if (cmp) {
    var out = cmp.querySelector('[data-cmp-out]');
    cmp.querySelector('[data-cmp-go]').addEventListener('click', function () {
      var a = cmp.querySelector('[name=a]').value, b = cmp.querySelector('[name=b]').value;
      clear(out);
      if (!a || !b) { html('p', 'muted', out, t('ftr_pick_two')); return; }
      fetch(cmp.dataset.url + '?a=' + a + '&b=' + b, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) {
        if (!j.ok) { html('p', 'field-err', out, j.error || ''); return; }
        var names = { weight: t('weight'), bmi: t('bmi'), body_fat: t('ftr_body_fat'), resting_hr: t('ftr_resting_hr') };
        var rows = j.rows.filter(function (r) { return r.a != null || r.b != null; }).map(function (r) {
          return [names[r.key] || t('ftr_m_' + r.key), r.a, r.b, r.diff == null ? null : (r.diff > 0 ? '+' : '') + r.diff];
        });
        table(out, [t('ftr_value'), fmtIso(j.a), fmtIso(j.b), t('ftr_diff')], rows);
      });
    });
  }

  /* ---- goal form: shows the field that matches the goal type */
  var gk = document.querySelector('[data-goal-kind]');
  if (gk) {
    var sync = function () {
      document.querySelectorAll('[data-goalform] [data-for]').forEach(function (lab) {
        var on = lab.dataset.for === gk.value;
        lab.hidden = !on;
        lab.querySelectorAll('select,input').forEach(function (f) { f.disabled = !on; });
      });
    };
    gk.addEventListener('change', sync); sync();
  }

  var firstActive = root.querySelector('[data-period][aria-pressed="true"]');
  load(firstActive ? firstActive.dataset.period : '3m');
})();
