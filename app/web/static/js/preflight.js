/* Pre-flight page: rows, the confirmation, and the page's own header dot, rendered from
   GET /api/preflight and from the reply to POST /api/preflight/run. The dot's state comes from the
   payload's header, worked out by the server against the seats in force (spec 012 research D8).
   The page never guesses: no timer, no inferred state. Markup and colours follow the design
   export's Preflight.html (pending, one-fail, all-pass states). */
(function () {
  'use strict';
  var GLYPH = { pass: '✓', fail: '✕', skip: '○', pending: '○' };
  var state = { busy: false };

  function api(method, path) {
    return fetch(path, { method: method }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) { throw new Error(data.error || response.statusText); }
        return data;
      });
    });
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === 'text') { node.textContent = attrs[key]; } else { node.setAttribute(key, attrs[key]); }
    });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function row(check) {
    return el('div', { class: 'check-row', 'data-part': 'check-row', 'data-check': check.id, 'data-status': check.status }, [
      el('div', { class: 'check-dot', 'data-status': check.status }),
      el('div', { class: 'check-name', text: check.name }),
      el('div', { class: 'check-detail', 'data-status': check.status, text: (GLYPH[check.status] || '○') + ' ' + check.detail })
    ]);
  }

  function modeWord(mode) { return mode === 'cloud' ? 'Cloud mode' : 'Laptop mode'; }

  function render(result) {
    var rows = document.getElementById('pf-rows');
    rows.textContent = '';
    result.checks.forEach(function (check) { rows.appendChild(row(check)); });
    var confirmation = document.getElementById('pf-confirmation');
    if (result.ran_at && result.applicable > 0 && result.passed === result.applicable) {
      document.getElementById('pf-confirmation-line').textContent =
        modeWord(result.run_mode) + ' · ' + result.passed + ' of ' + result.applicable + ' · ' + result.stamp;
      confirmation.hidden = false;
    } else {
      confirmation.hidden = true;
    }
    var dot = document.querySelector('[data-part="preflight-indicator"]');
    if (dot && result.header) {
      dot.setAttribute('data-status', result.header.status);
      dot.textContent = result.header.glyph;
      dot.setAttribute('title', result.header.title);
    }
  }

  function note(text) { document.getElementById('pf-note').textContent = text; }

  function run() {
    if (state.busy) { return; }
    state.busy = true;
    var button = document.getElementById('run-preflight');
    button.disabled = true;
    button.textContent = 'Running';
    note('');
    api('POST', '/api/preflight/run').then(function (result) {
      render(result);
    }).catch(function (error) {
      note(error.message);
    }).then(function () {
      state.busy = false;
      button.disabled = false;
      button.textContent = 'Run pre-flight';
    });
  }

  document.getElementById('run-preflight').addEventListener('click', run);
  api('GET', '/api/preflight').then(render).catch(function (error) { note(error.message); });
})();
