/* Broiler Platform — site behaviour: theme, nav, copy buttons, TOC. */
(function () {
  'use strict';

  /* ---------- Theme ---------- */
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem('broiler-theme');
    if (saved === 'light' || saved === 'dark') root.setAttribute('data-theme', saved);
  } catch (e) { /* storage unavailable */ }

  function currentTheme() {
    var explicit = root.getAttribute('data-theme');
    if (explicit) return explicit;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function toggleTheme() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('broiler-theme', next); } catch (e) { /* ignore */ }
  }

  /* ---------- Nav toggle ---------- */
  function ready() {
    var themeBtn = document.querySelector('[data-theme-toggle]');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

    var navBtn = document.querySelector('[data-nav-toggle]');
    var nav = document.querySelector('.nav');
    if (navBtn && nav) {
      navBtn.addEventListener('click', function () {
        var open = nav.classList.toggle('open');
        navBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      nav.addEventListener('click', function (ev) {
        if (ev.target.tagName === 'A') {
          nav.classList.remove('open');
          navBtn.setAttribute('aria-expanded', 'false');
        }
      });
    }

    /* ---------- Copy buttons ---------- */
    Array.prototype.forEach.call(document.querySelectorAll('.code'), function (block) {
      var pre = block.querySelector('pre');
      var btn = block.querySelector('.copy-btn');
      if (!pre || !btn) return;
      btn.addEventListener('click', function () {
        var text = pre.innerText;
        var done = function () {
          var was = btn.textContent;
          btn.textContent = 'Copied';
          btn.classList.add('done');
          setTimeout(function () { btn.textContent = was; btn.classList.remove('done'); }, 1600);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () { /* ignore */ });
        } else {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.setAttribute('readonly', '');
          ta.style.position = 'absolute';
          ta.style.left = '-9999px';
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand('copy'); done(); } catch (e) { /* ignore */ }
          document.body.removeChild(ta);
        }
      });
    });

    /* ---------- Heading anchors + TOC ---------- */
    var body = document.querySelector('.doc-body');
    var toc = document.querySelector('[data-toc]');
    if (!body) return;

    var headings = body.querySelectorAll('h2[id], h3[id]');
    Array.prototype.forEach.call(headings, function (h) {
      if (h.querySelector('.anchor')) return;
      var a = document.createElement('a');
      a.className = 'anchor';
      a.href = '#' + h.id;
      a.textContent = '#';
      a.setAttribute('aria-label', 'Link to this section');
      h.appendChild(a);
    });

    if (!toc) return;
    var list = document.createElement('ul');
    var entries = [];
    Array.prototype.forEach.call(headings, function (h) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = (h.textContent || '').replace(/#$/, '').trim();
      if (h.tagName === 'H3') a.className = 'toc-h3';
      li.appendChild(a);
      list.appendChild(li);
      entries.push({ heading: h, link: a });
    });
    if (!entries.length) { toc.hidden = true; return; }
    toc.appendChild(list);

    if (!('IntersectionObserver' in window)) return;
    var visible = new Map();
    var obs = new IntersectionObserver(function (records) {
      records.forEach(function (r) {
        if (r.isIntersecting) visible.set(r.target, r.intersectionRatio);
        else visible.delete(r.target);
      });
      var best = null;
      entries.forEach(function (e) { if (visible.has(e.heading) && !best) best = e; });
      if (!best) return;
      entries.forEach(function (e) { e.link.classList.toggle('active', e === best); });
    }, { rootMargin: '-72px 0px -70% 0px', threshold: [0, 1] });
    entries.forEach(function (e) { obs.observe(e.heading); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ready);
  } else {
    ready();
  }
})();
