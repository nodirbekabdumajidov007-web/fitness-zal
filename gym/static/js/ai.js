/* AI coach page: the question is sent without reloading the page, the answer appears as a chat bubble.
   Without JavaScript the same form posts normally and the page reloads with the answer. */
(function () {
  var form = document.querySelector('[data-ai-form]');
  var log = document.querySelector('[data-ai-log]');
  if (form && log) {
    var box = form.querySelector('textarea'), btn = form.querySelector('button');
    function csrf() { return form.querySelector('[name=csrfmiddlewaretoken]').value; }
    function bubble(role, text) {
      var empty = log.querySelector('[data-ai-empty]'); if (empty) empty.remove();
      var d = document.createElement('div'), p = document.createElement('p');
      d.className = 'ai-msg ' + role; p.textContent = text;  // textContent: the answer is never treated as HTML
      d.appendChild(p); log.appendChild(d); log.scrollTop = log.scrollHeight;
      return d;
    }
    log.scrollTop = log.scrollHeight;
    document.querySelectorAll('[data-ai-chip]').forEach(function (c) {
      c.addEventListener('click', function () { box.value = c.textContent.trim(); box.focus(); });
    });
    box.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit ? form.requestSubmit() : form.submit(); }
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = box.value.trim();
      if (!q || btn.disabled) return;
      bubble('user', q);
      var wait = bubble('assistant typing', form.dataset.thinking);
      box.value = ''; btn.disabled = true; btn.classList.add('loading');
      var body = new FormData(); body.append('q', q);
      fetch(form.action, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          wait.remove();
          if (d.ok) {
            bubble('assistant', d.answer);
            var used = document.querySelector('[data-ai-used]');
            if (used) used.textContent = used.textContent.replace(/^\d+\s*\/\s*\d+/, d.used + ' / ' + d.limit);
          } else { bubble('assistant error', d.error || form.dataset.err); box.value = q; }
        })
        .catch(function () { wait.remove(); bubble('assistant error', form.dataset.err); box.value = q; })
        .then(function () { btn.disabled = false; btn.classList.remove('loading'); box.focus(); });
    });
  }
  // the plan takes up to a minute: show it is working and stop a double click from paying twice
  var plan = document.querySelector('[data-ai-plan]');
  if (plan) plan.addEventListener('submit', function (e) {
    var b = plan.querySelector('button[type=submit]');
    if (b.disabled) { e.preventDefault(); return; }
    setTimeout(function () { b.disabled = true; b.classList.add('loading'); b.textContent = b.dataset.busy; }, 0);
  });
})();
