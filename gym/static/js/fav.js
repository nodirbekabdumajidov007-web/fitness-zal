/* Shop hearts: toggle a favourite without reloading the page (the form still works without JavaScript). */
(function () {
  document.addEventListener('submit', function (e) {
    var f = e.target.closest ? e.target.closest('.fav-form') : null;
    if (!f) return;
    e.preventDefault();
    var b = f.querySelector('.fav-btn');
    if (b.disabled) return;
    b.disabled = true;
    fetch(f.action, { method: 'POST', body: new FormData(f), credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) return;
        b.classList.toggle('on', d.on); b.setAttribute('aria-pressed', d.on ? 'true' : 'false');
        if (!d.on && location.pathname.indexOf('/favorites/') !== -1) { var card = f.closest('.prod'); if (card) card.remove(); }
      })
      .catch(function () { f.submit(); })
      .then(function () { b.disabled = false; });
  });
})();
