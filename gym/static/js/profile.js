/* Profile: the tab bar highlights the section in view (they are plain anchors, so it works without JS too).
   The password strength meter lives in app.js, shared with the sign-up page. */
(function () {
  var tabs = document.querySelector('[data-ptabs]');
  if (tabs && 'IntersectionObserver' in window) {
    var links = [].slice.call(tabs.querySelectorAll('a'));
    var seen = {}, pinned = 0;
    function mark(id) { links.forEach(function (a) { a.setAttribute('aria-selected', a.getAttribute('href') === '#' + id ? 'true' : 'false'); }); }
    // a tapped tab stays lit while the page scrolls to it (its panel may share a row with the one before it)
    links.forEach(function (a) { a.addEventListener('click', function () { mark(a.getAttribute('href').slice(1)); pinned = Date.now() + 1200; }); });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { seen[e.target.id] = e.isIntersecting; });
      if (Date.now() < pinned) return;
      // panels sit two per row on wide screens, so both are "in view" at once: the first one in page order wins
      for (var i = 0; i < links.length; i++) { var id = links[i].getAttribute('href').slice(1); if (seen[id]) { mark(id); return; } }
    }, { rootMargin: '-30% 0px -60% 0px' });
    var h = location.hash.slice(1);
    if (h && links.some(function (a) { return a.getAttribute('href') === '#' + h; })) { mark(h); pinned = Date.now() + 1200; }
    else if (window.scrollY < 40) mark(links[0].getAttribute('href').slice(1));
    links.forEach(function (a) { var s = document.querySelector(a.getAttribute('href')); if (s) io.observe(s); });
  }
  // profile picture: choosing a file uploads it straight away (the picture shows at once as a preview)
  var af = document.querySelector('[data-avatar-form]');
  if (af) {
    var inp = af.querySelector('input[type=file]');
    inp.addEventListener('change', function () {
      if (!inp.files.length) return;
      var lab = af.querySelector('.pf-ava, .db-ava'), img = lab.querySelector('img') || document.createElement('img');
      img.src = URL.createObjectURL(inp.files[0]); lab.classList.add('has-img', 'busy');
      var s = lab.querySelector('span'); if (s) s.remove();
      if (!img.parentNode) lab.prepend(img);
      af.submit();
    });
  }
  // account settings: show the chosen file's name next to the "change" button
  document.querySelectorAll('input[data-file-name]').forEach(function (inp) {
    var label = inp.parentNode.querySelector('[data-file-label]');
    inp.addEventListener('change', function () { if (label && inp.files.length) label.textContent = inp.files[0].name; });
  });
})();
