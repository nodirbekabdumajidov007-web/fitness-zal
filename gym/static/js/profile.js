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
})();
