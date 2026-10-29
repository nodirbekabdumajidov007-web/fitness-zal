/* Voice assistant ("Ovozli yordamchi"): the browser's Web Speech API listens (SpeechRecognition) and speaks (speechSynthesis).
   Order of work: 1) food logging via the built-in table, 2) gym facts from /voice/info/, 3) opening pages, 4) the knowledge base /assistant/ask/, else a friendly "don't know yet".
   Strings and settings come from <script type="application/json" id="voice-i18n"> (not executable, so the CSP allows it). */
(function () {
  var cfgEl = document.getElementById('voice-i18n');
  var btn = document.getElementById('vmic'), panel = document.getElementById('vpanel');
  if (!cfgEl || !btn || !panel) return;
  var C;
  try { C = JSON.parse(cfgEl.textContent); } catch (e) { return; }
  var T = {};
  Object.keys(C.t || {}).forEach(function (k) { T[k.replace(/-/g, '_')] = C.t[k]; });  // the server sends keys with hyphens
  var $ = function (id) { return document.getElementById(id); };
  var big = $('vbig'), stateEl = $('vstate'), heard = $('vheard'), ans = $('vanswer'), warn = $('vwarn'), form = $('vform'),
      text = $('vtext'), spk = $('vspk'), closeBtn = $('vclose');
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var rec = null, listening = false, busy = false, infoCache = null, infoAt = 0;

  function fmt(s, o) { return String(s || '').replace(/\{(\w+)\}/g, function (m, k) { return o && o[k] != null ? o[k] : m; }); }
  function norm(s) {  // lower case, apostrophes dropped (do'kon -> dokon), punctuation to spaces
    return String(s || '').toLowerCase().replace(/[ʻʼ’‘`´']/g, '').replace(/ё/g, 'е')
      .replace(/[^\p{L}\p{N}\s]/gu, ' ').replace(/\s+/g, ' ').trim();
  }
  function money(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' ' + (T.price_unit || ''); }

  // ------------------------------------------------------------ text-to-speech
  var ttsOn = true;
  try { ttsOn = localStorage.getItem('fz_voice_tts') !== '0'; } catch (e) {}
  function paintSpeaker() {
    spk.setAttribute('aria-pressed', ttsOn ? 'true' : 'false');
    var l = ttsOn ? T.vc_speaker_on : T.vc_speaker_off;
    spk.setAttribute('aria-label', l); spk.title = l;
  }
  paintSpeaker();
  spk.addEventListener('click', function () {
    ttsOn = !ttsOn;
    try { localStorage.setItem('fz_voice_tts', ttsOn ? '1' : '0'); } catch (e) {}
    if (!ttsOn) stopSpeak();
    paintSpeaker();
  });
  function stopSpeak() { try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) {} }
  function pickVoice() {
    var vs = [];
    try { vs = window.speechSynthesis.getVoices() || []; } catch (e) {}
    var base = C.lang, best = null;
    vs.forEach(function (v) {
      var l = String(v.lang || '').toLowerCase().replace('_', '-');
      if (l.indexOf(base) !== 0) return;
      if (!best || l === C.speechLang.toLowerCase() && String(best.lang).toLowerCase() !== C.speechLang.toLowerCase()) best = v;
    });
    return best;
  }
  function speak(s) {
    if (!ttsOn || !window.speechSynthesis || !window.SpeechSynthesisUtterance || !s) return;
    try {
      var v = pickVoice();
      if (!v && C.lang === 'uz') return;  // Uzbek voices are rare: the text answer is enough, a Russian voice would mispronounce it
      stopSpeak();
      var u = new SpeechSynthesisUtterance(s);
      u.lang = v ? v.lang : C.speechLang;
      if (v) u.voice = v;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  // ------------------------------------------------------------ output
  function plain(s, bullets) {  // markdown -> plain text (the answer is shown and read out as text, never as HTML)
    return String(s || '').replace(/```[\s\S]*?```/g, ' ').replace(/`([^`]*)`/g, '$1').replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/^\s{0,3}#{1,6}\s+/gm, '').replace(/(\*\*|__)(.+?)\1/g, '$2').replace(/(^|[\s(])[*_]([^*_\n]+)[*_](?=[\s).,!?]|$)/g, '$1$2')
      .replace(/^\s*[-*•]\s+/gm, bullets ? '• ' : '').replace(/^\s*\d+[.)]\s+/gm, '').replace(/\n{3,}/g, '\n\n').trim();
  }
  function say(msg, link, spoken) {
    ans.hidden = false; ans.textContent = '';
    ans.appendChild(document.createTextNode(msg));
    if (link) {
      var a = document.createElement('a'); a.href = link.url; a.textContent = link.label;
      ans.appendChild(document.createTextNode(' ')); ans.appendChild(a);
    }
    speak(spoken != null ? spoken : msg);
  }
  function setState(s) { stateEl.textContent = s; }
  function idleState() { setState(SR ? T.vc_idle : ''); }
  function setListening(on) {
    listening = on;
    panel.classList.toggle('listening', on);
    big.setAttribute('aria-label', on ? T.vc_stop : T.vc_start);
    if (on) setState(T.vc_listening); else if (!busy) idleState();
  }

  // ------------------------------------------------------------ data
  function csrf() { var i = panel.querySelector('[name=csrfmiddlewaretoken]'); return i ? i.value : ''; }
  function post(url, fields) {
    var body = new FormData();
    Object.keys(fields).forEach(function (k) { body.append(k, fields[k]); });
    return fetch(url, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' } });
  }
  function getInfo() {
    if (infoCache && Date.now() - infoAt < 60000) return Promise.resolve(infoCache);
    return fetch(C.urls.info, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { if (!r.ok) throw new Error('info'); return r.json(); })
      .then(function (d) { infoCache = d; infoAt = Date.now(); return d; });
  }

  // ------------------------------------------------------------ intents
  var PAGE_RULES = [  // order matters: the first match wins
    ['ai', /(murabbiy yordamchi|ai (murabbiy|trener|coach)|аи тренер|ai тренер|ии тренер|aytrener|ai yordamchi|помощник[- ]тренер|coach assistant|искусствен)/],
    ['account', /(akkaunt|hisob sozlam|sozlamalar|настройк|аккаунт|account|settings)/],
    ['profile', /(profil|профил)/],
    ['cart', /(savat|корзин|\bcart\b|basket)/],
    ['plans', /(abonement|obuna|членств|абонемент|membership|plans|subscription)/],
    ['shop', /(dokon|магазин|\bshop\b|\bstore\b|mahsulot|товар)/],
    ['classes', /(mashgulot|dars jadval|занят|расписан|classes|schedule)/],
    ['trainers', /(murabbiy|trener|тренер|trainer|coach)/],
    ['calories', /(kaloriy|калори|calorie)/],
    ['dashboard', /(kabinet|кабинет|dashboard|shaxsiy)/],
    ['chat', /(\bchat\b|чат|xabarlar|сообщен|messages)/],
    ['tools', /(kalkulyator|калькулятор|calculator|asboblar|\btools\b)/],
    ['reviews', /(fikr|sharh|отзыв|review|feedback)/],
    ['home', /(bosh sahifa|asosiy sahifa|главн|домой|\bhome\b|homepage|main page)/]
  ];
  var NAV_VERB = /(\boch|otish|otkaz|\bket\b|\bbor\b|korsat|открой|открыть|перейди|перейти|покажи|зайди|go to|open|show me|take me|navigate)/;
  var INFO_RULES = [
    ['hours', /(ish vaqti|ishlash vaqti|soat nechada|nechagacha|qachon (ochil|yopil|ochiq)|ochiqmi|yopiqmi|часы работы|график|режим работы|во сколько|до скольки|открыто|открыты|работает|opening|open now|are you open|working hours|what time|hours|closing time)/],
    ['phone', /(telefon|nomer|raqam|номер|телефон|позвон|phone|call you|contact number)/],
    ['address', /(manzil|adres|адрес|где (вы|находится|зал)|qayerdasiz|joylashuv|joylashgan|address|where are you|where is the gym|location)/],
    ['social', /(instagram|инстаграм|telegram|телеграм)/],
    ['crowd', /(odam (kop|kam|bor)|\bband\b|tirband|gavjum|народ|людей|загружен|многолюдно|crowd|\bbusy\b|how full|packed)/]
  ];
  var PRICE = /(narx|qancha|necha pul|pul turadi|tarif|цен|стоим|прайс|price|cost|how much)/;
  var PLAN_STEM = PAGE_RULES[4][1];
  var EAT = /(yedim|yedik|yeb |yeyman|ichdim|qosh |qoshing|съел|поел|выпил|добав|\bate\b|eaten|\bhad\b|drank|\badd\b|\blog\b)/;

  function pageOf(n) {
    for (var i = 0; i < PAGE_RULES.length; i++) if (PAGE_RULES[i][1].test(n)) return PAGE_RULES[i][0];
    return null;
  }
  function go(id) {
    var p = C.pages[id]; if (!p) return false;
    say(fmt(T.vc_going, { page: p.label }));
    setTimeout(function () { window.location.href = p.url; }, 900);
    return true;
  }

  // ---- foods: the server recognises them (/calories/parse/: ~600 built-in foods plus the member's own), so there is no table here
  var NUM_WORDS = { bir: 1, bitta: 1, ikki: 2, ikkita: 2, uch: 3, uchta: 3, tort: 4, tortta: 4, besh: 5, beshta: 5, olti: 6, oltita: 6, yetti: 7, yettita: 7,
    sakkiz: 8, sakkizta: 8, toqqiz: 9, toqqizta: 9, 'один': 1, 'одна': 1, 'одну': 1, 'два': 2, 'две': 2,
    'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6 };
  function mealOf(n) {
    if (/(nonushta|завтрак|breakfast)/.test(n)) return 'breakfast';
    if (/(tushlik|обед|lunch)/.test(n)) return 'lunch';
    if (/(kechki|kechlik|ужин|dinner|supper)/.test(n)) return 'dinner';
    if (/(gazak|перекус|snack)/.test(n)) return 'snack';
    var h = new Date().getHours();
    return h < 11 ? 'breakfast' : (h < 16 ? 'lunch' : (h < 21 ? 'dinner' : 'snack'));
  }

  function addLocal(items, meal) {
    return items.reduce(function (p, it) {
      return p.then(function () {
        return post(C.urls.calAdd, { food: it.idx, grams: it.grams, meal: meal }).then(function (r) { if (!r.ok) throw new Error('add'); });
      });
    }, Promise.resolve());
  }
  function doneFood(label) {
    say(fmt(T.vc_added, { items: label }), { url: C.urls.calories, label: T.nav_calories });
  }
  function logFood(raw, n) {
    if (!C.auth) { say(T.vc_login_cal, { url: C.urls.login, label: T.vc_login }); return Promise.resolve(); }
    var meal = mealOf(n);
    // the server does the matching; a failed request means "no items" and the friendly help text
    var parsed = post(C.urls.calParse, { text: raw }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { return d && d.ok ? d.items : []; }).catch(function () { return []; });
    return parsed.then(function (items) {
      var hasNum = /\d/.test(n) || n.split(' ').some(function (w) { return NUM_WORDS[w] != null; });
      var local = function () {
        return addLocal(items, meal).then(function () {
          doneFood(items.map(function (it) { return it.name + ' ' + it.grams + ' g'; }).join(', '));
        });
      };
      if (!items.length && !hasNum && /(nima|что|what)/.test(n)) {  // "what did I eat today" -> the calorie page
        say(T.vc_cal_open); setTimeout(function () { window.location.href = C.urls.calories; }, 1200); return null;
      }
      if (items.length) {
        return local().catch(function () { say(T.vc_error); });
      }
      say(T.vc_cal_unknown); return null;
    });
  }

  function infoAnswer(kind, n) {
    return getInfo().then(function (d) {
      if (kind === 'hours') say(fmt(T.vc_hours, { open: d.open, close: d.close, state: d.is_open ? T.vc_state_open : T.vc_state_closed }));
      else if (kind === 'phone') say(fmt(T.vc_phone, { phone: d.phone }));
      else if (kind === 'address') say(d.address ? fmt(T.vc_address, { address: d.address }) : fmt(T.vc_no_address, { phone: d.phone }));
      else if (kind === 'social') say(fmt(T.vc_social, { instagram: d.instagram, telegram: d.telegram }));
      else if (kind === 'crowd') say(T['vc_crowd_' + d.crowd] || T.vc_crowd_mid);
      else if (kind === 'plans') {
        if (!d.plans || !d.plans.length) say(T.vc_no_plans);
        else say(fmt(T.vc_plans, { list: d.plans.map(function (p) { return p.name + ' — ' + money(p.price); }).join('; ') }),
          { url: C.pages.plans.url, label: C.pages.plans.label });
      }
    });
  }

  // our own knowledge base (/assistant/ask/): 404, network error or an "unknown" answer means no match
  function askKB(raw) {
    return post(C.urls.assistant, { q: raw, lang: C.lang }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || !d.ok || !d.answer || d.matched === false) return false;  // unmatched: the friendly help text is shown instead
      var link = d.links && d.links[0] ? { url: d.links[0].url, label: d.links[0].label } : null;
      say(plain(d.answer, true), link, plain(d.answer, false));
      return true;
    }).catch(function () { return false; });
  }
  function fallback(raw) {
    setState(T.vc_thinking);
    return askKB(raw).then(function (found) { if (!found) say(T.vc_help); return null; });
  }

  // one utterance in, one action out; returns a promise
  function handle(raw) {
    raw = String(raw || '').trim();
    if (!raw || busy) return Promise.resolve();
    busy = true; stopSpeak();
    heard.textContent = raw; heard.classList.remove('interim');
    ans.hidden = true;
    var n = norm(raw), words = n.split(' ').length, p = null;
    var run;
    try {
      var pg = pageOf(n);
      if (EAT.test(n + ' ') && (/\d/.test(n) || !pg || /(yedim|съел|\bate\b)/.test(n))) run = logFood(raw, n);
      else {
        var kind = null;
        INFO_RULES.forEach(function (r) { if (!kind && r[1].test(n)) kind = r[0]; });
        if (!kind && PRICE.test(n) && (PLAN_STEM.test(n) || !pg)) kind = 'plans';
        if (kind) run = infoAnswer(kind, n);
        else if (pg && (words <= 5 || NAV_VERB.test(n))) { go(pg); run = Promise.resolve(); }
        else run = fallback(raw);
      }
    } catch (e) { run = Promise.reject(e); }
    return Promise.resolve(run).catch(function () { say(T.vc_error); }).then(function () { busy = false; if (!listening) idleState(); });
  }

  // ------------------------------------------------------------ speech recognition
  function startListen() {
    if (!SR || listening || busy) return;
    stopSpeak();
    var finalText = '', err = null;
    try { rec = new SR(); } catch (e) { return; }
    rec.lang = C.speechLang; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
    rec.onstart = function () { setListening(true); heard.textContent = ''; ans.hidden = true; };
    rec.onresult = function (e) {
      var interim = '';
      for (var i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalText += e.results[i][0].transcript; else interim += e.results[i][0].transcript;
      }
      heard.textContent = (finalText + ' ' + interim).trim();
      heard.classList.toggle('interim', !finalText && !!interim);
    };
    rec.onerror = function (e) { err = e.error; };
    rec.onend = function () {
      setListening(false);
      if (finalText.trim()) { handle(finalText); return; }
      if (err === 'not-allowed' || err === 'service-not-allowed') say(T.vc_mic_denied);
      else if (err === 'no-speech' || !err) { if (panel.hidden) return; say(T.vc_no_speech); }
      else if (err !== 'aborted') say(T.vc_error);
    };
    try { rec.start(); } catch (e) { setListening(false); }
  }
  function stopListen() { try { if (rec) rec.stop(); } catch (e) {} }

  // ------------------------------------------------------------ panel
  function open() {
    panel.hidden = false; btn.setAttribute('aria-expanded', 'true');
    if (SR) { big.focus(); startListen(); } else text.focus();
  }
  function close() {
    try { if (rec) { rec.onend = null; rec.abort(); } } catch (e) {}
    setListening(false); stopSpeak();
    panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus();
  }
  if (!SR) { panel.classList.add('nomic'); warn.hidden = false; }
  idleState();
  btn.addEventListener('click', function () { if (panel.hidden) open(); else close(); });
  closeBtn.addEventListener('click', close);
  big.addEventListener('click', function () { if (listening) stopListen(); else startListen(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) { e.preventDefault(); close(); } });
  form.addEventListener('submit', function (e) { e.preventDefault(); var v = text.value; text.value = ''; handle(v); });
  panel.querySelectorAll('[data-vchip]').forEach(function (c) {
    c.addEventListener('click', function () { handle(c.textContent); });
  });
  window.FZVoice = { handle: handle, open: open, close: close, norm: norm };
})();
