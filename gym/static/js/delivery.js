/* Cart: pick "pickup" or "courier"; the address fields open, the delivery fee and the grand total update live
   (the same rule the server uses: free delivery above the threshold). The server recomputes everything. */
(function () {
  var box = document.getElementById('dlv'), sub = document.getElementById('cart-total'), grand = document.getElementById('grand-total');
  if (!sub || !grand) return;
  var unit = box ? box.dataset.unit : '';
  function money(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }
  function digits(el) { return +(el.textContent || '').replace(/\D/g, '') || 0; }
  function update() {
    var s = digits(sub), courier = box && box.querySelector('input[value=courier]').checked, fee = 0;
    if (courier) { var free = +box.dataset.free || 0; fee = free && s >= free ? 0 : (+box.dataset.fee || 0); }
    var feeEl = document.getElementById('dlv-fee');
    if (feeEl) feeEl.textContent = fee ? money(fee) + ' ' + unit : box.dataset.freeLabel;
    var old = digits(grand), now = s + fee;
    grand.innerHTML = money(now) + ' <small>' + (unit || grand.querySelector('small') && grand.querySelector('small').textContent || '') + '</small>';
    if (old !== now) { grand.classList.remove('bump'); void grand.offsetWidth; grand.classList.add('bump'); }
  }
  if (box) {
    var addr = document.getElementById('dlv-addr');
    box.addEventListener('change', function () {
      var courier = box.querySelector('input[value=courier]').checked;
      addr.hidden = !courier;
      document.getElementById('dlv-a').required = courier;
      box.classList.toggle('courier', courier);
      if (courier) document.getElementById('dlv-a').focus();
      update();
    });
  }
  new MutationObserver(update).observe(sub, { childList: true, characterData: true, subtree: true });  // the cart's − n + changes the subtotal
  update();
})();
