(function () {
  var input = document.getElementById('page-filter');
  if (!input) return;
  var items = Array.prototype.slice.call(document.querySelectorAll('.link-list li'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('.sub-section'));
  var visibleEl = document.querySelector('[data-count-visible]');
  var total = items.length;

  // index each <li> text once for fast filtering
  var haystacks = items.map(function (li) { return li.textContent.toLowerCase(); });

  function apply(q) {
    q = q.trim().toLowerCase();
    var visible = 0;
    for (var i = 0; i < items.length; i++) {
      var match = !q || haystacks[i].indexOf(q) !== -1;
      items[i].classList.toggle('hidden', !match);
      if (match) visible++;
    }
    // hide empty sub-sections
    sections.forEach(function (sec) {
      var any = sec.querySelector('.link-list li:not(.hidden)');
      sec.style.display = any ? '' : 'none';
    });
    if (visibleEl) visibleEl.textContent = visible.toLocaleString();
  }

  // honor ?q= deeplink
  var params = new URLSearchParams(location.search);
  var initial = params.get('q') || '';
  if (initial) { input.value = initial; apply(initial); }

  var t;
  input.addEventListener('input', function (e) {
    clearTimeout(t);
    var v = e.target.value;
    t = setTimeout(function () { apply(v); }, 80);
  });
})();
