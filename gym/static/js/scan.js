/* Front-desk QR scanning, shared by the desk console (desk.js) and the full-screen scanner page.
   FZScan.camera() opens the camera and reads QR codes with BarcodeDetector (Chrome/Edge); without it the code box still works for a
   USB scanner or typing. FZScan.post() sends a code to the server and always answers {ok, d} (also when the session has ended).
   The full-screen page below "prints" an entry receipt; the receipt HTML comes from the server (escaped there). */
(function () {
  var FZScan = window.FZScan = {};

  FZScan.csrf = function () {
    return (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || '';
  };

  FZScan.post = function (url, payload) {
    return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': FZScan.csrf(), 'X-Requested-With': 'fetch' }, body: JSON.stringify(payload) })
      .then(function (r) {
        // signed out (session ended or admin mode lost): the server answers with a login page instead of JSON
        if (r.redirected || (r.headers.get('Content-Type') || '').indexOf('application/json') < 0) return { ok: false, status: r.status, d: { error: 'Sessiya tugagan. Sahifani yangilab, qayta kiring.' } };
        return r.json().then(function (d) { return { ok: r.ok && d.ok !== false, status: r.status, d: d }; });
      })
      .catch(function () { return { ok: false, status: 0, d: { error: "Server bilan aloqa yo'q. Internetni tekshiring." } }; });
  };

  var audio = null;
  FZScan.beep = function (good) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      var tones = good ? [[880, 0, .12]] : [[220, 0, .16], [220, .22, .16]];
      tones.forEach(function (t) {
        var o = audio.createOscillator(), g = audio.createGain();
        o.type = 'sine'; o.frequency.value = t[0]; o.connect(g); g.connect(audio.destination);
        var at = audio.currentTime + t[1];
        g.gain.setValueAtTime(.0001, at); g.gain.exponentialRampToValueAtTime(.25, at + .02); g.gain.exponentialRampToValueAtTime(.0001, at + t[2]);
        o.start(at); o.stop(at + t[2] + .02);
      });
    } catch (e) {}
    if (navigator.vibrate) navigator.vibrate(good ? 60 : [80, 60, 80]);
  };

  /* opts: video, button, support, onCode(text), unsupported (text), wrap (element that gets .live) */
  FZScan.camera = function (o) {
    if (!('BarcodeDetector' in window) || !navigator.mediaDevices) { o.button.disabled = true; o.support.textContent = o.unsupported; return; }
    o.button.addEventListener('click', function () {
      o.button.disabled = true;  // one camera and one detection loop, however many times the button is pressed
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then(function (stream) {
        o.video.srcObject = stream; o.video.play(); (o.wrap || o.video.parentNode).classList.add('live');
        var det = new BarcodeDetector({ formats: ['qr_code'] });
        setInterval(function () {
          if (o.video.readyState < 2) return;
          det.detect(o.video).then(function (codes) { if (codes.length) o.onCode(codes[0].rawValue); }).catch(function () {});
        }, 400);
      }).catch(function () { o.support.textContent = o.unsupported; o.button.disabled = false; });
    });
  };

  /* ---- the full-screen scanner page ---- */
  var result = document.getElementById('scan-result');
  if (!result) return;
  var root = document.getElementById('scan-page'), url = root.dataset.url;
  var input = document.getElementById('scan-code'), led = document.getElementById('sc-led'), printBtn = document.getElementById('sc-print');
  var log = document.getElementById('sc-log'), today = document.getElementById('sc-today'), banner = document.getElementById('sc-banner');
  var last = '', lastAt = 0, hideTimer = null;

  function blink(cls) { led.className = 'sc-led ' + cls; setTimeout(function () { led.className = 'sc-led'; }, 1600); }

  function say(good, title, name, sub) {
    banner.hidden = false;
    banner.className = 'dk-banner sc-banner ' + (good ? 'good' : 'bad');
    banner.querySelector('[data-b="title"]').textContent = title;
    banner.querySelector('[data-b="name"]').textContent = name || '';
    banner.querySelector('[data-b="sub"]').textContent = sub || '';
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { banner.hidden = true; }, 7000);
  }

  function remember(good, name) {
    var li = document.createElement('li'), time = new Date();
    li.className = good ? 'ok' : 'no';
    var b = document.createElement('b'), s = document.createElement('span');
    b.textContent = name;
    s.textContent = ('0' + time.getHours()).slice(-2) + ':' + ('0' + time.getMinutes()).slice(-2);
    li.appendChild(b); li.appendChild(s);
    var ol = log.querySelector('ol');
    ol.insertBefore(li, ol.firstChild);
    while (ol.children.length > 8) ol.removeChild(ol.lastChild);
    log.hidden = false;
  }

  function show(x) {
    var d = x.d;
    if (!x.ok) {
      var reason = d.reason_label || '';
      say(false, 'Kirish taqiqlangan', d.error || 'Xato', reason);
      remember(false, d.error || 'Xato'); blink('no'); FZScan.beep(false);
      result.textContent = '';
      return;
    }
    var b = d.banner || { entered: d.entered, title: d.entered ? 'Kirishga ruxsat' : 'Kirish taqiqlangan', name: d.name, plan: d.plan, reason_label: d.message };
    say(!!d.entered, b.title, d.name, d.entered ? [b.plan, b.until ? ('— ' + b.until + ' gacha') : '', b.note].filter(Boolean).join(' ') : (b.reason_label || d.message));
    remember(!!d.entered, d.name);
    result.innerHTML = d.ticket;  // server-rendered template: every value is already HTML-escaped
    var tk = result.querySelector('.tk');
    if (tk) tk.classList.add('printing');
    if (d.today !== undefined) today.textContent = d.today;
    printBtn.hidden = false;
    blink(d.entered ? 'ok' : 'no');
    FZScan.beep(!!d.entered);
  }

  function submit(code) {
    code = (code || '').trim();
    if (!code || (code === last && Date.now() - lastAt < 4000)) return;
    last = code; lastAt = Date.now();
    led.className = 'sc-led busy';
    FZScan.post(url, { code: code }).then(show);
  }

  printBtn.addEventListener('click', function () { document.body.classList.add('dk-print-ticket'); window.print(); setTimeout(function () { document.body.classList.remove('dk-print-ticket'); }, 500); });
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(input.value); input.value = ''; } });
  FZScan.camera({ video: document.getElementById('scan-video'), button: document.getElementById('scan-start'), support: document.getElementById('scan-support'),
    onCode: submit, unsupported: "Bu brauzerda kamera orqali skanerlash yo'q. Pastdagi maydonga kodni kiriting yoki USB skanerdan foydalaning." });
})();
