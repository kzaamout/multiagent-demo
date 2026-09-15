/* Demo page wiring. The page holds the run's events and re-renders from them; the only other
   state is presentation state (which cards are open, the chosen dataset and speed). */
(function () {
  'use strict';
  var F = window.S1Format;
  var EXPORT_NAMES = { orchestrator: 'Oscar', intake: 'Anna', estimator: 'Elena', pricing: 'Pavel', writer: 'Willa', reviewer: 'Rafael' };

  var params = new URLSearchParams(window.location.search);
  var events = [];
  var stream = null;
  var runId = null;
  var ui = {
    open: {}, promptOpen: {}, prompts: {}, mode: 'idle', speed: 1, submitting: false,
    meterOpen: null, rawOpen: false, compareOpen: false, animatedArrows: {}, animate: params.get('animate') !== '0',
    autoScroll: true, bannerAskId: null, drafts: {}, loadDraft: null, dryIntake: false, following: false
  };
  var ctx = { datasets: [], selectedDataset: null, retryBudget: 2, costCeiling: 5, idleRoster: {} };
  var scheduled = false;

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

  function render() {
    scheduled = false;
    var view = window.S1Reducer.reduce(events, ctx);
    window.S1Render.renderAll(view, ui, ctx);
    window.__s1 = { view: view, ui: ui, ctx: ctx, events: events };
  }

  function schedule() {
    if (scheduled) { return; }
    scheduled = true;
    /* Animation frames do not fire while the tab is hidden; keep the page current anyway so it
       is right the moment the projector window is shown. */
    if (document.hidden) { window.setTimeout(render, 50); } else { window.requestAnimationFrame(render); }
  }

  ui.loadDraft = function (runId, path) {
    var key = runId + '/' + path;
    if (ui.drafts[key]) { return; }
    ui.drafts[key] = { status: 'loading' };
    fetch('/api/runs/' + encodeURIComponent(runId) + '/files/' + path.split('/').map(encodeURIComponent).join('/'))
      .then(function (response) {
        if (!response.ok) { throw new Error(String(response.status)); }
        return response.text();
      })
      .then(function (text) { ui.drafts[key] = { status: 'loaded', text: text }; schedule(); })
      .catch(function () { ui.drafts[key] = { status: 'missing' }; schedule(); });
  };

  function onEvent(event) {
    events.push(event);
    if (event.type === 'clarification.answered' || event.type === 'human.approved' || event.type === 'run.terminated') {
      ui.submitting = false;
    }
    schedule();
  }

  function openStream(url, since) {
    if (stream) { stream.close(); }
    stream = new window.S1EventStream(url, { sinceSeq: since || 0, onEvent: onEvent, onClose: schedule });
    stream.open();
  }

  function resetView(mode) {
    events = [];
    ui.open = {};
    ui.promptOpen = {};
    ui.animatedArrows = {};
    ui.bannerAskId = null;
    ui.meterOpen = null;
    ui.submitting = false;
    ui.mode = mode;
    ui.following = false;
    var feed = document.getElementById('feed');
    Array.prototype.forEach.call(feed.querySelectorAll('article.card'), function (n) { n.remove(); });
  }

  function refreshDatasets() {
    return api('GET', '/api/datasets').then(function (list) { ctx.datasets = list; schedule(); });
  }

  function startRun() {
    if (!ctx.selectedDataset || isBusy()) { return; }
    var body = { dataset_id: ctx.selectedDataset, dry_intake: ui.dryIntake };
    if (params.get('pin') === 'export') { body.names = EXPORT_NAMES; }
    api('POST', '/api/runs', body).then(function (data) {
      resetView('live');
      ui.following = true;
      runId = data.run_id;
      ctx.retryBudget = data.retry_budget;
      ctx.costCeiling = data.cost_ceiling;
      openStream(data.stream_url, 0);
      schedule();
    }).catch(function (error) {
      window.alertless(error);
      if (!events.length) { document.getElementById('feed-empty').textContent = String(error && error.message ? error.message : error); }
    });
  }

  function startReplay() {
    if (!ctx.selectedDataset || isBusy()) { return; }
    api('POST', '/api/replays', { dataset_id: ctx.selectedDataset, speed: ui.speed }).then(function (data) {
      resetView('replay');
      runId = data.run_id;
      openStream(data.stream_url, 0);
      schedule();
    }).catch(function (error) { window.alertless(error); });
  }

  function isBusy() {
    if (ui.mode === 'idle') { return false; }
    var last = events[events.length - 1];
    return !(last && last.type === 'run.terminated');
  }

  function submitAnswers(answers) {
    if (ui.mode !== 'live' || !runId) { return; }
    ui.submitting = true;
    schedule();
    api('POST', '/api/runs/' + runId + '/answers', { answers: answers }).catch(function (error) {
      ui.submitting = false;
      schedule();
      window.alertless(error);
    });
  }

  window.alertless = function (error) {
    /* No browser dialogs on a projector: report in the console and the raw drawer label. */
    console.error('[demo]', error);
    document.getElementById('raw-label').textContent = 'Error: ' + (error && error.message ? error.message : error);
  };

  function cardIsOpen(node) {
    var chev = node.querySelector('.card-hd .chev-sm');
    return chev ? chev.textContent === '▾' : false;
  }

  document.addEventListener('click', function (e) {
    var target = e.target;
    var menu = document.getElementById('dataset-menu');
    var select = document.getElementById('dataset-select');

    var item = target.closest('[data-dataset]');
    if (item) {
      ctx.selectedDataset = item.getAttribute('data-dataset');
      try { window.localStorage.setItem('s1.dataset', ctx.selectedDataset); } catch (err) { /* private mode */ }
      menu.hidden = true;
      schedule();
      return;
    }
    if (target.closest('#dataset-select')) {
      if (!select.classList.contains('is-locked')) {
        menu.hidden = !menu.hidden;
        if (!menu.hidden) { buildMenu(); }
      }
      return;
    }
    menu.hidden = true;

    var actionNode = target.closest('[data-action]');
    if (!actionNode) {
      if (target.closest('#btn-run')) { startRun(); }
      return;
    }
    var action = actionNode.getAttribute('data-action');
    if (action === 'none') { e.stopPropagation(); return; }
    if (action === 'prompt') {
      var id = actionNode.getAttribute('data-card');
      var ref = actionNode.getAttribute('data-ref');
      ui.promptOpen[id] = !ui.promptOpen[id];
      if (ui.promptOpen[id] && !ui.prompts[ref]) {
        api('GET', '/api/prompts/' + encodeURIComponent(ref)).then(function (bundle) { ui.prompts[ref] = bundle; schedule(); })
          .catch(function (error) { window.alertless(error); });
      }
      schedule();
      return;
    }
    if (action === 'blocker-answer' || action === 'blocker-escalate') {
      var blockerId = actionNode.getAttribute('data-blocker');
      var input = document.querySelector('input[data-blocker-input="' + blockerId + '"]');
      var text = input ? input.value.trim() : '';
      if (action === 'blocker-answer' && !text) { if (input) { input.focus(); } return; }
      submitAnswers([{ question_id: blockerId, answer: text, action: action === 'blocker-answer' ? 'answer' : 'escalate' }]);
      return;
    }
    if (action === 'control-pause' || action === 'control-resume' || action === 'control-stop') {
      if (ui.mode !== 'live' || !ui.following || !runId) { return; }
      var route = action === 'control-pause' ? 'pause' : action === 'control-resume' ? 'resume' : 'stop';
      api('POST', '/api/runs/' + runId + '/' + route).catch(function (error) { window.alertless(error); });
      return;
    }
    if (action === 'dry-off' || action === 'dry-on') {
      if (isBusy()) { return; }
      ui.dryIntake = action === 'dry-on';
      schedule();
      return;
    }
    if (action === 'meter') {
      var agentId = actionNode.getAttribute('data-agent');
      ui.meterOpen = ui.meterOpen === agentId ? null : agentId;
      schedule();
      return;
    }
    if (action === 'meter-close') { ui.meterOpen = null; schedule(); return; }
    if (action === 'toggle') {
      if (target.closest('input, .prompt-panel, .blocker-actions, a')) { return; }
      var cardId = actionNode.getAttribute('data-card');
      ui.open[cardId] = !cardIsOpen(actionNode);
      schedule();
    }
  });

  function buildMenu() {
    var menu = document.getElementById('dataset-menu');
    menu.innerHTML = '';
    ctx.datasets.forEach(function (d) {
      menu.appendChild(F.el('button', {
        class: 'menu-item', type: 'button', role: 'option', 'data-dataset': d.id,
        'aria-selected': String(d.id === ctx.selectedDataset)
      }, [d.label, F.el('span', { class: 'menu-note', text: d.replay_source === 'recording' ? 'recorded' : d.replay_source === 'golden' ? 'golden log' : '' })]));
    });
  }

  document.getElementById('banner-resume').addEventListener('click', function () {
    var inputs = document.querySelectorAll('#banner-questions input[data-question]');
    var answers = Array.prototype.map.call(inputs, function (input) {
      return { question_id: input.getAttribute('data-question'), answer: input.value.trim(), action: 'answer' };
    });
    submitAnswers(answers);
  });

  document.getElementById('btn-approve').addEventListener('click', function () {
    if (ui.mode !== 'live' || !runId) { return; }
    ui.submitting = true;
    schedule();
    api('POST', '/api/runs/' + runId + '/decision', { decision: 'approve', notes: '' }).catch(function (error) {
      ui.submitting = false;
      schedule();
      window.alertless(error);
    });
  });

  document.getElementById('btn-replay').addEventListener('click', startReplay);
  ['speed-1', 'speed-4'].forEach(function (id) {
    document.getElementById(id).addEventListener('click', function (e) {
      if (isBusy()) { return; }
      ui.speed = Number(e.currentTarget.getAttribute('data-speed'));
      schedule();
    });
  });
  document.getElementById('raw-btn').addEventListener('click', function () { ui.rawOpen = !ui.rawOpen; schedule(); });
  document.getElementById('compare-btn').addEventListener('click', function () { ui.compareOpen = !ui.compareOpen; schedule(); });
  document.getElementById('feed').addEventListener('scroll', function (e) {
    var feed = e.currentTarget;
    ui.autoScroll = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 80;
  });

  Promise.all([api('GET', '/api/meta'), api('GET', '/api/datasets')]).then(function (results) {
    var meta = results[0];
    ctx.datasets = results[1];
    ctx.retryBudget = meta.retry_budget;
    ctx.costCeiling = meta.cost_ceiling;
    ctx.idleRoster = meta.idle_roster || {};
    var stored = null;
    try { stored = window.localStorage.getItem('s1.dataset'); } catch (err) { stored = null; }
    var wanted = params.get('dataset') || stored || 'planted-inconsistency';
    ctx.selectedDataset = ctx.datasets.some(function (d) { return d.id === wanted; }) ? wanted : (ctx.datasets[0] || {}).id;
    var recordedRun = params.get('run');
    if (recordedRun) {
      /* A recorded run rendered from its event list, used to compare a replay with its source. */
      return api('GET', '/api/runs/' + encodeURIComponent(recordedRun) + '/events').then(function (list) {
        resetView('replay');
        ui.animate = false;
        ui.autoScroll = false;
        events = list;
        schedule();
      });
    }
    var goldenId = params.get('golden');
    if (goldenId) {
      /* Fixed state for screenshot comparison: a prefix of the committed golden log, rendered
         through the same reducer and renderer as a live run. */
      var upto = params.get('upto');
      return api('GET', '/api/datasets/' + encodeURIComponent(goldenId) + '/golden' + (upto ? '?upto=' + upto : '')).then(function (list) {
        resetView(params.get('as') || 'live');
        ui.animate = false;
        ui.autoScroll = false;
        ctx.selectedDataset = goldenId;
        events = list;
        schedule();
      });
    }
    if (meta.live_run_id) {
      runId = meta.live_run_id;
      return api('GET', '/api/runs/' + runId + '/events').then(function (list) {
        resetView('live');
        events = list;
        openStream('/api/streams/' + runId + '/events', list.length ? list[list.length - 1].seq : 0);
        schedule();
      });
    }
    schedule();
    return null;
  }).catch(function (error) { window.alertless(error); });

  document.addEventListener('visibilitychange', function () { if (!document.hidden) { scheduled = false; render(); refreshDatasets(); } });
})();
