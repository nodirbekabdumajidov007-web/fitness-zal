/* Loaded in <head>, before first paint, so the saved theme never flashes. */
(function () {
  document.documentElement.classList.add('js');  // lets CSS prepare effects (e.g. trainer pixels) before the first paint
  try {
    var t = localStorage.getItem('fz-theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  } catch (e) {}
})();
