/* Coach assistant page (offline knowledge base): the question is sent without reloading the page, the answer appears as a chat bubble.
   Without JavaScript the same form posts normally and the page reloads with the answer. */
(function () {
  var form = document.querySelector('[data-ai-form]');
  var log = document.querySelector('[data-ai-log]');
  if (form && log) {
    var box = form.querySelector('textarea'), btn = form.querySelector('button[type=submit]');
    var pic = form.querySelector('input[type=file]'), picBox = document.querySelector('[data-ai-pic]');
    function showPic() {  // the chosen photo: a small chip with a remove button
      if (!picBox) return;
      picBox.textContent = '';
      if (!pic || !pic.files.length) { picBox.hidden = true; return; }
      var x = document.createElement('button'); x.type = 'button'; x.textContent = '×'; x.setAttribute('aria-label', 'remove');
      x.addEventListener('click', function () { pic.value = ''; showPic(); });
      picBox.appendChild(document.createTextNode(pic.files[0].name.slice(0, 30) + ' ')); picBox.appendChild(x); picBox.hidden = false;
    }
    if (pic) pic.addEventListener('change', function () {
      if (pic.files[0] && pic.files[0].size > 4 * 1024 * 1024) { pic.value = ''; bubble('assistant error', form.dataset.imgerr || ''); }
      showPic();
    });
    function csrf() { return form.querySelector('[name=csrfmiddlewaretoken]').value; }
    function bubble(role, text, extra) {
      var empty = log.querySelector('[data-ai-empty]'); if (empty) empty.remove();
      var d = document.createElement('div'), p = document.createElement('p');
      d.className = 'ai-msg ' + role; p.textContent = text;  // textContent: the answer is never treated as HTML
      d.appendChild(p);
      if (extra && extra.links && extra.links.length) {
        var l = document.createElement('p');
        extra.links.forEach(function (k) { var a = document.createElement('a'); a.href = k.url; a.textContent = k.label + ' \u2192'; l.appendChild(a); l.appendChild(document.createTextNode(' ')); });
        d.appendChild(l);
      }
      if (extra && !extra.matched && extra.suggest && extra.suggest.length) {
        var c = document.createElement('div'); c.className = 'ai-chips';
        extra.suggest.forEach(function (s) {
          var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = s;
          b.addEventListener('click', function () { box.value = s; box.focus(); });
          c.appendChild(b);
        });
        d.appendChild(c);
      }
      log.appendChild(d); log.scrollTop = log.scrollHeight;
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
      var q = box.value.trim(), hasPic = !!(pic && pic.files.length);
      if ((!q && !hasPic) || btn.disabled) return;
      bubble('user', (hasPic ? '[' + pic.files[0].name.slice(0, 24) + '] ' : '') + q);
      var wait = bubble('assistant typing', form.dataset.thinking);
      box.value = ''; btn.disabled = true; btn.classList.add('loading');
      var body = new FormData(); body.append('q', q); if (hasPic) body.append('image', pic.files[0]);
      if (pic) { pic.value = ''; showPic(); }
      fetch(form.action, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          wait.remove();
          if (d.ok) {
            bubble('assistant', d.answer, d);
          } else { bubble('assistant error', d.error || form.dataset.err); box.value = q; }
        })
        .catch(function () { wait.remove(); bubble('assistant error', form.dataset.err); box.value = q; })
        .then(function () { btn.disabled = false; btn.classList.remove('loading'); box.focus(); });
    });
  }
  // stop a double click from saving the plan twice
  var plan = document.querySelector('[data-ai-plan]');
  if (plan) plan.addEventListener('submit', function (e) {
    var b = plan.querySelector('button[type=submit]');
    if (b.disabled) { e.preventDefault(); return; }
    setTimeout(function () { b.disabled = true; }, 0);
  });
})();
