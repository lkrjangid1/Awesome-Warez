(function () {
  var input = document.getElementById('q');
  var status = document.getElementById('status');
  var results = document.getElementById('results');
  var form = document.getElementById('search-form');
  if (!input || !results) return;

  var fuse = null;
  var data = null;

  function escapeHTML(s) {
    return (s || '').replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function host(u) {
    try { return new URL(u).host; } catch (e) { return ''; }
  }

  function render(hits, query) {
    if (!hits.length) {
      results.innerHTML = '<p class="muted">No matches.</p>';
      return;
    }
    var byCat = {};
    var catTitles = {};
    data.categories.forEach(function (c) { catTitles[c.slug] = c.title; });
    hits.forEach(function (h) {
      var l = h.item || h;
      (byCat[l.category] = byCat[l.category] || []).push(l);
    });
    var order = data.categories
      .map(function (c) { return c.slug; })
      .filter(function (s) { return byCat[s]; });
    var html = '<p class="muted small">' + hits.length.toLocaleString() + ' result' + (hits.length === 1 ? '' : 's') + ' for "' + escapeHTML(query) + '"</p>';
    order.forEach(function (slug) {
      var arr = byCat[slug];
      var cap = arr.slice(0, 50);
      html += '<section class="group">'
            + '<h2><a href="categories/' + slug + '.html?q=' + encodeURIComponent(query) + '">' + escapeHTML(catTitles[slug]) + '</a>'
            + ' <span class="group-cat">' + arr.length + ' result' + (arr.length === 1 ? '' : 's') + '</span></h2>'
            + '<ul class="link-list">';
      cap.forEach(function (l) {
        html += '<li><a href="' + escapeHTML(l.url) + '" target="_blank" rel="nofollow noopener">' + escapeHTML(l.title) + '</a>'
             + ' <span class="host">' + escapeHTML(host(l.url)) + '</span>'
             + (l.description ? ' <span class="desc">— ' + escapeHTML(l.description) + '</span>' : '')
             + '</li>';
      });
      if (arr.length > cap.length) {
        html += '<li class="muted small">…and ' + (arr.length - cap.length).toLocaleString() + ' more in this category. '
             + '<a href="categories/' + slug + '.html?q=' + encodeURIComponent(query) + '">View all</a></li>';
      }
      html += '</ul></section>';
    });
    results.innerHTML = html;
  }

  function run(q) {
    if (!fuse) return;
    q = (q || '').trim();
    if (!q) {
      results.innerHTML = '';
      status.textContent = 'Type to search ' + data.links.length.toLocaleString() + ' links.';
      return;
    }
    status.textContent = '';
    var hits = fuse.search(q, { limit: 500 });
    render(hits, q);
  }

  fetch('data/links.json')
    .then(function (r) { return r.json(); })
    .then(function (d) {
      data = d;
      fuse = new Fuse(d.links, {
        keys: [
          { name: 'title',       weight: 0.5 },
          { name: 'description', weight: 0.25 },
          { name: 'subcategory', weight: 0.15 },
          { name: 'url',         weight: 0.1 }
        ],
        threshold: 0.35,
        ignoreLocation: true,
        minMatchCharLength: 2
      });
      status.textContent = 'Ready. Search ' + d.links.length.toLocaleString() + ' links.';
      var params = new URLSearchParams(location.search);
      var q = params.get('q');
      if (q) { input.value = q; run(q); }
    })
    .catch(function (err) {
      status.textContent = 'Failed to load search index: ' + err;
    });

  var t;
  input.addEventListener('input', function (e) {
    clearTimeout(t);
    var v = e.target.value;
    t = setTimeout(function () { run(v); }, 120);
  });
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      run(input.value);
      // update history so ?q= reflects current query
      var url = new URL(location.href);
      url.searchParams.set('q', input.value);
      history.replaceState(null, '', url.toString());
    });
  }
})();
