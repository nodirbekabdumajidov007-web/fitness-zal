/* Home promo video: the page only shows a poster and a play button. The third-party player (YouTube privacy mode, Instagram embed)
   or the <video> file is created when the visitor presses play, so nothing is loaded or sent to anyone before that. */
(function () {
  'use strict';
  document.querySelectorAll('[data-promo]').forEach(function (box) {
    var btn = box.querySelector('.promo-play');
    if (!btn) return;
    var kind = box.getAttribute('data-kind'), src = box.getAttribute('data-src') || '';
    if (src.indexOf('https://') !== 0) return;
    function play() {
      var node;
      if (kind === 'file') {
        node = document.createElement('video');
        node.src = src; node.controls = true; node.autoplay = true; node.muted = true;  // muted: browsers only allow autoplay that way; sound is one tap on the controls
        node.setAttribute('playsinline', ''); node.setAttribute('preload', 'auto');
        var poster = box.querySelector('.promo-poster');
        if (poster) node.poster = poster.getAttribute('src');
      } else {
        node = document.createElement('iframe');
        node.src = src;
        node.title = box.getAttribute('data-label') || 'Video';
        node.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture; fullscreen');
        node.setAttribute('allowfullscreen', '');
        node.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
        node.setAttribute('loading', 'lazy');
      }
      node.className = 'promo-media';
      box.classList.add('on');
      box.appendChild(node);
      btn.hidden = true;
      var p = box.querySelector('.promo-poster'); if (p) p.hidden = true;
      if (kind === 'file' && node.play) { try { var r = node.play(); if (r && r.catch) r.catch(function () {}); } catch (e) {} }
    }
    btn.addEventListener('click', play);
  });
})();
