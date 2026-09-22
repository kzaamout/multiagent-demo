/* Settings page: one row per seat from /api/seats, a model menu per row, a swap posted to
   /api/seats/<seat>. The page shows what the registry says; it never holds a credential.
   Markup and classes follow the design export's Settings.html (open dropdown state).
   The seat model guide (spec 014) comes in the same table: the top open and top proprietary model per
   seat and the current model's instruction accuracy. The server works out every figure; this page never
   divides or rounds. */
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

  var KIND_LABELS = { open: 'Top open model', proprietary: 'Top proprietary model' };

  function counts(record) {
    return record.percent + '% (' + record.first_time + ' of ' + record.replies;
  }

  /* The current model's figure after its name in the button; no runs yet when it has no replies here. */
  function currentFigure(guide) {
    return guide && guide.current ? counts(guide.current) + ')' : 'no runs yet';
  }

  function pickText(pick) {
    if (pick && pick.status === 'pick') { return pick.model + ' · ' + counts(pick) + ' replies)'; }
    if (pick && pick.status === 'too_few_runs') {
      return 'none with ' + state.table.guide.min_runs + ' runs on this seat yet';
    }
    return 'no runs yet';
  }

  function seatGuide(row) {
    var guide = row.guide || {};
    var lines = ['open', 'proprietary'].map(function (kind) {
      return el('div', { class: 'guide-line', 'data-kind': kind }, [
        el('span', { class: 'guide-kind', 'data-part': 'guide-kind', text: KIND_LABELS[kind] }),
        el('span', { class: 'guide-value', 'data-part': 'guide-value', text: pickText(guide[kind]) })
      ]);
    });
    return el('div', { class: 'seat-guide', 'data-part': 'seat-guide' }, lines);
  }

  /* A seat with no guide (the appraisal seats, before their workflow runs) shows none. */
  function seatRow(row) {
    var open = state.open === row.seat;
    var label = el('span', { class: 'select-model-name', text: row.card.model ? row.card.model.label : '' });
    var figure = row.guide ? el('span', { class: 'select-fig', 'data-part': 'select-fig', text: currentFigure(row.guide) }) : null;
    var children = [
      el('button', { class: 'model-select', type: 'button', 'data-part': 'model-select', 'data-seat': row.seat, 'aria-expanded': String(open) }, [
        el('span', { class: 'select-text' }, [label, figure]),
        el('span', { class: 'select-chev', text: '▾' })
      ])
    ];
    if (open) { children.push(menu(row)); }
    if (row.warning) { children.push(el('div', { class: 'seat-warning', 'data-part': 'seat-warning', text: row.warning })); }
    return el('div', { class: 'seat-row', 'data-part': 'seat-row', 'data-seat': row.seat }, [
      agentCard(row.card),
      el('div', { class: 'seat-select-col' }, children),
      el('div', { class: 'seat-dep', text: row.dependency }),
      row.guide ? seatGuide(row) : null
    ]);
  }

  function guideNote(guide) {
    var runs = guide ? guide.runs : 0;
    return "Instruction accuracy is the share of a seat's replies the Orchestrator accepted the first time it " +
      "checked them against the seat's instructions. Figures from " + runs +
      (runs === 1 ? ' recorded run.' : ' recorded runs.');
  }

  function render() {
    var box = document.getElementById('seat-rows');
    box.innerHTML = '';
    if (!state.table) { return; }
    state.table.seats.forEach(function (row) { box.appendChild(seatRow(row)); });
    document.getElementById('settings-note').textContent = state.table.note;
    document.getElementById('guide-note').textContent = guideNote(state.table.guide);
    document.getElementById('settings-status').textContent = state.status;
  }

  function load() {
    return api('GET', '/api/seats').then(function (table) { state.table = table; render(); })
      .catch(function (error) { state.status = 'Could not load the seats: ' + error.message; render(); });
  }

  function setDot(header) {
    var dot = document.querySelector('[data-part="preflight-indicator"]');
    if (!dot || !header) { return; }
    dot.setAttribute('data-status', header.status);
    dot.textContent = header.glyph;
    dot.setAttribute('title', header.title);
  }

  /* After a swap, the pre-flight rechecks the chosen model and the key for its provider (spec 012
     research D10). The reply carries the model's row and the header state; the last reply wins.
     No timer and no polling: the result arrives as the reply. */
  function recheck(modelKey, label, applied) {
    var asked = (state.rechecks = (state.rechecks || 0) + 1);
    api('POST', '/api/preflight/recheck', { model: modelKey }).then(function (reply) {
      if (asked !== state.rechecks) { return; }
      var row = reply.checks.filter(function (c) { return c.subject && c.subject.model_key === modelKey; })[0];
      /* A cloud row's detail names the model; a local row's says only whether it is pulled. */
      var line = !row ? 'Checked.' : (row.subject.provider === 'ollama' ? label + ': ' : '') + row.detail + '.';
      if (reply.header.status === 'fail') { line += ' Pre-flight is red.'; }
      state.status = applied + ' ' + line;
      setDot(reply.header);
      render();
    }).catch(function (error) {
      if (asked !== state.rechecks) { return; }
      state.status = applied + ' The pre-flight recheck did not run: ' + error.message + '.';
      render();
    });
  }

  function choose(seat, modelKey) {
    if (state.busy) { return; }
    state.busy = true;
    state.open = null;
    api('POST', '/api/seats/' + encodeURIComponent(seat), { model: modelKey }).then(function (result) {
      var label = result.model.label;
      var applied = result.applied === 'next-dispatch'
        ? 'Applied to the live run: the next dispatch uses ' + label + '.'
        : 'Applied: the next run uses ' + label + '.';
      state.status = applied + ' Checking ' + label + '.';
      state.busy = false;
      recheck(modelKey, label, applied);
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
