/* Introduction page: team cards expand on click, and the replay frame's speed control reloads the
   read-only Demo frame at 1x or 4x. Nothing here touches a run. */
(function () {
  'use strict';

  document.querySelectorAll('[data-part="team-card"]').forEach(function (card) {
    function toggle() {
      var open = card.getAttribute('data-open') === 'true';
      card.setAttribute('data-open', String(!open));
      var detail = card.querySelector('[data-part="team-card-detail"]');
      if (detail) { detail.hidden = open; }
    }
    card.addEventListener('click', toggle);
    card.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
  });

  var frame = document.getElementById('replay-iframe');
  document.querySelectorAll('.replay-speed').forEach(function (button) {
    button.addEventListener('click', function () {
      if (!frame) { return; }
      var speed = button.getAttribute('data-speed');
      document.querySelectorAll('.replay-speed').forEach(function (b) { b.classList.toggle('is-on', b === button); });
      var url = new URL(frame.getAttribute('src'), window.location.origin);
      url.searchParams.set('speed', speed);
      frame.setAttribute('src', url.pathname + url.search);
    });
  });
})();
