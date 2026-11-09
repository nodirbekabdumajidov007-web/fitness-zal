/* Workout logging: exercise autocomplete, set rows under a plan exercise ("log sets") and the standalone "add workout" form. */
(function () {
  var SUGGEST = '/progress/exercises/';

  function rowHtml(name, n, v) {
    v = v || {};
    var d = document.createElement('div');
    d.className = 'tk-setrow';
    d.innerHTML = '<input type="hidden" name="name"><span class="num"></span>' +
      '<input name="reps" type="number" min="1" max="100" inputmode="numeric"><input name="weight" inputmode="decimal">' +
      '<input name="rpe" inputmode="decimal" placeholder="1-10"><input name="snote" maxlength="120">';
    d.querySelector('[name=name]').value = name;
    d.querySelector('.num').textContent = n;
    d.querySelector('[name=reps]').value = v.reps || '';
    d.querySelector('[name=weight]').value = v.weight || '';
    d.querySelector('[name=rpe]').value = v.rpe || '';
    d.querySelector('[name=snote]').value = v.snote || '';
    return d;
  }

  /* autocomplete: fills the shared <datalist> from /progress/exercises/?q= */
  var list = document.getElementById('tkExercises'), timer = null, last = null;
  function suggest(q) {
    if (!list || q === last) return;
    last = q;
    fetch((list.dataset.suggest || SUGGEST) + '?q=' + encodeURIComponent(q), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); }).then(function (j) {
        list.innerHTML = '';
        (j.items || []).forEach(function (n) { var o = document.createElement('option'); o.value = n; list.appendChild(o); });
      }).catch(function () {});
  }
  document.addEventListener('input', function (e) {
    if (!e.target.matches || !e.target.matches('[data-exname],input[list=tkExercises]')) return;
    clearTimeout(timer);
    var q = e.target.value;
    timer = setTimeout(function () { suggest(q); }, 180);
  });
  document.addEventListener('focusin', function (e) { if (e.target.matches && e.target.matches('[data-exname],input[list=tkExercises]')) suggest(e.target.value || ''); });

  /* under a plan exercise: rows start from the planned number of sets and reps */
  document.querySelectorAll('[data-tk-sets]').forEach(function (box) {
    var rows = box.querySelector('[data-rows]'), name = box.dataset.name;
    function add(v) { rows.appendChild(rowHtml(name, rows.children.length + 1, v)); }
    box.addEventListener('toggle', function () {
      if (!box.open || rows.children.length) return;
      var reps = (String(box.dataset.reps).match(/\d+/) || [''])[0];
      for (var i = 0; i < (+box.dataset.sets || 3); i++) add({ reps: reps });
    });
    box.querySelector('[data-add-set]').addEventListener('click', function () { add(); });
  });

  /* standalone form: exercise blocks with set rows */
  var form = document.querySelector('[data-wform]');
  if (form) {
    if (list) list.dataset.suggest = form.dataset.suggest;
    var blocks = form.querySelector('[data-blocks]');
    var tplB = form.querySelector('[data-tpl-block]'), posted = null;
    try { posted = JSON.parse(document.getElementById('tkPosted').textContent); } catch (e) {}
    function renumber(rows) { Array.prototype.forEach.call(rows.children, function (r, i) { r.querySelector('.num').textContent = i + 1; }); }
    function addSet(block, v) {
      var rows = block.querySelector('[data-rows]');
      rows.appendChild(rowHtml(block.querySelector('[data-exname]').value, rows.children.length + 1, v));
    }
    function addBlock(name, sets) {
      var node = tplB.content.firstElementChild.cloneNode(true);
      blocks.appendChild(node);
      var nm = node.querySelector('[data-exname]');
      nm.value = name || '';
      nm.addEventListener('input', function () { node.querySelectorAll('[name=name]').forEach(function (h) { h.value = nm.value; }); });
      node.querySelector('[data-add-set]').addEventListener('click', function () { addSet(node); });
      node.querySelector('[data-del-ex]').addEventListener('click', function () { node.remove(); });
      (sets && sets.length ? sets : [{}, {}, {}]).forEach(function (s) { addSet(node, s); });
      return node;
    }
    form.querySelector('[data-add-ex]').addEventListener('click', function () { addBlock('').querySelector('[data-exname]').focus(); });
    if (posted && posted.length) {
      var groups = {}, order = [];
      posted.forEach(function (r) { if (!groups[r.name]) { groups[r.name] = []; order.push(r.name); } groups[r.name].push(r); });
      order.forEach(function (n) { addBlock(n, groups[n]); });
    } else addBlock('');
    form.addEventListener('submit', function () {
      form.querySelectorAll('.tk-block').forEach(function (b) {
        var n = b.querySelector('[data-exname]').value;
        b.querySelectorAll('[name=name]').forEach(function (h) { h.value = n; });
      });
    });
  }
})();
