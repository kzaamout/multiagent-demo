/* Pure reducer: the run's event list becomes the view model. Nothing else is run state.
   No timers, no inference beyond what the events say (constitution II). */
(function (global) {
  'use strict';
  var F = global.S1Format;

  function stageTransitions(events) {
    return events.filter(function (e) { return e.type === 'stage.changed'; });
  }

  function agentOf(event) { return typeof event.actor === 'object' && event.actor ? event.actor : null; }

  function reduce(events, ctx) {
    ctx = ctx || {};
    var budget = ctx.retryBudget || 2;
    var ceiling = ctx.costCeiling || 5;
    var view = {
      hasRun: events.length > 0,
      runId: null,
      datasetId: null,
      workflow: null,
      startMs: 0,
      elapsedMs: 0,
      roster: {},
      nodes: {},
      fired: {},
      firedEventIds: {},
      retryText: 'retry 0 of ' + budget,
      banner: null,
      blockerPending: null,
      handoffPending: false,
      terminated: null,
      cards: [],
      meters: {},
      totalCost: 0,
      ceiling: ceiling,
      ceilingPct: '0%',
      raw: events,
      latestDraft: null,
      eventCount: events.length
    };
    if (!events.length) {
      F.STAGES.forEach(function (s) { view.nodes[s] = 'idle'; });
      return view;
    }

    var byId = {};
    var cardsById = {};
    var cards = [];
    function addCard(card) { cardsById[card.id] = card; cards.push(card); return card; }

    var entered = {};
    var current = null;
    var pausedByHuman = false;
    var handoffReady = false;
    var terminated = null;
    var retry = { count: 0, budget: budget };
    var questions = {};        /* question_id -> clarification.needed payload */
    var asks = [];             /* clarification.asked events without blocker */
    var answered = {};         /* question_id -> answered event */
    var tasks = {};            /* task_id -> subtask from plan */
    var plan = null;
    var threads = {};          /* task_id -> thread card */
    var drafts = {};
    var intakeCards = {};      /* prompt_ref -> card */

    events.forEach(function (event) {
      byId[event.event_id] = event;
      var agent = agentOf(event);
      if (agent) { view.roster[agent.agent_id] = agent; }
      var p = event.payload || {};
      var time = F.tsMs(event.ts);
      switch (event.type) {
        case 'run.started':
          view.runId = event.run_id;
          view.datasetId = p.dataset_id;
          view.workflow = p.workflow;
          view.startMs = time;
          (p.roster || []).forEach(function (a) { view.roster[a.agent_id] = a; });
          addCard({ id: 'start', kind: 'orchestrator-note', event: event, first: event, stage: 'intake' });
          break;
        case 'stage.changed':
          if (current) { entered[current] = true; }
          current = p.to;
          entered[p.to] = true;
          if (p.direction === 'backward') {
            var key = p.from + '-' + p.to;
            view.fired[key] = true;
            view.firedEventIds[key] = event.event_id;
            addCard({ id: 'route:' + event.event_id, kind: 'orchestrator-note', role: 'route', event: event, retry: { count: retry.count, budget: retry.budget } });
          }
          break;
        case 'intake.brief':
        case 'intake.readiness':
        case 'clarification.needed': {
          var ref = event.prompt_ref || event.event_id;
          var card = intakeCards[ref];
          if (!card) {
            card = addCard({ id: 'intake:' + ref, kind: 'agent-message', role: 'intake', agent: agent, events: [], brief: null, readiness: null, event: event });
            intakeCards[ref] = card;
          }
          card.events.push(event);
          if (event.type === 'intake.brief') { card.brief = p.brief; }
          if (event.type === 'intake.readiness') { card.readiness = event; card.event = event; }
          if (event.type === 'clarification.needed') { questions[p.question_id] = p; }
          card.promptRef = event.prompt_ref;
          break;
        }
        case 'assumption.accepted':
          addCard({ id: 'assume:' + p.question_id, kind: 'assumption', event: event });
          break;
        case 'clarification.asked':
          if (p.blocker) {
            addCard({ id: 'blocker:' + p.blocker.blocker_id, kind: 'blocker', event: event, blocker: p.blocker, answer: null });
            view.blockerPending = { event: event, blocker: p.blocker };
          } else {
            var askCard = addCard({ id: 'ask:' + event.event_id, kind: 'question', event: event, questionIds: p.question_ids.slice(), answers: [] });
            asks.push(askCard);
          }
          break;
        case 'clarification.answered': {
          answered[p.question_id] = event;
          var blockerCard = cardsById['blocker:' + p.question_id];
          if (blockerCard) {
            blockerCard.answer = event;
            view.blockerPending = null;
            addCard({ id: 'banswer:' + p.question_id, kind: 'human-answer', role: 'blocker', event: event, answers: [event] });
            break;
          }
          var ask = asks.filter(function (a) { return a.questionIds.indexOf(p.question_id) !== -1; })[0];
          if (ask) {
            ask.answers.push(event);
            var groupId = 'answers:' + ask.event.event_id;
            if (!cardsById[groupId]) {
              addCard({ id: groupId, kind: 'human-answer', role: 'clarifications', event: event, answers: ask.answers });
            }
          }
          break;
        }
        case 'plan.created':
          plan = p.subtasks;
          p.subtasks.forEach(function (t, i) { tasks[t.task_id] = { subtask: t, index: i }; });
          addCard({ id: 'plan:' + event.event_id, kind: 'orchestrator-note', role: 'plan', event: event, subtasks: p.subtasks });
          break;
        case 'task.dispatched': {
          if (p.agent_id === 'writer') { break; }
          var thread = addCard({
            id: 'thread:' + p.task_id, kind: 'specialist-thread', taskId: p.task_id, agentId: p.agent_id,
            dispatch: event, replies: [], completed: null, blocker: null, event: event, promptRef: null
          });
          threads[p.task_id] = thread;
          break;
        }
        case 'task.progress':
        case 'tool.called':
        case 'task.completed':
        case 'blocker.raised': {
          var th = threads[p.task_id];
          if (!th) {
            th = addCard({ id: 'thread:' + p.task_id, kind: 'specialist-thread', taskId: p.task_id, agentId: p.agent_id, dispatch: null, replies: [], completed: null, blocker: null, event: event, promptRef: null });
            threads[p.task_id] = th;
          }
          th.replies.push(event);
          th.event = event;
          th.promptRef = event.prompt_ref || th.promptRef;
          if (event.type === 'task.completed') { th.completed = event; }
          if (event.type === 'blocker.raised') { th.blocker = event; }
          break;
        }
        case 'draft.committed':
          drafts[p.version] = addCard({ id: 'draft:' + p.version + ':' + event.event_id, kind: 'draft-committed', event: event });
          view.latestDraft = { version: p.version, path: p.markdown_path, runId: event.run_id, eventId: event.event_id };
          break;
        case 'review.verdict':
          addCard({ id: 'verdict:' + event.event_id, kind: 'verdict', event: event, draftVersion: Object.keys(drafts).length });
          break;
        case 'retry.incremented':
          retry = { count: p.count, budget: p.budget };
          break;
        case 'handoff.ready':
          handoffReady = true;
          view.handoffPending = true;
          addCard({ id: 'term', kind: 'termination', event: event, handoff: event, terminated: null, retry: { count: retry.count, budget: retry.budget } });
          break;
        case 'human.approved':
          view.handoffPending = false;
          break;
        case 'run.paused':
          pausedByHuman = true;
          addCard({ id: 'paused:' + event.event_id, kind: 'orchestrator-note', role: 'paused', event: event });
          break;
        case 'run.resumed':
          pausedByHuman = false;
          addCard({ id: 'resumed:' + event.event_id, kind: 'orchestrator-note', role: 'resumed', event: event });
          break;
        case 'meter.update': {
          var m = view.meters[p.agent_id] || (view.meters[p.agent_id] = { tokens: 0, tokensIn: 0, tokensOut: 0, cost: 0, calls: 0, wallMs: 0, lastEvent: 'none' });
          m.tokensIn += p.tokens_in;
          m.tokensOut += p.tokens_out;
          m.tokens += p.tokens_in + p.tokens_out;
          m.cost += p.est_cost;
          m.calls += 1;
          m.wallMs += p.wall_ms;
          view.totalCost += p.est_cost;
          break;
        }
        case 'run.terminated':
          terminated = event;
          var term = cardsById.term;
          if (term) { term.terminated = event; term.event = event; }
          else { addCard({ id: 'term', kind: 'termination', event: event, handoff: null, terminated: event, retry: { count: retry.count, budget: retry.budget } }); }
          view.handoffPending = false;
          view.blockerPending = null;
          break;
        default:
          break;
      }
      if (agent && event.type !== 'meter.update') {
        var meter = view.meters[agent.agent_id] || (view.meters[agent.agent_id] = { tokens: 0, tokensIn: 0, tokensOut: 0, cost: 0, calls: 0, wallMs: 0, lastEvent: 'none' });
        meter.lastEvent = event.type;
      }
    });

    var last = events[events.length - 1];
    view.elapsedMs = F.tsMs(last.ts) - view.startMs;
    view.retryText = 'retry ' + retry.count + ' of ' + retry.budget;
    view.terminated = terminated;
    view.ceilingPct = Math.round(view.totalCost / ceiling * 100) + '%';

    /* Pending clarifications: open asks with unanswered questions. */
    var openAsk = asks.filter(function (a) {
      return a.questionIds.some(function (q) { return !answered[q]; });
    })[0];
    if (openAsk && !terminated) {
      view.banner = {
        askEvent: openAsk.event,
        questions: openAsk.questionIds.map(function (q) { return Object.assign({ question_id: q }, questions[q] || { question: q, proposed_default: '', why_it_matters: '' }); })
      };
    }
    /* The question card gives way to the answer card once every question is answered (as in the export). */
    cards = cards.filter(function (c) {
      if (c.kind !== 'question') { return true; }
      return c.questionIds.some(function (q) { return !answered[q]; });
    });

    var humanPending = !!view.banner || !!view.blockerPending;
    var pausedStage = (humanPending || pausedByHuman) && !terminated;
    F.STAGES.forEach(function (s) {
      var state = 'idle';
      if (terminated) { state = entered[s] ? 'complete' : 'idle'; }
      else if (s === current) {
        if (pausedStage) { state = 'paused'; }
        else if (s === 'handoff' && handoffReady) { state = 'complete'; }
        else { state = 'active'; }
      } else if (entered[s]) { state = 'complete'; }
      view.nodes[s] = state;
    });

    /* Thread status and plan glyphs. */
    Object.keys(threads).forEach(function (taskId) {
      var t = threads[taskId];
      var sub = tasks[taskId] ? tasks[taskId].subtask : null;
      var deps = sub ? sub.depends_on : [];
      var waitingOn = deps.filter(function (d) { return !(threads[d] && threads[d].completed); });
      t.subtask = sub;
      if (t.completed) { t.status = 'complete'; }
      else if (t.blocker) { t.status = 'blocked'; }
      else if (t.replies.length === 0 && waitingOn.length) { t.status = 'waiting'; t.waitingOn = waitingOn; }
      else { t.status = terminated ? 'stopped' : 'active'; }
    });
    view.threads = threads;
    view.plan = plan;
    view.tasks = tasks;
    view.cards = cards;
    view.byId = byId;
    view.questions = questions;
    view.answered = answered;
    return view;
  }

  global.S1Reducer = { reduce: reduce, stageTransitions: stageTransitions };
})(window);
