/* Trainer plan builder: add / remove exercise rows, or start from one of the ready-made programs. */
(function () {
  var form = document.querySelector('[data-plan-builder]');
  if (!form) return;
  var box = form.querySelector('[data-rows]');
  var programs = JSON.parse((document.getElementById('pb-programs') || {}).textContent || '{}');
  function blankRow() {
    var tpl = box.querySelector('.pb-row');
    var row = tpl.cloneNode(true);
    row.querySelectorAll('input').forEach(function (i) { i.value = i.name === 'sets' ? '3' : (i.name === 'reps' ? '10' : ''); });
    return row;
  }
  function fill(row, r) {
    row.querySelector('[name=wd]').value = String(r.wd);
    row.querySelector('[name=name]').value = r.name;
    row.querySelector('[name=sets]').value = r.sets;
    row.querySelector('[name=reps]').value = r.reps;
    row.querySelector('[name=note]').value = r.note || '';
  }
  form.querySelector('[data-add]').addEventListener('click', function () {
    var last = box.querySelector('.pb-row:last-child'), row = blankRow();
    if (last) row.querySelector('[name=wd]').value = last.querySelector('[name=wd]').value;  // same day as the row above
    box.appendChild(row);
    row.classList.add('pb-new');
    row.querySelector('[name=name]').focus();
  });
  box.addEventListener('click', function (e) {
    var del = e.target.closest('[data-del]');
    if (!del) return;
    var rows = box.querySelectorAll('.pb-row');
    if (rows.length > 1) del.closest('.pb-row').remove();
    else fill(rows[0], { wd: 0, name: '', sets: 3, reps: '10', note: '' });
  });
  form.querySelectorAll('[data-program]').forEach(function (b) {
    b.addEventListener('click', function () {
      var list = programs[b.dataset.program] || [];
      var tpl = blankRow();
      box.innerHTML = '';
      (list.length ? list : [{ wd: 0, name: '', sets: 3, reps: '10', note: '' }]).forEach(function (r) {
        var row = tpl.cloneNode(true); fill(row, r); box.appendChild(row);
      });
      if (list.length && !form.elements.title.value) form.elements.title.value = b.textContent.trim();
    });
  });
})();
