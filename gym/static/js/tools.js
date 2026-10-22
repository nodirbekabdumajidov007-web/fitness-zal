/* Fitness calculators. Everything is computed here in the browser and updates as you type.
   BMI = kg / m²; calories: Mifflin–St Jeor BMR × activity, ± goal; macros: protein 2 g/kg, fat 25 % of calories, the rest carbs;
   1RM: Epley; water: 35 ml/kg + 12 ml per training minute; heart-rate zones: Karvonen (max HR = 220 − age). */
(function () {
  var root = document.querySelector('[data-tools]');
  if (!root) return;
  var T = document.getElementById('tl-i18n').dataset;
  function v(name) { var el = root.querySelector('[name="' + name + '"]:checked') || root.querySelector('[name="' + name + '"]'); return parseFloat(el && el.value) || 0; }
  function sv(name) { var el = root.querySelector('[name="' + name + '"]:checked'); return el ? el.value : ''; }
  function out(k, text) { root.querySelectorAll('[data-out="' + k + '"]').forEach(function (e) { e.textContent = text; }); }
  function el(k) { return root.querySelector('[data-out="' + k + '"]'); }
  function n(x) { return Math.round(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }

  function calc() {
    var age = v('age'), w = v('w'), h = v('h'), act = v('act'), goal = v('goal'), male = sv('sex') !== 'f';
    // BMI
    var bmi = w && h ? w / Math.pow(h / 100, 2) : 0;
    out('bmi', bmi ? bmi.toFixed(1) : '—');
    var cat = bmi < 18.5 ? ['under', T.under] : bmi < 25 ? ['normal', T.normal] : bmi < 30 ? ['over', T.over] : ['obese', T.obese];
    var tag = el('bmi-cat'); tag.textContent = bmi ? cat[1] : ''; tag.className = 'tl-tag ' + (bmi ? cat[0] : '');
    el('bmi-pin').style.left = Math.max(0, Math.min(100, (bmi - 15) / (40 - 15) * 100)) + '%';
    // calories
    var bmr = 10 * w + 6.25 * h - 5 * age + (male ? 5 : -161), tdee = bmr * act, kcal = Math.max(1200, tdee + goal);
    out('bmr', n(bmr)); out('tdee', n(tdee)); out('kcal', n(kcal)); out('kcal2', n(kcal));
    // macros
    var p = 2 * w, f = kcal * 0.25 / 9, c = Math.max(0, (kcal - p * 4 - f * 9) / 4);
    out('p', n(p) + ' g'); out('f', n(f) + ' g'); out('c', n(c) + ' g');
    var pp = p * 4 / kcal * 100, fp = f * 9 / kcal * 100;
    el('donut').style.setProperty('--p', pp.toFixed(1)); el('donut').style.setProperty('--f', (pp + fp).toFixed(1));
    // 1RM
    var lw = v('lw'), lr = Math.max(1, v('lr')), orm = lr === 1 ? lw : lw * (1 + lr / 30);
    out('orm', orm ? orm.toFixed(1) + ' kg' : '—');
    var pct = el('pct'); pct.innerHTML = '';
    [[95, 2], [90, 4], [85, 6], [80, 8], [75, 10], [70, 12]].forEach(function (x) {
      var s = document.createElement('span'); s.innerHTML = '<b></b><small></small>';
      s.querySelector('b').textContent = (orm * x[0] / 100).toFixed(1) + ' kg';
      s.querySelector('small').textContent = x[0] + '% · ' + x[1] + ' ' + T.reps; pct.appendChild(s);
    });
    // water
    var litres = (w * 35 + v('tm') * 12) / 1000;
    out('water', litres.toFixed(1));
    var cups = el('cups'); cups.innerHTML = '';
    for (var i = 0; i < Math.min(16, Math.round(litres / 0.25)); i++) { var cu = document.createElement('i'); cu.style.animationDelay = i * 40 + 'ms'; cups.appendChild(cu); }
    // heart-rate zones
    var max = 220 - age, rest = v('rhr'), reserve = max - rest, zones = el('zones'); zones.innerHTML = '';
    [[50, 60, T.z1], [60, 70, T.z2], [70, 80, T.z3], [80, 90, T.z4], [90, 100, T.z5]].forEach(function (z, i) {
      var r = document.createElement('div'); r.className = 'tl-zone z' + (i + 1);
      r.innerHTML = '<span class="nm"></span><span class="bar"><i></i></span><b class="num"></b>';
      r.querySelector('.nm').textContent = z[2];
      r.querySelector('i').style.width = z[1] + '%';
      r.querySelector('b').textContent = Math.round(rest + reserve * z[0] / 100) + '–' + Math.round(rest + reserve * z[1] / 100);
      zones.appendChild(r);
    });
  }
  root.addEventListener('input', calc);
  root.addEventListener('change', calc);
  calc();
})();
