/* Profile: the tab bar highlights the section in view (they are plain anchors, so it works without JS too).
   The password strength meter lives in app.js, shared with the sign-up page. */
(function () {
  var tabs = document.querySelector('[data-ptabs]');
  if (tabs && 'IntersectionObserver' in window) {
    var links = [].slice.call(tabs.querySelectorAll('a'));
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) links.forEach(function (a) { a.setAttribute('aria-selected', a.getAttribute('href') === '#' + e.target.id ? 'true' : 'false'); });
      });
    }, { rootMargin: '-40% 0px -55% 0px' });
    links.forEach(function (a) { var s = document.querySelector(a.getAttribute('href')); if (s) io.observe(s); });
  }
  // profile picture: choosing a file uploads it straight away (the picture shows at once as a preview)
  var af = document.querySelector('[data-avatar-form]');
  if (af) {
    var inp = af.querySelector('input[type=file]');
    inp.addEventListener('change', function () {
      if (!inp.files.length) return;
      var lab = af.querySelector('.pf-ava'), img = lab.querySelector('img') || document.createElement('img');
      img.src = URL.createObjectURL(inp.files[0]); lab.classList.add('has-img', 'busy');
      var s = lab.querySelector('span'); if (s) s.remove();
      if (!img.parentNode) lab.prepend(img);
      af.submit();
    });
  }
})();
