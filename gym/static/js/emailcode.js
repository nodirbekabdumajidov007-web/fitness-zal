/* Resend button of the e-mail code page: counts the cooldown down, then enables itself. */
(function () {
  var b = document.querySelector('[data-wait]');
  if (!b) return;
  var n = +b.dataset.wait, c = b.querySelector('[data-count]');
  var t = setInterval(function () {
    n--;
    if (n <= 0) { clearInterval(t); b.disabled = false; if (c) c.remove(); }
    else if (c) c.textContent = '(' + n + ')';
  }, 1000);
})();
