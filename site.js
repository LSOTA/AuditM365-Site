// AuditM365 : menu mobile de la navigation commune (site.css).
(function () {
  var b = document.getElementById('sn-burger'), m = document.getElementById('sn-menu');
  if (!b || !m) return;
  function set(open) { m.classList.toggle('open', open); b.setAttribute('aria-expanded', open ? 'true' : 'false'); }
  b.addEventListener('click', function (e) { e.stopPropagation(); set(!m.classList.contains('open')); });
  m.addEventListener('click', function (e) { if (e.target.closest('a')) set(false); });
  document.addEventListener('click', function (e) { if (m.classList.contains('open') && !m.contains(e.target)) set(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
  window.addEventListener('resize', function () { if (window.innerWidth > 1240) set(false); });
})();
