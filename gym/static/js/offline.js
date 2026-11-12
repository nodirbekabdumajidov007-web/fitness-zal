/* Offline page: picks the language, retries, and offers the member card when the service worker has kept it. */
(function () {
  var root = document.documentElement, lang = 'uz';
  try {
    var m = document.cookie.match(/(?:^|; )fz_lang=([a-z]{2})/);
    var l = (m && m[1]) || (navigator.language || 'uz').slice(0, 2).toLowerCase();
    if (['ru', 'en', 'uz', 'tr', 'ky', 'tg'].indexOf(l) >= 0) lang = l;
  } catch (e) {}
  root.classList.add('js'); root.lang = lang;
  [].forEach.call(document.querySelectorAll('[data-l="' + lang + '"]'), function (n) { n.classList.add('on'); });

  var retry = document.getElementById('retry');
  function go() { location.href = '/'; }
  if (retry) retry.addEventListener('click', go);
  window.addEventListener('online', go);

  var card = document.getElementById('card');
  if (card && window.caches) {
    caches.match('/card/').then(function (hit) { if (hit) card.hidden = false; }).catch(function () {});
  }
})();
