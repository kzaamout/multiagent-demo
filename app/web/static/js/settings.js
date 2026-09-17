/* Settings page: one row per seat from /api/seats, a model menu per row, a swap posted to
   /api/seats/<seat>. The page shows what the registry says; it never holds a credential.
   Markup and classes follow the design export's Settings.html (open dropdown state). */
(function () {
  'use strict';
  var F = window.S1Format;
  var el = F.el;
  var state = { table: null, open: null, status: '', busy: false };

  function api(method, path, body) {
    return fetch(path, {
      method: method,
      headers: body ? { 'content-type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) { throw new Error(data.error || response.statusText); }
        return data;
      });
    });
  }

  function agentCard(agent) {
    return el('div', { class: 'agent agent-lg', 'data-part': 'agent-card', 'data-agent': agent.agent_id }, [
      el('div', { class: 'avatar', 'data-part': 'avatar', style: 'background:' + F.seatColor(agent.agent_id), text: F.initials(agent.name) }),
      el('div', { class: 'agent-text' }, [
        el('div', { class: 'agent-name', 'data-part': 'name', text: agent.name + ', ' + agent.role }),
        el('div', { class: 'agent-model', 'data-part': 'model', text: agent.model ? agent.model.label : '' })
      ])
    ]);
  }

  function menu(row) {
    var items = state.table.models.map(function (option) {
      var attrs = {
        class: 'menu-item', type: 'button', role: 'option', 'data-seat': row.seat, 'data-model': option.key,
        'aria-selected': String(option.key === row.model_key), 'aria-disabled': String(!option.available)
      };
      return el('button', attrs, [option.label, el('span', { class: 'menu-note', text: option.note })]);
    });
    return el('div', { class: 'menu', role: 'listbox', 'data-part': 'model-menu' }, items);
  }

  function seatRow(row) {
    var open = state.open === row.seat;
    var children = [
      el('button', { class: 'model-select', type: 'button', 'data-part': 'model-select', 'data-seat': row.seat, 'aria-expanded': String(open) }, [
        el('span', { text: row.card.model ? row.card.model.label : '' }), el('span', { class: 'select-chev', text: '▾' })
      ])
    ];
    if (open) { children.push(menu(row)); }
    if (row.warning) { children.push(el('div', { class: 'seat-warning', 'data-part': 'seat-warning', text: row.warning })); }
    return el('div', { class: 'seat-row', 'data-part': 'seat-row', 'data-seat': row.seat }, [
      agentCard(row.card),
      el('div', { class: 'seat-select-col' }, children),
      el('div', { class: 'seat-dep', text: row.dependency })
    ]);
  }

  function render() {
    var box = document.getElementById('seat-rows');
    box.innerHTML = '';
    if (!state.table) { return; }
    state.table.seats.forEach(function (row) { box.appendChild(seatRow(row)); });
    document.getElementById('settings-note').textContent = state.table.note;
    document.getElementById('settings-status').textContent = state.status;
  }

  function load() {
    return api('GET', '/api/seats').then(function (table) { state.table = table; render(); })
      .catch(function (error) { state.status = 'Could not load the seats: ' + error.message; render(); });
  }

  function choose(seat, modelKey) {
    if (state.busy) { return; }
    state.busy = true;
    state.open = null;
    api('POST', '/api/seats/' + encodeURIComponent(seat), { model: modelKey }).then(function (result) {
      state.status = result.applied === 'next-dispatch'
        ? 'Applied to the live run: the next dispatch uses ' + result.model.label + '.'
        : 'Applied: the next run uses ' + result.model.label + '.';
      state.busy = false;
      return load();
    }).catch(function (error) {
      state.status = 'Not applied: ' + error.message;
      state.busy = false;
      render();
    });
  }

  document.addEventListener('click', function (e) {
    var item = e.target.closest('.menu-item[data-seat]');
    if (item) {
      if (item.getAttribute('aria-disabled') === 'true') { return; }
      choose(item.getAttribute('data-seat'), item.getAttribute('data-model'));
      return;
    }
    var select = e.target.closest('.model-select[data-seat]');
    if (select) {
      var seat = select.getAttribute('data-seat');
      state.open = state.open === seat ? null : seat;
      render();
      return;
    }
    if (state.open !== null) { state.open = null; render(); }
  });

  window.__s1settings = { state: state, reload: load };
  load();
})();
