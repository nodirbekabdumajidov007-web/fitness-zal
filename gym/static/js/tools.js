/* Fitness calculators. Everything is computed in the browser and updates as you type.
   Pure math lives in FZTools (no DOM) so it can be checked on its own:
   BMI = kg / m² (WHO classes); BMR = Mifflin–St Jeor (+5 men / −161 women); TDEE = BMR × activity (1.2 … 1.9);
   goal: lose −20 % of TDEE (never below BMR, max 1000 kcal), gain +12 %; 1 kg of body fat ≈ 7700 kcal;
   macros: protein 1.8 g/kg (2.2 when cutting), fat 0.8–1.0 g/kg (≥ 20 % of kcal), carbs = the rest;
   1RM = average of Epley and Brzycki (1–12 reps); water ≈ 33 ml/kg + 10 ml per training minute (+0.5 l in heat);
   heart rate: max = Tanaka 208 − 0.7 × age, zones by Karvonen if resting HR is known, else % of max;
   body fat: US Navy method (metric). */
(function (global) {
  var M = {};
  M.bmi = function (w, h) { return w / Math.pow(h / 100, 2); };
  M.bmiClass = function (b) { return b < 18.5 ? 'under' : b < 25 ? 'normal' : b < 30 ? 'over' : 'obese'; };
  M.healthyRange = function (h) { var m = h / 100; return [18.5 * m * m, 24.9 * m * m]; };
  M.devine = function (male, h) { return (male ? 50 : 45.5) + 2.3 * Math.max(0, h / 2.54 - 60); };
  M.bmr = function (male, w, h, age) { return 10 * w + 6.25 * h - 5 * age + (male ? 5 : -161); };
  // goal: 'lose' | 'keep' | 'gain' → {target, delta, perWeek (kg), floored}
  M.target = function (goal, bmr, tdee) {
    var t = tdee, floored = false;
    if (goal === 'lose') {
      t = tdee - Math.min(0.2 * tdee, 1000);
      if (t < bmr) { t = bmr; floored = true; }
    } else if (goal === 'gain') { t = tdee * 1.12; }
    t = Math.round(t);
    var delta = t - Math.round(tdee);
    return { target: t, delta: delta, perWeek: delta * 7 / 7700, floored: floored };
  };
  // grams of protein / fat / carbs that add up to `kcal` (± rounding)
  M.macros = function (goal, w, h, kcal) {
    var m = h / 100, ref = 25 * m * m, bw = w <= 30 * m * m ? w : ref + 0.4 * (w - ref); // high body weight: use an adjusted weight
    var p = Math.min((goal === 'lose' ? 2.2 : 1.8) * bw, 220, kcal * 0.35 / 4);
    var f = Math.max((goal === 'lose' ? 0.8 : goal === 'gain' ? 1.0 : 0.9) * bw, kcal * 0.2 / 9);
    if (p * 4 + f * 9 > kcal) {
      f = Math.max(kcal * 0.2 / 9, (kcal - p * 4) / 9);
      if (p * 4 + f * 9 > kcal) p = (kcal - f * 9) / 4;
    }
    p = Math.round(p); f = Math.round(f);
    var c = Math.max(0, Math.round((kcal - p * 4 - f * 9) / 4));
    return { p: p, f: f, c: c, pk: p * 4, fk: f * 9, ck: c * 4 };
  };
  M.orm = function (lw, r) { return r <= 1 ? lw : (lw * (1 + r / 30) + lw * 36 / (37 - r)) / 2; };
  M.pctTable = [[95, 2], [90, 4], [85, 6], [80, 8], [75, 10], [70, 12]];
  M.water = function (w, trainMin, hot) { return (33 * w + 10 * trainMin + (hot ? 500 : 0)) / 1000; };
  M.hrMax = function (age) { return 208 - 0.7 * age; };
  M.zonePcts = [[50, 60], [60, 70], [70, 80], [80, 90], [90, 100]];
  M.zones = function (age, rest) {
    var max = M.hrMax(age), res = rest > 0 ? max - rest : 0;
    return M.zonePcts.map(function (z) {
      return rest > 0 ? [Math.round(rest + res * z[0] / 100), Math.round(rest + res * z[1] / 100)]
                      : [Math.round(max * z[0] / 100), Math.round(max * z[1] / 100)];
    });
  };
  // US Navy body-fat %, lengths in cm; null when the measurements are impossible
  M.bodyFat = function (male, h, neck, waist, hip) {
    var bf;
    if (male) {
      if (waist <= neck) return null;
      bf = 495 / (1.0324 - 0.19077 * Math.log10(waist - neck) + 0.15456 * Math.log10(h)) - 450;
    } else {
      if (waist + hip <= neck) return null;
      bf = 495 / (1.29579 - 0.35004 * Math.log10(waist + hip - neck) + 0.221 * Math.log10(h)) - 450;
    }
    return isFinite(bf) && bf >= 2 && bf <= 60 ? bf : null;
  };
  M.bfClass = function (male, bf) {
    var t = male ? [6, 14, 18, 25] : [14, 21, 25, 32];
    return bf < t[0] ? 1 : bf < t[1] ? 2 : bf < t[2] ? 3 : bf < t[3] ? 4 : 5;
  };
  global.FZTools = M;

  var root = global.document && document.querySelector('[data-tools]');
  if (!root) return;
  var T = document.getElementById('tl-i18n').dataset, KEY = 'fz_tools_v2', TABKEY = 'fz_tools_tab', NB = ' ';
  var RULES = { age: [14, 90], w: [30, 250], h: [120, 230], lw: [1, 500], lr: [1, 12], tm: [0, 300], rhr: [30, 120], neck: [25, 60], waist: [50, 200], hip: [60, 200] };

  function input(name) { return root.querySelector('[name="' + name + '"]'); }
  function raw(name) { var e = input(name); return e ? String(e.value).trim() : ''; }
  function num(name) { var s = raw(name).replace(',', '.'); return s === '' ? NaN : Number(s); }
  function sv(name) { var e = root.querySelector('[name="' + name + '"]:checked'); return e ? e.value : ''; }
  function out(k, text) { root.querySelectorAll('[data-out="' + k + '"]').forEach(function (e) { e.textContent = text; }); }
  function el(k) { return root.querySelector('[data-out="' + k + '"]'); }
  function box(k) { return root.querySelector('[data-chart="' + k + '"]'); }
  function show(node, on) { if (node) node.hidden = !on; }
  function n(x) { return Math.round(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g, NB); }
  function d1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
  function fmt(s, o) { return String(s).replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

  // validate the named fields; returns the list of problems and marks bad inputs
  function check(names, optional) {
    var bad = [];
    names.forEach(function (nm) {
      var e = input(nm), x = num(nm), r = RULES[nm], empty = raw(nm) === '';
      var ok = (empty && optional && optional.indexOf(nm) >= 0) || (!empty && isFinite(x) && x >= r[0] && x <= r[1]);
      if (e) e.setAttribute('aria-invalid', ok ? 'false' : 'true');
      if (!ok) bad.push(fmt(T.range, { n: T['n' + nm.charAt(0).toUpperCase() + nm.slice(1)], min: r[0], max: r[1] }));
    });
    return bad;
  }
  function hint(k, msgs) { var e = root.querySelector('[data-hint="' + k + '"]'); if (e) { e.textContent = msgs.join(' · '); e.hidden = !msgs.length; } }
  function dash(keys) { keys.forEach(function (k) { out(k, '—'); }); }

  // ---------------------------------------------------------------- charts (inline SVG, built once, then only updated)
  var C = {}, W = 300; // gauge geometry: viewBox 0 0 300 56, bar at y 22..34
  function scaleSvg(id, segs, ticks) {
    var s = '<svg class="tl-svg" viewBox="0 0 ' + W + ' 56" aria-hidden="true" focusable="false"><defs><clipPath id="tl-clip-' + id + '"><rect x="0" y="22" width="' + W + '" height="12" rx="6"/></clipPath></defs><g clip-path="url(#tl-clip-' + id + ')">';
    segs.forEach(function (c) { s += '<rect class="' + c + '" x="0" y="22" width="0" height="12"/>'; });
    s += '</g>';
    for (var i = 0; i < ticks; i++) s += '<rect class="gap" x="0" y="22" width="2" height="12"/><text class="tk" x="0" y="50" text-anchor="middle"></text>';
    return s + '<g class="pin" style="opacity:0"><path d="M0 19L-6 8H6Z"/><rect x="-1.5" y="19" width="3" height="18" rx="1.5"/></g></svg>';
  }
  function placeScale(svg, edges, max, ticks) { // edges: [0, t1, t2, …, max] in value units
    var k = W / max, rs = svg.querySelectorAll('g[clip-path] rect');
    for (var i = 0; i < rs.length; i++) { rs[i].setAttribute('x', edges[i] * k); rs[i].setAttribute('width', (edges[i + 1] - edges[i]) * k); }
    var gaps = svg.querySelectorAll('.gap'), tks = svg.querySelectorAll('.tk');
    for (var j = 0; j < gaps.length; j++) {
      gaps[j].setAttribute('x', edges[j + 1] * k - 1); tks[j].setAttribute('x', edges[j + 1] * k); tks[j].textContent = ticks[j];
    }
  }
  function pinTo(svg, v, max) {
    var p = svg.querySelector('.pin');
    if (v === null) { p.style.opacity = 0; return; }
    p.style.opacity = 1; p.style.transform = 'translateX(' + (clamp(v / max, 0, 1) * W).toFixed(1) + 'px)';
  }
  function row(parent, fillCls) {
    var r = document.createElement('div'); r.className = 'tl-r';
    r.innerHTML = '<span class="nm"></span><b class="num"></b><svg class="tl-bar" viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="f ' + fillCls + '" x="0" y="0" width="0" height="8"/></svg>';
    parent.appendChild(r);
    return { nm: r.querySelector('.nm'), val: r.querySelector('b'), rect: r.querySelector('rect') };
  }
  function setRow(r, name, val, x, w) {
    r.nm.textContent = name; r.val.textContent = val;
    x = clamp(x, 0, 100); w = clamp(w, 0, 100 - x);
    r.rect.setAttribute('x', x); r.rect.setAttribute('width', w); r.rect.style.x = x + 'px'; r.rect.style.width = w + 'px';
  }

  var BF_MAX = 40; // body-fat scale 0…40 %; BMI scale 15…40 drawn on the full width
  (function build() {
    C.bmi = box('bmi'); C.bmi.innerHTML = scaleSvg('bmi', ['s-under', 's-normal', 's-over', 's-obese'], 3);
    C.bmiSvg = C.bmi.firstChild; placeScale(C.bmiSvg, [0, 3.5, 10, 15, 25], 25, ['18.5', '25', '30']);
    C.bf = box('bf'); C.bf.innerHTML = scaleSvg('bf', ['s-bf1', 's-bf2', 's-bf3', 's-bf4', 's-bf5'], 4);
    C.bfSvg = C.bf.firstChild;
    C.cal = [row(box('cal'), 'c-bmr'), row(box('cal'), 'c-tdee'), row(box('cal'), 'c-target')];
    C.orm = [100].concat(M.pctTable.map(function (x) { return x[0]; })).map(function () { return row(box('orm'), 'c-orm'); });
    C.zones = M.zonePcts.map(function (z, i) { return row(box('zones'), 'z' + (i + 1)); });
    box('macro').innerHTML = '<svg class="tl-svg" viewBox="0 0 120 120" aria-hidden="true" focusable="false"><circle class="trk" cx="60" cy="60" r="48"/><g transform="rotate(-90 60 60)">' +
      ['p', 'f', 'c'].map(function (k) { return '<circle class="arc ' + k + '" cx="60" cy="60" r="48" pathLength="100" style="stroke-dasharray:0 100"/>'; }).join('') +
      '</g><text class="dv" x="60" y="64" text-anchor="middle">—</text><text class="du" x="60" y="80" text-anchor="middle">' + T.kcal + '</text></svg>';
    C.arcs = box('macro').querySelectorAll('.arc'); C.dv = box('macro').querySelector('.dv');
    C.cups = box('cups'); C.cupN = 0;
  })();
  function setArcs(parts) { // three shares that add up to 100
    var start = 0;
    for (var i = 0; i < 3; i++) {
      var len = Math.max(0, parts[i] - (parts[i] > 1.5 ? 0.8 : 0));
      C.arcs[i].style.strokeDasharray = len.toFixed(2) + ' 100'; C.arcs[i].style.strokeDashoffset = (-start).toFixed(2);
      start += parts[i];
    }
  }
  var CUP_MAX = 20, CUP = '<svg class="tl-cup" viewBox="0 0 20 26" aria-hidden="true" focusable="false"><path class="wa" d="M3.9 9H16.1L15 23Q14.9 24 13.4 24H6.6Q5.1 24 5 23Z"/><path class="ol" d="M3 2L5 23Q5.1 24.5 6.6 24.5H13.4Q14.9 24.5 15 23L17 2Z"/></svg>';
  function setCups(count) {
    var want = Math.min(CUP_MAX, count), more = C.cups.querySelector('.more');
    if (more) C.cups.removeChild(more);
    while (C.cupN < want) { var s = document.createElement('span'); s.innerHTML = CUP; s.style.animationDelay = (C.cupN % 10) * 35 + 'ms'; C.cups.appendChild(s); C.cupN++; }
    while (C.cupN > want) { C.cups.removeChild(C.cups.lastChild); C.cupN--; }
    if (count > CUP_MAX) { var m = document.createElement('b'); m.className = 'more num'; m.textContent = '+' + (count - CUP_MAX); C.cups.appendChild(m); }
  }

  function calc() {
    var male = sv('sex') !== 'f', goal = sv('goal') || 'keep', act = num('act');
    var meBad = check(['age', 'w', 'h']), meOk = !meBad.length;
    hint('me', meBad);
    var age = num('age'), w = num('w'), h = num('h');
    var bmiEl = el('bmi-cat');
    out('summary', [male ? T.male : T.female, (isFinite(age) ? raw('age') : '—') + ' ' + T.yrs, (isFinite(w) ? raw('w') : '—') + ' ' + T.kg, (isFinite(h) ? raw('h') : '—') + ' ' + T.cm].join(' · '));

    // ---- BMI + healthy range
    if (isFinite(w) && isFinite(h) && w > 0 && h > 0 && meOk) {
      var bmi = M.bmi(w, h), cls = M.bmiClass(bmi), hr = M.healthyRange(h);
      out('bmi', d1(bmi)); bmiEl.textContent = T[cls]; bmiEl.className = 'tl-tag ' + cls;
      pinTo(C.bmiSvg, bmi - 15, 25);
      out('healthy', d1(hr[0]) + '–' + d1(hr[1]) + ' ' + T.kg);
    } else { dash(['bmi', 'healthy']); bmiEl.textContent = ''; bmiEl.className = 'tl-tag'; pinTo(C.bmiSvg, null, 25); }

    // ---- calories + macros
    var gtag = el('goal-tag'); gtag.textContent = T[goal]; gtag.className = 'tl-tag goal-' + goal;
    out('adj-label', T['adj' + goal.charAt(0).toUpperCase() + goal.slice(1)]);
    if (meOk) {
      var bmr = M.bmr(male, w, h, age), tdee = bmr * act, g = M.target(goal, bmr, tdee), kcal = g.target, top = Math.max(bmr, tdee, kcal) || 1;
      out('kcal', n(kcal));
      setRow(C.cal[0], T.bmr, n(bmr) + ' ' + T.kcal, 0, bmr / top * 100);
      setRow(C.cal[1], T.tdee, n(tdee) + ' ' + T.kcal + ' (×' + act + ')', 0, tdee / top * 100);
      setRow(C.cal[2], T.target, n(kcal) + ' ' + T.kcal, 0, kcal / top * 100);
      out('adj', (g.delta > 0 ? '+' : g.delta < 0 ? '−' : '') + n(Math.abs(g.delta)) + ' ' + T.kcal);
      out('pace', goal === 'keep' ? T.paceKeep : fmt(T['pace' + goal.charAt(0).toUpperCase() + goal.slice(1)], { x: d1(Math.abs(g.perWeek)) }));
      show(el('floor'), g.floored);
      var link = el('cal-link'); if (link) { var base = link.getAttribute('href').split('?')[0]; link.setAttribute('href', base + '?target=' + kcal); }
      var mc = M.macros(goal, w, h, kcal), tot = mc.pk + mc.fk + mc.ck || 1;
      out('p', mc.p + ' g'); out('f', mc.f + ' g'); out('c', mc.c + ' g');
      out('p-sub', n(mc.pk) + ' ' + T.kcal + ' · ' + Math.round(mc.pk / tot * 100) + '%');
      out('f-sub', n(mc.fk) + ' ' + T.kcal + ' · ' + Math.round(mc.fk / tot * 100) + '%');
      out('c-sub', n(mc.ck) + ' ' + T.kcal + ' · ' + Math.round(mc.ck / tot * 100) + '%');
      setArcs([mc.pk / tot * 100, mc.fk / tot * 100, mc.ck / tot * 100]); C.dv.textContent = n(kcal);
      out('macro-note', fmt(T.macroNote, { p: d1(mc.p / w), f: d1(mc.f / w) }));
    } else {
      dash(['kcal', 'adj', 'pace', 'p', 'f', 'c']); out('p-sub', ''); out('f-sub', ''); out('c-sub', '');
      C.cal.forEach(function (r, i) { setRow(r, [T.bmr, T.tdee, T.target][i], '—', 0, 0); });
      setArcs([0, 0, 0]); C.dv.textContent = '—';
      show(el('floor'), false);
    }

    // ---- body fat (US Navy) + ideal weight
    var hipLabel = root.querySelector('[data-hip]'); show(hipLabel, !male);
    var bfNames = male ? ['neck', 'waist'] : ['neck', 'waist', 'hip'];
    var anyBf = bfNames.some(function (k) { return raw(k) !== ''; }), allBf = bfNames.every(function (k) { return raw(k) !== ''; });
    var bfBad = anyBf ? check(bfNames) : (check(['neck', 'waist', 'hip'], ['neck', 'waist', 'hip']), []);
    var bf = null;
    if (allBf && !bfBad.length && meOk) {
      bf = M.bodyFat(male, h, num('neck'), num('waist'), male ? 0 : num('hip'));
      if (bf === null) bfBad = [T.bfBad];
    }
    hint('bf', bfBad);
    var t = male ? [6, 14, 18, 25] : [14, 21, 25, 32];
    placeScale(C.bfSvg, [0, t[0], t[1], t[2], t[3], BF_MAX], BF_MAX, t.map(String));
    var bfCat = el('bf-cat');
    if (bf !== null) {
      var bc = M.bfClass(male, bf);
      out('bf', d1(bf) + ' %'); out('lean', d1(w * (1 - bf / 100)) + ' ' + T.kg);
      bfCat.textContent = T['bf' + bc]; bfCat.className = 'tl-tag bf' + bc; pinTo(C.bfSvg, bf, BF_MAX);
    } else { out('bf', '—'); out('lean', '—'); bfCat.textContent = ''; bfCat.className = 'tl-tag'; pinTo(C.bfSvg, null, BF_MAX); }
    if (meOk) { var dv = M.devine(male, h); out('ideal', n(dv * 0.9) + '–' + n(dv * 1.1) + ' ' + T.kg); out('cur-w', d1(w) + ' ' + T.kg); } else { out('ideal', '—'); out('cur-w', '—'); }

    // ---- 1RM
    var ob = check(['lw', 'lr']); hint('orm', ob);
    if (!ob.length && Number.isInteger(num('lr'))) {
      var lw = num('lw'), lr = num('lr'), orm = M.orm(lw, lr);
      out('orm', d1(orm) + ' kg');
      [[100, 1]].concat(M.pctTable).forEach(function (x, i) {
        setRow(C.orm[i], x[0] + '% · ' + x[1] + ' ' + T.reps, d1(orm * x[0] / 100) + ' kg', 0, x[0]);
      });
    } else {
      out('orm', '—');
      C.orm.forEach(function (r) { setRow(r, '', '', 0, 0); });
      if (!ob.length) hint('orm', [T.ormBad]);
    }

    // ---- water
    var wb = check(['tm']); hint('water', wb);
    if (meOk && !wb.length) {
      var litres = M.water(w, num('tm'), input('hot').checked), glasses = Math.round(litres * 4);
      out('water', d1(litres)); out('glasses', fmt(T.glasses, { n: glasses })); setCups(glasses);
    } else { out('water', '—'); out('glasses', ''); setCups(0); }

    // ---- heart-rate zones: each bar spans its bpm range on a scale from 40 % of max to max
    var hb = check(['rhr'], ['rhr']); hint('hr', hb);
    if (isFinite(age) && age >= 14 && age <= 90 && !hb.length) {
      var rest = raw('rhr') === '' ? 0 : num('rhr'), zs = M.zones(age, rest), mx = M.hrMax(age), lo = Math.round(mx * 0.4);
      out('hrmax', Math.round(mx) + ' ' + T.bpm);
      out('hr-help', fmt(rest > 0 ? T.hrKarvonen : T.hrSimple, { m: Math.round(mx) }));
      M.zonePcts.forEach(function (z, i) {
        var a = clamp((zs[i][0] - lo) / (mx - lo) * 100, 0, 100), b = (zs[i][1] - lo) / (mx - lo) * 100;
        setRow(C.zones[i], T['z' + (i + 1)], zs[i][0] + '–' + zs[i][1] + ' ' + T.bpm, a, b - a);
      });
    } else { out('hrmax', '—'); C.zones.forEach(function (r, i) { setRow(r, T['z' + (i + 1)], '—', 0, 0); }); }
  }

  // ---- remember inputs (per browser) and prefill from the member's profile
  var FIELDS = ['age', 'w', 'h', 'act', 'lw', 'lr', 'tm', 'rhr', 'neck', 'waist', 'hip'];
  function load() {
    var s = {};
    try { s = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { s = {}; }
    FIELDS.forEach(function (k) { if (s[k] !== undefined && s[k] !== null && input(k)) input(k).value = s[k]; });
    ['sex', 'goal'].forEach(function (k) { var r = s[k] && root.querySelector('[name="' + k + '"][value="' + s[k] + '"]'); if (r) r.checked = true; });
    if (s.hot) input('hot').checked = true;
    else if (!s.goal) { // first visit: start from the member's profile goal
      var pg = root.dataset.goal, r2 = (pg === 'lose' || pg === 'gain') && root.querySelector('[name="goal"][value="' + pg + '"]');
      if (r2) r2.checked = true;
    }
    var used = false, pw = parseFloat(root.dataset.profileW), ph = parseFloat(root.dataset.profileH), bd = root.dataset.birth;
    if (pw >= 30 && pw <= 250) { input('w').value = pw; used = true; }
    if (ph >= 120 && ph <= 230) { input('h').value = ph; used = true; }
    if (bd) {
      var b = new Date(bd), t = new Date(), a = t.getFullYear() - b.getFullYear();
      if (t.getMonth() < b.getMonth() || (t.getMonth() === b.getMonth() && t.getDate() < b.getDate())) a--;
      if (a >= 14 && a <= 90) { input('age').value = a; used = true; }
    }
    show(el('from-profile'), used);
  }
  function save() {
    var s = {};
    FIELDS.forEach(function (k) { s[k] = raw(k); });
    s.sex = sv('sex'); s.goal = sv('goal'); s.hot = input('hot').checked;
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode: just don't remember */ }
  }
  function update() { calc(); save(); }
  root.addEventListener('input', update);
  root.addEventListener('change', update);
  load();
  calc();

  // ---- "Natijani saqlash" (members only): weight + height become today's body measurement, the goal becomes the profile goal
  var saveBtn = root.querySelector('[data-save]'), toastEl = document.getElementById('tl-toast'), toastTimer, goalTouched = false;
  function toast(text, ok) {
    if (!toastEl) return;
    toastEl.textContent = '';
    var i = document.createElement('span'); i.className = 'ct-ico'; i.textContent = ok ? '✓' : '!';
    var s = document.createElement('span'); s.textContent = text;
    toastEl.appendChild(i); toastEl.appendChild(s);
    toastEl.className = 'cart-toast' + (ok ? '' : ' bad');
    toastEl.hidden = false;
    void toastEl.offsetWidth; toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); setTimeout(function () { toastEl.hidden = true; }, 300); }, 2600);
  }
  if (saveBtn) {
    root.addEventListener('change', function (e) { if (e.target && e.target.name === 'goal') goalTouched = true; });
    saveBtn.addEventListener('click', function () {
      var bad = check(['w', 'h']);
      if (bad.length) { toast(bad[0], false); return; }
      // the calculators know lose / keep / gain only: a profile goal such as "strength" is overwritten only when the member picks one here
      var send = goalTouched || ['', 'lose', 'keep', 'gain'].indexOf(root.dataset.goal || '') >= 0;
      var body = new URLSearchParams({ weight: String(num('w')), height: String(Math.round(num('h'))) });
      if (send) body.set('goal', sv('goal') || 'keep');
      var token = root.querySelector('[name=csrfmiddlewaretoken]');
      saveBtn.disabled = true;
      fetch(saveBtn.dataset.url, { method: 'POST', credentials: 'same-origin', body: body,
        headers: { 'X-CSRFToken': token ? token.value : '', 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j && j.ok) { if (send) root.dataset.goal = j.goal; toast(j.message, true); }
          else toast((j && j.error) || T.net, false);
        })
        .catch(function () { toast(T.net, false); })
        .then(function () { saveBtn.disabled = false; });
    });
  }

  // ---- tabs: #tana / #ovqat / #mashq deep links, last tab remembered per browser
  var TABS = ['tana', 'ovqat', 'mashq'];
  function selectTab(name, focus, keepHash) {
    if (TABS.indexOf(name) < 0) name = TABS[0];
    TABS.forEach(function (t) {
      var tab = document.getElementById('tl-tab-' + t), panel = document.getElementById('tl-panel-' + t), on = t === name;
      tab.setAttribute('aria-selected', on ? 'true' : 'false'); tab.tabIndex = on ? 0 : -1; panel.hidden = !on;
    });
    var cur = document.getElementById('tl-tab-' + name);
    if (focus) cur.focus();
    if (cur.scrollIntoView) cur.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    try { localStorage.setItem(TABKEY, name); } catch (e) { /* private mode */ }
    if (!keepHash) { try { history.replaceState(null, '', '#' + name); } catch (e) { /* ignore */ } }
  }
  var tablist = root.querySelector('[role=tablist]');
  tablist.addEventListener('click', function (e) { var b = e.target.closest('[role=tab]'); if (b) selectTab(b.dataset.tab, false); });
  tablist.addEventListener('keydown', function (e) {
    var i = TABS.indexOf(e.target.dataset && e.target.dataset.tab), to = -1;
    if (i < 0) return;
    if (e.key === 'ArrowRight') to = (i + 1) % TABS.length;
    else if (e.key === 'ArrowLeft') to = (i + TABS.length - 1) % TABS.length;
    else if (e.key === 'Home') to = 0;
    else if (e.key === 'End') to = TABS.length - 1;
    if (to >= 0) { e.preventDefault(); selectTab(TABS[to], true); }
  });
  global.addEventListener('hashchange', function () { var h2 = location.hash.slice(1); if (TABS.indexOf(h2) >= 0) selectTab(h2, false, true); });
  (function initTab() {
    var start = location.hash.slice(1), saved = '';
    if (TABS.indexOf(start) < 0) { try { saved = localStorage.getItem(TABKEY) || ''; } catch (e) { saved = ''; } start = saved; }
    selectTab(TABS.indexOf(start) >= 0 ? start : TABS[0], false, true);
  })();

  // ---- "Ma'lumotlarim" collapses on phones (CSS shows it permanently on wide screens)
  var side = root.querySelector('.tl-side'), tgl = root.querySelector('.tl-me-toggle');
  tgl.addEventListener('click', function () { var o = side.classList.toggle('is-open'); tgl.setAttribute('aria-expanded', o ? 'true' : 'false'); });
})(window);
