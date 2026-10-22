/* Front-desk QR scanner: camera (BarcodeDetector, Chrome/Edge), or a USB scanner / keyboard typing into the field.
   Every scan "prints" an entry receipt out of the printer slot; the receipt HTML comes from the server (escaped there). */
(function () {
  var video = document.getElementById('scan-video'), input = document.getElementById('scan-code');
  var startBtn = document.getElementById('scan-start'), support = document.getElementById('scan-support');
  var result = document.getElementById('scan-result'), t = document.getElementById('scan-i18n').dataset;
  var led = document.getElementById('sc-led'), printBtn = document.getElementById('sc-print');
  var log = document.getElementById('sc-log'), today = document.getElementById('sc-today');
  var last = '', lastAt = 0;

  function csrf() { return (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || ''; }

  function blink(cls) {
    led.className = 'sc-led ' + cls;
    setTimeout(function () { led.className = 'sc-led'; }, 1600);
  }

  function remember(ok, d) {
    var li = document.createElement('li'), time = new Date();
    li.className = ok && d.entered ? 'ok' : 'no';
    var b = document.createElement('b'), s = document.createElement('span');
    b.textContent = ok ? d.name : (d.error || t.err);
    s.textContent = ('0' + time.getHours()).slice(-2) + ':' + ('0' + time.getMinutes()).slice(-2);
    li.appendChild(b); li.appendChild(s);
    var ol = log.querySelector('ol');
    ol.insertBefore(li, ol.firstChild);
    while (ol.children.length > 6) ol.removeChild(ol.lastChild);
    log.hidden = false;
  }

  function show(ok, d) {
    remember(ok, d);
    if (!ok) {
      result.textContent = '';
      var e = document.createElement('p'); e.className = 'sc-wait sc-bad'; e.textContent = d.error || t.err;
      result.appendChild(e); printBtn.hidden = true; blink('no');
      if (result.getBoundingClientRect().top > innerHeight - 80) result.parentNode.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    result.innerHTML = d.ticket;  // server-rendered template: every value is already HTML-escaped
    var tk = result.querySelector('.tk');
    if (tk) { tk.classList.add('printing'); }
    // on a phone the printer sits below the camera: bring the receipt into view (focus stays in the code field for the USB scanner)
    var box = result.getBoundingClientRect();
    if (box.top > innerHeight - 80 || box.bottom < 0) result.parentNode.scrollIntoView({ behavior: 'smooth', block: 'start' });
    if (d.today !== undefined) today.textContent = d.today;
    printBtn.hidden = false;
    blink(d.entered ? 'ok' : 'no');
    if (navigator.vibrate) navigator.vibrate(d.entered ? 60 : [80, 60, 80]);
  }

  function submit(code) {
    code = (code || '').trim();
    if (!code || (code === last && Date.now() - lastAt < 4000)) return;
    last = code; lastAt = Date.now();
    led.className = 'sc-led busy';
    fetch('/staff/scan/', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify({ code: code }) })
      .then(function (r) {
        // signed out (session ended or admin mode lost): the server answers with a login page instead of JSON
        if (r.redirected || (r.headers.get('Content-Type') || '').indexOf('application/json') < 0) return { ok: false, d: { error: t.session } };
        return r.json().then(function (d) { return { ok: r.ok, d: d }; });
      })
      .then(function (x) { show(x.ok, x.d); })
      .catch(function () { show(false, { error: t.err }); });
  }

  printBtn.addEventListener('click', function () { window.print(); });
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(input.value); input.value = ''; } });

  if (!('BarcodeDetector' in window) || !navigator.mediaDevices) { startBtn.disabled = true; support.textContent = t.nocam; return; }
  startBtn.addEventListener('click', function () {
    startBtn.disabled = true;  // one camera and one detection loop, however many times the button is pressed
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then(function (stream) {
      video.srcObject = stream; video.play(); video.parentNode.classList.add('live');
      var det = new BarcodeDetector({ formats: ['qr_code'] });
      setInterval(function () {
        if (video.readyState < 2) return;
        det.detect(video).then(function (codes) { if (codes.length) submit(codes[0].rawValue); }).catch(function () {});
      }, 400);
    }).catch(function () { support.textContent = t.nocam; startBtn.disabled = false; });
  });
})();
