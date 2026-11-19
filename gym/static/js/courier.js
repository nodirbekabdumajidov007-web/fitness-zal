/* Courier page (staff): shares this phone's position with the order (POST every ~8 s) and shows it on the map next to the customer's address. */
(function () {
  var me = document.currentScript, T = me ? me.dataset : {}, box = document.getElementById('courier-map');
  if (!box) return;
  function pt(s) { var a = s.split(','); return [parseFloat(a[0]), parseFloat(a[1])]; }
  var gym = pt(box.dataset.gym), client = pt(box.dataset.client), state = document.getElementById('courier-state'), btn = document.getElementById('courier-go');
  var map = window.FZMap(box, { labels: { gym: T.gym, client: T.you, courier: T.courier } }), watch = null, last = 0, csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  map.set({ gym: gym, client: client, route: [gym, client], dashed: true });
  fetch(box.dataset.route + '?lat=' + client[0] + '&lng=' + client[1], { credentials: 'same-origin' }).then(function (r) { return r.json(); })
    .then(function (r) { if (r.ok) map.set({ route: r.coords, dashed: r.source !== 'road' }); }).catch(function () {});
  function send(p) {
    var body = new FormData(); body.append('lat', p.coords.latitude.toFixed(6)); body.append('lng', p.coords.longitude.toFixed(6));
    fetch(box.dataset.ping, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json(); })
      .then(function (d) { state.textContent = d.ok ? T.on : T.err; }).catch(function () { state.textContent = T.err; });
  }
  function stop() { if (watch !== null) navigator.geolocation.clearWatch(watch); watch = null; btn.querySelector('span').textContent = btn.dataset.start; state.textContent = T.idle; }
  btn.addEventListener('click', function () {
    if (watch !== null) { stop(); return; }
    if (!navigator.geolocation) { state.textContent = T.err; return; }
    btn.querySelector('span').textContent = btn.dataset.stop;
    watch = navigator.geolocation.watchPosition(function (p) {
      map.set({ courier: [p.coords.latitude, p.coords.longitude] });
      var now = Date.now(); if (now - last > 8000) { last = now; send(p); }
    }, function () { state.textContent = T.err; stop(); }, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
  });
})();
