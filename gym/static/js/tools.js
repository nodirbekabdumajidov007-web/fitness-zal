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
  var T = document.getElementById('tl-i18n').dataset, KEY = 'fz_tools_v2', NB = ' ';
  var RULES = { age: [14, 90], w: [30, 250], h: [120, 230], lw: [1, 500], lr: [1, 12], tm: [0, 300], rhr: [30, 120], neck: [25, 60], waist: [50, 200], hip: [60, 200] };

  function input(name) { return root.querySelector('[name="' + name + '"]'); }
  function raw(name) { var e = input(name); return e ? String(e.value).trim() : ''; }
  function num(name) { var s = raw(name).replace(',', '.'); return s === '' ? NaN : Number(s); }
  function sv(name) { var e = root.querySelector('[name="' + name + '"]:checked'); return e ? e.value : ''; }
  function out(k, text) { root.querySelectorAll('[data-out="' + k + '"]').forEach(function (e) { e.textContent = text; }); }
  function el(k) { return root.querySelector('[data-out="' + k + '"]'); }
  function show(node, on) { if (node) node.hidden = !on; }
  function n(x) { return Math.round(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g, NB); }
  function d1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
  function fmt(s, o) { return String(s).replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); }

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

  function calc() {
    var male = sv('sex') !== 'f', goal = sv('goal') || 'keep', act = num('act');
    var meBad = check(['age', 'w', 'h']), meOk = !meBad.length;
    hint('me', meBad);
    var age = num('age'), w = num('w'), h = num('h');
    var bmiEl = el('bmi-cat'), pin = el('bmi-pin');

    // ---- BMI + healthy range
    if (isFinite(w) && isFinite(h) && w > 0 && h > 0 && meOk) {
      var bmi = M.bmi(w, h), cls = M.bmiClass(bmi), hr = M.healthyRange(h);
      out('bmi', d1(bmi)); bmiEl.textContent = T[cls]; bmiEl.className = 'tl-tag ' + cls;
      pin.style.left = Math.max(0, Math.min(100, (bmi - 15) / 25 * 100)) + '%';
      out('healthy', d1(hr[0]) + '–' + d1(hr[1]) + ' ' + T.kg);
    } else { dash(['bmi', 'healthy']); bmiEl.textContent = ''; bmiEl.className = 'tl-tag'; pin.style.left = '0%'; }

    // ---- calories + macros
    var gtag = el('goal-tag'); gtag.textContent = T[goal]; gtag.className = 'tl-tag goal-' + goal;
    ['adj-label'].forEach(function (k) { out(k, T['adj' + goal.charAt(0).toUpperCase() + goal.slice(1)]); });
    if (meOk) {
      var bmr = M.bmr(male, w, h, age), tdee = bmr * act, g = M.target(goal, bmr, tdee), kcal = g.target;
      out('bmr', n(bmr) + ' ' + T.kcal); out('tdee', n(tdee) + ' ' + T.kcal + ' (×' + act + ')');
      out('kcal', n(kcal)); out('kcal2', n(kcal));
      out('adj', (g.delta > 0 ? '+' : g.delta < 0 ? '−' : '') + n(Math.abs(g.delta)) + ' ' + T.kcal);
      out('pace', goal === 'keep' ? T.paceKeep : fmt(T['pace' + goal.charAt(0).toUpperCase() + goal.slice(1)], { x: d1(Math.abs(g.perWeek)) }));
      show(el('floor'), g.floored);
      var link = el('cal-link'); if (link) { var base = link.getAttribute('href').split('?')[0]; link.setAttribute('href', base + '?target=' + kcal); }
      var mc = M.macros(goal, w, h, kcal), tot = mc.pk + mc.fk + mc.ck || 1;
      out('p', mc.p + ' g'); out('f', mc.f + ' g'); out('c', mc.c + ' g');
      out('p-sub', n(mc.pk) + ' ' + T.kcal + ' · ' + Math.round(mc.pk / tot * 100) + '%');
      out('f-sub', n(mc.fk) + ' ' + T.kcal + ' · ' + Math.round(mc.fk / tot * 100) + '%');
      out('c-sub', n(mc.ck) + ' ' + T.kcal + ' · ' + Math.round(mc.ck / tot * 100) + '%');
      var pp = mc.pk / tot * 100, fp = mc.fk / tot * 100, dn = el('donut');
      dn.style.setProperty('--p', pp.toFixed(1)); dn.style.setProperty('--f', (pp + fp).toFixed(1));
      out('macro-note', fmt(T.macroNote, { p: d1(mc.p / w), f: d1(mc.f / w) }));
    } else {
      dash(['bmr', 'tdee', 'kcal', 'kcal2', 'adj', 'pace', 'p', 'f', 'c']); out('p-sub', ''); out('f-sub', ''); out('c-sub', '');
      show(el('floor'), false);
    }

    // ---- body fat + ideal weight (US Navy)
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
    var bfCat = el('bf-cat');
    if (bf !== null) {
      var bc = M.bfClass(male, bf);
      out('bf', d1(bf) + ' %'); out('lean', d1(w * (1 - bf / 100)) + ' ' + T.kg);
      bfCat.textContent = T['bf' + bc]; bfCat.className = 'tl-tag bf' + bc;
    } else { out('bf', '—'); out('lean', '—'); bfCat.textContent = ''; bfCat.className = 'tl-tag'; }
    if (meOk) { var dv = M.devine(male, h); out('ideal', n(dv * 0.9) + '–' + n(dv * 1.1) + ' ' + T.kg); } else out('ideal', '—');

    // ---- 1RM
    var ob = check(['lw', 'lr']), pct = el('pct'); pct.innerHTML = ''; hint('orm', ob);
    if (!ob.length && Number.isInteger(num('lr'))) {
      var lw = num('lw'), lr = num('lr'), orm = M.orm(lw, lr);
      out('orm', d1(orm) + ' kg');
      M.pctTable.forEach(function (x) {
        var s = document.createElement('span'); s.innerHTML = '<b></b><small></small>';
        s.querySelector('b').textContent = d1(orm * x[0] / 100) + ' kg';
        s.querySelector('small').textContent = x[0] + '% · ' + x[1] + ' ' + T.reps; pct.appendChild(s);
      });
    } else {
      out('orm', '—');
      if (!ob.length) hint('orm', [T.ormBad]);
    }

    // ---- water
    var wb = check(['tm']); hint('water', wb);
    var cups = el('cups'); cups.innerHTML = '';
    if (meOk && !wb.length) {
      var litres = M.water(w, num('tm'), input('hot').checked), glasses = Math.round(litres * 4);
      out('water', d1(litres)); out('glasses', fmt(T.glasses, { n: glasses }));
      for (var i = 0; i < Math.min(16, glasses); i++) { var cu = document.createElement('i'); cu.style.animationDelay = i * 40 + 'ms'; cups.appendChild(cu); }
    } else { out('water', '—'); out('glasses', ''); }

    // ---- heart-rate zones
    var hb = check(['rhr'], ['rhr']); hint('hr', hb);
    var zones = el('zones'); zones.innerHTML = '';
    if (isFinite(age) && age >= 14 && age <= 90 && !hb.length) {
      var rest = raw('rhr') === '' ? 0 : num('rhr'), zs = M.zones(age, rest);
      out('hrmax', Math.round(M.hrMax(age)) + ' ' + T.bpm);
      out('hr-help', fmt(rest > 0 ? T.hrKarvonen : T.hrSimple, { m: Math.round(M.hrMax(age)) }));
      M.zonePcts.forEach(function (z, i) {
        var r = document.createElement('div'); r.className = 'tl-zone z' + (i + 1);
        r.innerHTML = '<span class="nm"></span><b class="num"></b><span class="bar"><i></i></span>';
        r.querySelector('.nm').textContent = T['z' + (i + 1)];
        r.querySelector('i').style.width = z[1] + '%';
        r.querySelector('b').textContent = zs[i][0] + '–' + zs[i][1] + ' ' + T.bpm;
        zones.appendChild(r);
      });
    } else out('hrmax', '—');
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
})(window);
