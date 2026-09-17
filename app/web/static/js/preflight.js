/* Pre-flight page: rows, the confirmation, and the page's own header dot, rendered from
   GET /api/preflight (the stored result) and from the reply to POST /api/preflight/run.
   The page never guesses: no timer, no inferred state. Markup and colours follow the design
   export's Preflight.html (pending, one-fail, all-pass states). */
(function () {
  'use strict';
  var GLYPH = { pass: '✓', fail: '✕', skip: '○', pending: '○' };
  var HEADER_GLYPH = { pending: '○', pass: '✓', warn: '!', fail: '✕' };
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

  function headerTitle(result) {
    if (result.status === 'pending') { return 'Pre-flight: not run yet'; }
    var failed = result.checks.filter(function (c) { return c.status === 'fail'; });
    if (result.status === 'fail') {
      var essential = failed.filter(function (c) { return c.essential; })[0] || failed[0];
      return 'Pre-flight: ' + (essential ? essential.name : 'an essential check') + ' failed, ' + result.stamp;
    }
    if (result.status === 'warn') {
      return 'Pre-flight: ' + (failed[0] ? failed[0].name : 'a non-essential check') + ' failed (non-essential), ' + result.stamp;
    }
    return 'Pre-flight: all checks pass, ' + result.stamp;
  }

  function render(result) {
    var rows = document.getElementById('pf-rows');
    rows.textContent = '';
    result.checks.forEach(function (check) { rows.appendChild(row(check)); });
    var confirmation = document.getElementById('pf-confirmation');
    if (result.status === 'pass') {
      document.getElementById('pf-confirmation-line').textContent =
        modeWord(result.run_mode) + ' · ' + result.passed + ' of ' + result.applicable + ' · ' + result.stamp;
      confirmation.hidden = false;
    } else {
      confirmation.hidden = true;
    }
    var dot = document.querySelector('[data-part="preflight-indicator"]');
    if (dot) {
      dot.setAttribute('data-status', result.status);
      dot.textContent = HEADER_GLYPH[result.status] || '○';
      dot.setAttribute('title', headerTitle(result));
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
