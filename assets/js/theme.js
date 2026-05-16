(function () {
  var root = document.documentElement;
  var btn = document.querySelector('.theme-toggle');
  if (btn) {
    btn.addEventListener('click', function () {
      var current = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', current);
      try { localStorage.setItem('theme', current); } catch (e) {}
    });
  }

  // global "/" focuses the header search input (ignore when typing in a field)
  document.addEventListener('keydown', function (e) {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target;
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    var input = document.querySelector('.site-header input[type="search"]')
             || document.querySelector('.hero-search input[type="search"]')
             || document.querySelector('input[type="search"]');
    if (input) {
      e.preventDefault();
      input.focus();
      input.select();
    }
  });
})();
