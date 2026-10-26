/* Small progressive enhancements. Every page works without this file. */
document.addEventListener('DOMContentLoaded', function () {
  var root = document.documentElement;

  // a picture linked from another site may be blocked or deleted: show our drawing instead of an empty box
  document.querySelectorAll('img[data-fallback]').forEach(function (img) {
    function swap() { if (img.dataset.fallback && img.src.indexOf(img.dataset.fallback) === -1) { img.classList.remove('cover'); img.src = img.dataset.fallback; } }
    img.addEventListener('error', swap);
    if (img.complete && img.naturalWidth === 0 && img.getAttribute('loading') !== 'lazy') swap();
    if (img.complete && img.naturalWidth === 0 && img.currentSrc) swap();
  });

  // theme toggle (auto -> follows the OS until the visitor picks one)
  // day / night switch: the look follows the theme in CSS; here we only flip it, remember it and keep aria-checked right
  var tb = document.getElementById('theme-btn');
  function isDark() {
    return root.getAttribute('data-theme') === 'dark' || (!root.getAttribute('data-theme') && matchMedia('(prefers-color-scheme:dark)').matches);
  }
  if (tb) {
    tb.setAttribute('aria-checked', isDark() ? 'true' : 'false');
    tb.addEventListener('click', function () {
      var next = isDark() ? 'light' : 'dark';
      root.classList.add('theme-anim');  // colours glide instead of snapping, only during the switch
      root.setAttribute('data-theme', next);
      tb.setAttribute('aria-checked', next === 'dark' ? 'true' : 'false');
      setTimeout(function () { root.classList.remove('theme-anim'); }, 600);
      try { localStorage.setItem('fz-theme', next); } catch (e) {}
    });
  }

  // phone mask: keep only 9 digits, shown as 90 877 55 05
  document.querySelectorAll('input[data-phone]').forEach(function (el) {
    function fmt() {
      var d = el.value.replace(/\D/g, '');
      if (d.indexOf('998') === 0 && d.length > 9) d = d.slice(3);
      d = d.slice(0, 9);
      el.value = [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)].filter(Boolean).join(' ');
      var box = el.closest('.phone');  // a quiet tick once all 9 digits are in, so people know the number is complete
      if (box) box.classList.toggle('ok', d.length === 9);
    }
    el.addEventListener('input', fmt); fmt();
  });

  // password strength meter (sign-up and profile): length, mixed case, digits and symbols each add a step
  document.querySelectorAll('input[data-strength]').forEach(function (pw) {
    var form = pw.closest('form'), bar = form && form.querySelector('.pw-meter i');
    if (!bar) return;
    pw.addEventListener('input', function () {
      var v = pw.value, s = 0;
      if (v.length >= 6) s++; if (v.length >= 10) s++; if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++; if (/\d/.test(v)) s++; if (/[^A-Za-z0-9]/.test(v)) s++;
      bar.style.width = (s / 5 * 100) + '%';
      bar.className = s <= 1 ? 'weak' : s <= 3 ? 'ok' : 'strong';
    });
  });

  // press ripple on buttons: a soft circle grows from the point that was pressed (CSS: .btn .rip)
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.addEventListener('pointerdown', function (e) {
      var b = e.target.closest && e.target.closest('.btn');
      if (!b || b.disabled || b.classList.contains('loading')) return;
      var r = b.getBoundingClientRect(), size = Math.max(r.width, r.height) * 2.2, s = document.createElement('span');
      s.className = 'rip';
      s.style.cssText = 'left:' + (e.clientX - r.left) + 'px;top:' + (e.clientY - r.top) + 'px;width:' + size + 'px;height:' + size + 'px';
      b.appendChild(s);
      s.addEventListener('animationend', function () { s.remove(); });
    }, { passive: true });
  }

  // Caps Lock warning on password fields (the most common reason a correct password "does not work")
  document.querySelectorAll('input[data-caps]').forEach(function (el) {
    var hint = document.createElement('small');
    hint.className = 'caps-hint'; hint.textContent = el.getAttribute('data-caps'); hint.hidden = true;
    hint.setAttribute('role', 'status');
    (el.closest('.pw') || el).insertAdjacentElement('afterend', hint);
    function check(e) { if (e.getModifierState) hint.hidden = !e.getModifierState('CapsLock'); }
    el.addEventListener('keydown', check); el.addEventListener('keyup', check);
    el.addEventListener('blur', function () { hint.hidden = true; });
  });

  // show / hide password
  document.querySelectorAll('[data-toggle-pw]').forEach(function (b) {
    b.addEventListener('click', function () {
      var i = document.getElementById(b.getAttribute('data-toggle-pw'));
      var show = i.type === 'password';
      i.type = show ? 'text' : 'password';
      b.textContent = show ? b.getAttribute('data-hide') : b.getAttribute('data-show');
    });
  });

  // two-step confirm for destructive buttons; buttons marked data-bin then drop their label into a little bin before sending
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function binAndSubmit(b) {
    var form = b.form;
    if (!form || calm || !b.animate) { if (form) form.submit(); return; }
    b.classList.remove('armed');
    b.classList.add('bin-fx');
    b.disabled = true;
    var text = b.dataset.label || b.textContent;
    b.textContent = '';
    var chars = text.split('').map(function (c) { var s = document.createElement('span'); s.className = 'ch'; s.textContent = c; b.appendChild(s); return s; });
    var bin = document.createElement('span'); bin.className = 'bin'; bin.innerHTML = '<b></b><i></i>'; b.appendChild(bin);
    void bin.offsetWidth;  // commit the hidden state first so the pop-in transition runs
    bin.classList.add('on', 'open');
    var target = bin.getBoundingClientRect(), tx = target.left + target.width / 2, ty = target.top + 6;
    var last = 0;
    chars.slice().reverse().forEach(function (s, i) {
      var r = s.getBoundingClientRect(), dx = tx - (r.left + r.width / 2), dy = ty - (r.top + r.height / 2);
      var delay = 180 + i * 55; last = delay + 520;
      s.animate([{ transform: 'none', opacity: 1 },
                 { transform: 'translate(' + dx * 0.55 + 'px,' + (dy - 26) + 'px) rotate(' + (i % 2 ? 140 : -140) + 'deg)', opacity: 1, offset: 0.55 },
                 { transform: 'translate(' + dx + 'px,' + dy + 'px) rotate(' + (i % 2 ? 300 : -300) + 'deg) scale(.2)', opacity: 0 }],
                { duration: 520, delay: delay, easing: 'cubic-bezier(.4,0,.6,1)', fill: 'forwards' });
    });
    setTimeout(function () { bin.classList.remove('open'); bin.classList.add('shut', 'done'); b.classList.add('sealed'); bin.animate([{ transform: 'none' }, { transform: 'translateY(-3px) rotate(-8deg)' }, { transform: 'none' }], { duration: 260 }); }, last + 40);
    setTimeout(function () { form.submit(); }, last + 520);
  }
  document.querySelectorAll('button[data-confirm]').forEach(function (b) {
    b.addEventListener('click', function (e) {
      if (!b.classList.contains('armed')) {
        e.preventDefault();
        b.classList.add('armed');
        b.dataset.label = b.textContent;
        b.textContent = b.getAttribute('data-confirm');
        b._t = setTimeout(function () { b.classList.remove('armed'); b.textContent = b.dataset.label; }, 4000);
      } else if (b.hasAttribute('data-bin')) {
        e.preventDefault();
        clearTimeout(b._t);
        binAndSubmit(b);
      }
    });
  });

  // close the language menu when clicking elsewhere or pressing Esc
  var lp = document.querySelector('.langpick');
  if (lp) {
    document.addEventListener('click', function (e) { if (lp.open && !lp.contains(e.target)) lp.open = false; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && lp.open) { lp.open = false; lp.querySelector('summary').focus(); } });
  }

  // live character counter for textareas that ask for one
  document.querySelectorAll('textarea[data-count-to]').forEach(function (t) {
    var out = document.getElementById(t.getAttribute('data-count-to'));
    function upd() { if (out) out.textContent = t.value.length + ' / ' + t.maxLength; }
    t.addEventListener('input', upd); upd();
  });

  // language select + print
  var ls = document.getElementById('lang-select');
  if (ls) ls.addEventListener('change', function () { location.href = '/lang/' + ls.value + '/?next=' + encodeURIComponent(location.pathname + location.search); });
  document.querySelectorAll('[data-print]').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });

  // copy-to-clipboard buttons (falls back to selecting the text)
  document.querySelectorAll('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var el = document.getElementById(b.getAttribute('data-copy'));
      el.select();
      var done = function () { var old = b.textContent; b.textContent = b.getAttribute('data-done'); setTimeout(function () { b.textContent = old; }, 1800); };
      if (navigator.clipboard) navigator.clipboard.writeText(el.value).then(done, function () {});
      else { try { document.execCommand('copy'); done(); } catch (e) {} }
    });
  });

  // trainer portraits open like a curtain when they scroll into view (the motion itself is pure CSS, see .px-done).
  // px-armed switches off the CSS safety timer, which only matters if this script never runs.
  var pxBoxes = [].slice.call(document.querySelectorAll('[data-px]'));
  function reveal(box) { box.classList.add('px-done'); }
  pxBoxes.forEach(function (b) { b.classList.add('px-armed'); });
  if (pxBoxes.length && 'IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var pxo = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); pxo.unobserve(e.target); } });
    }, { threshold: .3 });
    pxBoxes.forEach(function (b) { pxo.observe(b); });
  } else pxBoxes.forEach(reveal);

  // installable app: register the service worker
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(function () {});

  // a little celebration after anything that went well (order placed, payment reported, class booked, welcome...)
  function confetti() {
    var c = document.createElement('canvas'), x = c.getContext('2d'), W = c.width = innerWidth, H = c.height = innerHeight;
    c.className = 'confetti'; c.setAttribute('aria-hidden', 'true'); document.body.appendChild(c);
    var cols = ['#f0503d', '#ff8a3d', '#e2b84a', '#3ac47a', '#6e9bff', '#ffffff'], ps = [];
    for (var i = 0; i < 150; i++) {
      var fromLeft = i % 2 === 0;
      ps.push({ x: fromLeft ? -10 : W + 10, y: H * .75, vx: (fromLeft ? 1 : -1) * (4 + Math.random() * 9), vy: -(9 + Math.random() * 11),
                w: 6 + Math.random() * 6, h: 3 + Math.random() * 5, r: Math.random() * 6, vr: (Math.random() - .5) * .4, c: cols[i % cols.length] });
    }
    var t0 = performance.now();
    (function tick(t) {
      x.clearRect(0, 0, W, H);
      var k = (t - t0) / 2200;
      ps.forEach(function (p) {
        p.vy += .32; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.r += p.vr;
        x.save(); x.globalAlpha = Math.max(0, 1 - k); x.translate(p.x, p.y); x.rotate(p.r); x.fillStyle = p.c; x.fillRect(-p.w / 2, -p.h / 2, p.w, p.h * Math.abs(Math.cos(p.r * 2))); x.restore();
      });
      if (k < 1) requestAnimationFrame(tick); else c.remove();
    })(t0);
  }
  window.fzConfetti = confetti;
  if (document.querySelector('.msg.success') && !matchMedia('(prefers-reduced-motion: reduce)').matches) setTimeout(confetti, 250);

  // flash messages fade out
  document.querySelectorAll('.msg').forEach(function (m) { setTimeout(function () { m.classList.add('gone'); }, 6000); });

  // optional Google sign-in
  // Sign in with Apple (iCloud): Apple's own popup, then the server checks the signed token
  var ab = document.getElementById('abtn');
  if (ab && ab.dataset.client) {
    var as = document.createElement('script');
    as.src = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'; as.async = true;
    as.onload = function () {
      AppleID.auth.init({ clientId: ab.dataset.client, scope: 'name email', redirectURI: location.origin + '/auth/apple/', usePopup: true });
    };
    document.head.appendChild(as);
    ab.addEventListener('click', function () {
      if (!window.AppleID) return;
      AppleID.auth.signIn().then(function (r) {
        var tok = (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || '';
        return fetch('/auth/apple/', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': tok },
          body: JSON.stringify({ id_token: r.authorization.id_token, name: r.user && r.user.name }) }).then(function (x) { return x.json(); });
      }).then(function (d) {
        if (d && d.ok) location.href = d.next;
        else if (d) { var e = document.getElementById('gerr'); if (e) e.textContent = d.error; }
      }).catch(function () {});  // closed the popup
    });
  }

  var g = document.getElementById('gbtn');
  if (g && g.dataset.client && location.hostname === '127.0.0.1') {
    // Google only accepts "localhost" as a local origin, so move to the same page there
    location.replace(location.href.replace('//127.0.0.1', '//localhost'));
    return;
  }
  if (g && g.dataset.client) {
    var s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client'; s.async = true;
    s.onload = function () {
      google.accounts.id.initialize({
        client_id: g.dataset.client,
        callback: function (r) {
          var tok = (document.cookie.split('; ').find(function (c) { return c.indexOf('csrftoken=') === 0; }) || '').split('=')[1] || '';
          fetch('/auth/google/', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': tok }, body: JSON.stringify({ credential: r.credential }) })
            .then(function (x) { return x.json(); })
            .then(function (d) { if (d.ok) location.href = d.next; else { var e = document.getElementById('gerr'); if (e) e.textContent = d.error; } });
        }
      });
      var dark = root.getAttribute('data-theme') === 'dark' || (!root.getAttribute('data-theme') && matchMedia('(prefers-color-scheme:dark)').matches);
      google.accounts.id.renderButton(g, { theme: dark ? 'filled_black' : 'outline', size: 'large', shape: 'pill', text: 'continue_with',
                                           logo_alignment: 'center', width: Math.min(400, Math.max(200, g.offsetWidth || 300)) });
    };
    document.head.appendChild(s);
  }
});
