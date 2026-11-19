/* Order page: "Track" opens a map with the gym, the customer's address, the road and - while the order is on its way - the courier's live
   position (asked from /orders/<id>/track/ every 10 s while the map is open). */
(function () {
  var me = document.currentScript, T = me ? me.dataset : {};
  function fill(s, o) { return (s || '').replace(/@(\w+)/g, function (m, k) { return o[k] !== undefined ? o[k] : m; }); }
  document.querySelectorAll('[data-track]').forEach(function (btn) {
    var wrap = btn.closest('.ord-track-wrap'), panel = wrap.querySelector('.ord-track'), host = wrap.querySelector('.ord-map'), info = wrap.querySelector('.ord-track-info');
    var label = btn.querySelector('span'), map = null, timer = 0, first = true;
    function poll() {
      fetch(btn.dataset.track + (first ? '?route=1' : ''), { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { info.textContent = d.error || ''; return; }
          var upd = { courier: d.courier ? [d.courier.lat, d.courier.lng] : null };
          if (first) { upd.gym = d.gym; upd.client = d.client; upd.route = d.route ? d.route.coords : [d.gym, d.client]; upd.dashed = !d.route || d.route.source !== 'road'; first = false; }
          map.set(upd);
          if (d.status === 'done' || d.status === 'cancelled') { info.textContent = T.done; clearInterval(timer); timer = 0; }
          else if (d.courier) info.textContent = fill(T.eta, { min: d.eta_min });
          else info.textContent = d.status === 'shipping' ? T.offline : T.wait;
        })
        .catch(function () {});
    }
    btn.addEventListener('click', function () {
      var open = panel.hidden;
      panel.hidden = !open; label.textContent = open ? btn.dataset.close : btn.dataset.open;
      clearInterval(timer); timer = 0;
      if (!open) return;
      if (!map) map = window.FZMap(host, { labels: { gym: T.gym, client: T.you, courier: T.courier } });
      poll(); timer = setInterval(poll, 10000);
    });
  });
})();
