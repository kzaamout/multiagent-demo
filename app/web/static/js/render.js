/* Render the view model into the flattened Demo page. Cards are replaced in place only when
   their markup changes, so the page never flickers and typed input survives. */
(function (global) {
  'use strict';
  var F = global.S1Format;
  var el = F.el;

  var ROSTER_ORDER = ['orchestrator', 'intake', 'estimator', 'pricing', 'writer', 'reviewer'];
  var HUMAN = { agent_id: 'human', name: 'You', role: '', model: { label: 'human' } };

  function clock(view, event) { return F.fmtClock(F.tsMs(event.ts) - view.startMs); }

  function agentCard(agent, size) {
    var a = agent || HUMAN;
    var name = a.role ? a.name + ', ' + a.role : a.name;
    return el('div', { class: 'agent' + (size ? ' agent-' + size : ''), 'data-part': 'agent-card' }, [
      el('div', { class: 'avatar', 'data-part': 'avatar', style: 'background:' + F.seatColor(a.agent_id), text: F.initials(a.name) }),
      el('div', { class: 'agent-text' }, [
        el('div', { class: 'agent-name', 'data-part': 'name', text: name }),
        el('div', { class: 'agent-model', 'data-part': 'model', text: a.model ? a.model.label : '' })
      ])
    ]);
  }

  function roleOf(view, agentId) {
    var a = view.roster[agentId];
    return a ? a.role : agentId;
  }

  function header(card, left, summary, phase, time, open, ui) {
    /* Unread count: replies added since the presenter last had the thread open, shown while the task is live. */
    var replyCount = (card.replies || []).length;
    if (open) { ui.seen[card.id] = replyCount; }
    var unread = open ? 0 : replyCount - (ui.seen[card.id] || 0);
    var chip = card.live && unread > 0 ? el('span', { class: 'unread-chip', 'data-part': 'unread', text: unread + ' new' }) : null;
    return el('div', { class: 'card-hd', 'data-part': 'card-header' }, [
      left,
      el('span', { class: 'summary', 'data-part': 'summary', text: summary }),
      el('div', { class: 'card-meta' }, [
        chip,
        el('span', { class: 'phase', 'data-part': 'phase', text: phase }),
        el('span', { class: 'time', 'data-part': 'time', text: time }),
        el('span', { class: 'chev-sm', text: open ? '▾' : '▸' })
      ])
    ]);
  }

  function eventLabel(text) { return el('div', { class: 'event-label', 'data-part': 'event', text: text }); }
  function para(text, extra) { return el('p', { class: 'body-p' + (extra ? ' ' + extra : ''), text: text }); }
  function why(reason) {
    return el('p', { class: 'why', 'data-part': 'why' }, [el('span', { class: 'why-k', text: 'Why' }), ' ' + reason]);
  }

  function promptRow(card, ui, promptRef) {
    var open = !!ui.promptOpen[card.id];
    var nodes = [];
    var button;
    if (promptRef) {
      button = el('button', { class: 'prompt-btn', type: 'button', 'data-action': 'prompt', 'data-card': card.id, 'data-ref': promptRef, text: open ? 'prompt ▾' : 'prompt ▸' });
    } else {
      button = el('button', { class: 'prompt-btn', type: 'button', 'data-action': 'none', title: 'The Orchestrator is the state machine in this slice; no model call was made for this event.', text: 'prompt ▸' });
    }
    nodes.push(el('div', { class: 'prompt-row' }, [button]));
    if (promptRef && open) {
      var bundle = ui.prompts[promptRef];
      var panel = el('div', { class: 'prompt-panel', 'data-part': 'prompt-panel' }, []);
      if (!bundle) {
        panel.appendChild(el('div', { class: 'prompt-sec-label', text: 'Loading prompt bundle' }));
      } else {
        bundle.sections.forEach(function (sec) {
          panel.appendChild(el('div', {}, [
            el('div', { class: 'prompt-sec-label', text: sec.label }),
            el('pre', { class: 'prompt-sec-text', text: sec.text })
          ]));
        });
      }
      nodes.push(panel);
    }
    return nodes;
  }

  function defaultOpen(card, view, ui) {
    /* Threads start collapsed and stay collapsed until clicked (spec 0.7, 2.2). The blocker card is the
       human's door and stays open while it waits. */
    if (card.kind === 'blocker') { return !card.answer && !view.terminated; }
    return false;
  }

  function isOpen(card, view, ui) {
    return Object.prototype.hasOwnProperty.call(ui.open, card.id) ? ui.open[card.id] : defaultOpen(card, view, ui);
  }

  function datasetText(view, ctx) {
    var d = (ctx.datasets || []).filter(function (x) { return x.id === view.datasetId; })[0];
    return d ? d.label.replace(' · ', ' ') : view.datasetId;
  }

  /* Card builders */

  function noteCard(card, view, ui, ctx) {
    var e = card.event;
    var orch = view.roster.orchestrator;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var summary, phase, body = [];
    if (card.role === 'plan') {
      var subtasks = card.subtasks;
      var waits = subtasks.filter(function (s) { return s.agent_id !== 'writer' && s.depends_on.length; }).map(function (s) {
        var dep = subtasks.filter(function (x) { return x.task_id === s.depends_on[0]; })[0];
        return roleOf(view, s.agent_id) + ' waits for the ' + roleOf(view, dep ? dep.agent_id : '');
      });
      summary = 'Plan created, ' + subtasks.length + ' sub-tasks, moving to Work';
      phase = 'Plan';
      body.push(eventLabel(t + ' · plan.created'));
      body.push(para('Plan created. ' + F.words(subtasks.length) + ' sub-tasks' + (waits.length ? '; ' + waits.join('; ') : '') + '. Moving to Work.'));
      body.push(why(e.reason));
      body.push(planCard(subtasks, view));
    } else if (card.role === 'route') {
      var p = e.payload;
      var to = F.STAGE_LABEL[p.to];
      summary = p.from === 'review'
        ? 'Review failed, routing back to ' + to + ', retry ' + card.retry.count + ' of ' + card.retry.budget
        : 'Routing back to ' + to;
      phase = F.STAGE_LABEL[p.from] || to;
      body.push(eventLabel(t + ' · stage.changed backward'));
      body.push(para(p.target_reason));
      body.push(why(e.reason));
    } else if (card.role === 'paused' || card.role === 'resumed') {
      summary = card.role === 'paused' ? 'Run paused by the presenter' : 'Run resumed by the presenter';
      phase = F.STAGE_LABEL[e.stage] || '';
      body.push(eventLabel(t + ' · ' + e.type));
      body.push(why(e.reason));
    } else {
      var intake = view.roster.intake ? view.roster.intake.name : 'Intake';
      var p0 = e.payload;
      summary = 'Run started, dispatching Intake to ' + intake;
      phase = 'Intake';
      body.push(eventLabel(t + ' · run.started'));
      body.push(para('Run started. Workflow ' + (F.WORKFLOW_LABEL[p0.workflow] || p0.workflow) + ', dataset ' + datasetText(view, ctx) + ', ' + (p0.mode === 'single' ? 'Single model' : 'Team') + ' mode. Dispatching Intake to ' + intake + '.'));
      body.push(why(e.reason));
    }
    var children = [header(card, agentCard(orch), summary, phase, t, open, ui)];
    if (open) { children = children.concat(body, card.role === 'plan' ? [] : [], promptRow(card, ui, null)); }
    return children;
  }

  function planCard(subtasks, view) {
    var indexOf = {};
    subtasks.forEach(function (s, i) { indexOf[s.task_id] = i + 1; });
    return el('div', { class: 'plan-card', 'data-kind': 'plan-card' }, subtasks.map(function (s, i) {
      var thread = view.threads[s.task_id];
      var status = thread ? (thread.status === 'complete' ? 'complete' : thread.status === 'active' ? 'active' : 'waiting') : 'waiting';
      if (s.agent_id === 'writer' && view.cards.some(function (c) { return c.kind === 'draft-committed'; })) { status = 'complete'; }
      var glyph = status === 'complete' ? '✓' : status === 'active' ? '●' : '○';
      var deps = s.depends_on.map(function (d) { return indexOf[d]; }).filter(Boolean);
      var depText = deps.length === 0 ? 'no dependency'
        : '↳ after ' + (deps.length === 1 ? deps[0] : deps.slice(0, -1).join(', ') + ' and ' + deps[deps.length - 1]);
      return el('div', { class: 'plan-row' }, [
        el('span', { class: 'plan-glyph', 'data-status': status, text: glyph }),
        el('span', { class: 'plan-title', text: (i + 1) + ' · ' + s.title }),
        agentCard(view.roster[s.agent_id], 'sm'),
        el('span', { class: 'plan-dep', text: depText })
      ]);
    }));
  }

  function intakeCard(card, view, ui) {
    var open = isOpen(card, view, ui);
    var readiness = card.readiness;
    var intakeProgress = (card.replies || []).filter(function (r) { return r.type === 'task.progress'; });
    var summary = intakeProgress.length ? intakeProgress[intakeProgress.length - 1].payload.message : 'Reading the request';
    var t = clock(view, card.event);
    var body = [];
    if (readiness) {
      var p = readiness.payload;
      var total = p.checklist.length;
      var pass = p.checklist.filter(function (c) { return c.status === 'pass'; }).length;
      var verdictText = { ready: 'Brief ready', ready_with_assumptions: 'Brief ready with assumptions', not_ready: 'Not ready' }[p.verdict];
      summary = verdictText + ', ' + pass + ' of ' + total + ' checks pass';
      body.push(eventLabel(t + ' · intake.readiness'));
      var sentence = verdictText + '. Readiness checklist: ' + pass + ' of ' + total + ' items pass.';
      if (p.legibility.length) {
        var lowest = p.legibility.reduce(function (a, b) { return b.confidence < a.confidence ? b : a; });
        var pages = card.brief && card.brief.drawing_pages ? card.brief.drawing_pages : p.legibility.length;
        sentence += ' Legibility across ' + pages + ' drawing pages: lowest confidence ' + lowest.confidence.toFixed(2) + ' on ' + lowest.page + '.';
      }
      body.push(para(sentence));
      body.push(el('ul', { class: 'checklist' }, p.checklist.map(function (c) {
        var glyph = c.status === 'pass' ? '✓' : c.status === 'fail' ? '✕' : '!';
        return el('li', { title: c.note || null }, [el('span', { class: 'ck-' + c.status, text: glyph }), ' ' + c.item]);
      })));
    }
    if (card.replies && card.replies.length) { body.push(repliesBlock(view, card.replies, !readiness && !view.terminated)); }
    var children = [header(card, agentCard(card.agent), summary, 'Intake', t, open, ui)];
    if (open) { children = children.concat(body, promptRow(card, ui, card.promptRef)); }
    return children;
  }

  function assumptionCard(card, view, ui) {
    var e = card.event;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var text = 'Proceeding on default: ' + F.labelFromId(e.payload.question_id, true) + ' ' + e.payload.default_used;
    var children = [header(card, agentCard(view.roster.orchestrator), text, F.STAGE_LABEL[e.stage] || 'Intake', t, open, ui)];
    if (open) {
      children = children.concat([eventLabel(t + ' · assumption.accepted'), para(text + '. Flagged for Handoff.'), why(e.reason)], promptRow(card, ui, null));
    }
    return children;
  }

  function questionCard(card, view, ui) {
    var e = card.event;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var n = card.questionIds.length;
    var summary = 'Paused on ' + n + ' blocking ' + F.plural(n, 'question') + ', batched';
    var children = [header(card, agentCard(view.roster.orchestrator), summary, F.STAGE_LABEL[e.stage] || 'Intake', t, open, ui)];
    if (open) {
      children = children.concat([
        eventLabel(t + ' · clarification.asked'),
        para(F.words(n) + ' blocking ' + F.plural(n, 'question') + ' from Intake, batched. The run is paused until you answer above.'),
        el('ol', { class: 'q-list' }, card.questionIds.map(function (q) {
          var info = view.questions[q] || { question: q, proposed_default: '' };
          return el('li', {}, [info.question + ' ', el('span', { class: 'q-default', text: 'Proposed default: ' + info.proposed_default + '.' })]);
        })),
        why(e.reason)
      ], promptRow(card, ui, null));
    }
    return children;
  }

  function answerCard(card, view, ui) {
    var e = card.event;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var summary, text;
    if (card.role === 'blocker') {
      var escalated = e.payload.action === 'escalate';
      summary = escalated ? 'Escalated the blocker' : 'Answered: ' + e.payload.answer;
      text = escalated ? 'Escalated. ' + (e.payload.answer || '') : 'Answer to the blocker: ' + e.payload.answer + '.';
    } else {
      summary = 'Answered: ' + card.answers.map(function (a) { return a.payload.answer; }).join(', ');
      text = card.answers.map(function (a) { return F.labelFromId(a.payload.question_id) + ': ' + a.payload.answer + '.'; }).join(' ');
    }
    var children = [header(card, agentCard(HUMAN), summary, F.STAGE_LABEL[e.stage] || '', t, open, ui)];
    if (open) { children = children.concat([eventLabel(t + ' · clarification.answered'), para(text.trim())]); }
    return children;
  }

  function repliesBlock(view, replies, live) {
    var lastIndex = replies.length - 1;
    return el('div', { class: 'replies', 'data-part': 'replies' }, replies.map(function (r, i) {
      var p = r.payload;
      var text;
      if (r.type === 'task.progress') {
        var isLive = live && i === lastIndex;
        text = el('p', { class: 'reply-text' + (isLive ? ' is-live' : '') }, isLive
          ? [p.message + ' ', el('span', { class: 'dots' }, [el('span', { class: 'dot' }), el('span', { class: 'dot' }), el('span', { class: 'dot' })])]
          : [p.message]);
      } else if (r.type === 'tool.called') {
        text = el('p', { class: 'reply-text' }, [el('span', { class: 'tool-chip', text: p.tool }), p.args_summary + ' · ' + p.result_summary + ' · ' + F.fmtSeconds(p.duration_ms)]);
      } else if (r.type === 'task.completed') {
        text = el('p', { class: 'reply-text' }, [el('span', { class: 'tick', text: '✓' }), ' ' + (p.result.summary || p.result.headline || 'Complete')]);
      } else {
        text = el('p', { class: 'reply-text is-blocker', text: 'Blocker: ' + p.description });
      }
      return el('div', { class: 'reply' }, [el('span', { class: 'reply-time', text: clock(view, r) }), text]);
    }));
  }

  function threadSummary(card, view) {
    if (card.status === 'complete') { return card.completed.payload.result.headline || 'Complete'; }
    if (card.status === 'blocked') { return 'Blocked: ' + card.blocker.payload.description; }
    if (card.status === 'waiting') { return 'Waiting for the ' + roleOf(view, (view.threads[card.waitingOn[0]] || {}).agentId || ''); }
    var progress = card.replies.filter(function (r) { return r.type === 'task.progress'; });
    var lastProgress = progress[progress.length - 1];
    if (lastProgress) { return lastProgress.payload.headline || lastProgress.payload.message; }
    return card.dispatch ? card.dispatch.payload.inputs_summary : '';
  }

  function threadCard(card, view, ui) {
    var open = isOpen(card, view, ui);
    var agent = view.roster[card.agentId];
    var last = card.event;
    var t = clock(view, last);
    var phase = F.STAGE_LABEL[(card.dispatch || last).stage] || 'Work';
    var children = [header(card, agentCard(agent), threadSummary(card, view), phase, t, open, ui)];
    if (!open) { return children; }
    var stamp = card.completed ? clock(view, card.completed) + ' · task.completed' : card.dispatch ? clock(view, card.dispatch) + ' · task.dispatched' : t + ' · ' + last.type;
    children.push(eventLabel(stamp));
    if (card.dispatch) { children.push(para(card.dispatch.payload.inputs_summary)); }
    if (card.status === 'waiting' && card.subtask) {
      children.push(para('○ ' + card.subtask.title + ' · waiting for ' + roleOf(view, (view.threads[card.waitingOn[0]] || {}).agentId || ''), 'is-muted'));
    }
    if (card.replies.length) {
      children.push(repliesBlock(view, card.replies, card.status === 'active'));
    }
    return children.concat(promptRow(card, ui, card.promptRef));
  }

  function draftCard(card, view, ui) {
    var e = card.event;
    var p = e.payload;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var summary = 'Draft v' + p.version + ' committed' + (p.note ? ', ' + p.note : '');
    var children = [header(card, agentCard(typeof e.actor === 'object' ? e.actor : HUMAN), summary, F.STAGE_LABEL[e.stage] || 'Assemble', t, open, ui)];
    if (open) {
      children = children.concat([eventLabel(t + ' · draft.committed'), para('Draft committed · v' + p.version + (p.note ? ' · ' + p.note : ''))]);
      if (card.replies && card.replies.length) { children.push(repliesBlock(view, card.replies, false)); }
      children = children.concat(promptRow(card, ui, e.prompt_ref));
    }
    return children;
  }

  function routeText(view, f, passed) {
    if (f.route_to === 'work' && f.agent_id) { return 'back to ' + roleOf(view, f.agent_id); }
    if (f.route_to === 'assemble') { return 'back to Writer'; }
    return passed ? 'note for Handoff' : 'note for Handoff';
  }

  function verdictSummary(e, version) {
    var p = e.payload;
    var counts = { blocker: 0, major: 0, minor: 0 };
    p.findings.forEach(function (f) { counts[f.severity] += 1; });
    if (p.verdict === 'pass') {
      var k = counts.minor;
      return 'Pass on v' + version + (k ? ', ' + k + ' minor ' + F.plural(k, 'note') + ' ' + (k === 1 ? 'remains' : 'remain') : '');
    }
    var parts = ['blocker', 'major', 'minor'].filter(function (s) { return counts[s]; }).map(function (s) { return counts[s] + ' ' + s; });
    var lastCount = counts[['minor', 'major', 'blocker'].filter(function (s) { return counts[s]; })[0]] || 0;
    return 'Fail on v' + version + (parts.length ? ': ' + parts.join(', ') + ' ' + F.plural(lastCount, 'finding') : '');
  }

  function verdictCard(card, view, ui) {
    var e = card.event;
    var p = e.payload;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var passed = p.verdict === 'pass';
    var left = el('div', { class: 'card-hd-left' }, [
      agentCard(e.actor),
      el('span', { class: 'verdict-pill', 'data-verdict': p.verdict, text: passed ? '✓ PASS' : '✕ FAIL' })
    ]);
    var children = [header(card, left, verdictSummary(e, card.draftVersion || 1), 'Review', t, open, ui)];
    if (open) {
      children.push(eventLabel(t + ' · review.verdict'));
      if (p.summary) { children.push(para(p.summary)); }
      children.push(el('div', { class: 'findings' }, p.findings.map(function (f) {
        return el('div', { class: 'finding', 'data-part': 'finding' }, [
          el('span', { class: 'sev', 'data-severity': f.severity, text: f.severity }),
          el('div', {}, [el('div', { class: 'finding-text', text: f.text }), el('div', { class: 'finding-evidence', text: 'Evidence: ' + f.evidence })]),
          el('span', { class: 'route-pill', text: routeText(view, f, passed) })
        ]);
      })));
      children = children.concat(promptRow(card, ui, e.prompt_ref));
    }
    return children;
  }

  function blockerCard(card, view, ui) {
    var e = card.event;
    var b = card.blocker;
    var open = isOpen(card, view, ui);
    var t = clock(view, e);
    var who = view.roster[b.agent_id] ? view.roster[b.agent_id].name : b.agent_id;
    var summary = card.answer
      ? (card.answer.payload.action === 'escalate' ? 'Blocker from ' + who + ' escalated' : 'Blocker from ' + who + ' answered')
      : 'Paused on a blocker from ' + who;
    var children = [header(card, agentCard(view.roster.orchestrator), summary, F.STAGE_LABEL[e.stage] || 'Work', t, open, ui)];
    if (!open) { return children; }
    children.push(eventLabel(t + ' · clarification.asked'));
    children.push(para(b.description));
    children.push(why(e.reason));
    if (card.answer) {
      var a = card.answer.payload;
      children.push(para(a.action === 'escalate' ? 'You escalated this blocker.' : 'You answered: ' + a.answer, 'is-muted'));
    } else if (!view.terminated) {
      var live = ui.mode === 'live';
      children.push(el('div', { class: 'blocker-actions', 'data-part': 'blocker-actions' }, [
        el('input', { class: 'text-input', type: 'text', placeholder: 'Your answer', 'data-blocker-input': b.blocker_id, disabled: !live || ui.submitting }),
        el('button', { class: 'btn-pill-dark', type: 'button', 'data-action': 'blocker-answer', 'data-blocker': b.blocker_id, disabled: !live || ui.submitting, text: 'Answer' }),
        el('button', { class: 'btn-outline', type: 'button', 'data-action': 'blocker-escalate', 'data-blocker': b.blocker_id, disabled: !live || ui.submitting, text: 'Escalate' })
      ]));
    }
    return children.concat(promptRow(card, ui, null));
  }

  function headlineFor(exit, retries) {
    if (exit === 'reviewer_pass') {
      return retries === 0 ? 'The Reviewer passed the proposal first time.'
        : 'The Reviewer passed the proposal after ' + (retries === 1 ? 'one rework' : retries + ' reworks') + '.';
    }
    return 'Review stopped with findings unresolved.';
  }

  var STOP_REASON_TEXT = {
    no_progress: 'no progress in the last review cycle',
    repeated_finding: 'a finding repeated from the previous cycle',
    max_cycles: 'the maximum number of review cycles was reached'
  };

  function terminationCard(card, view) {
    var h = card.handoff;
    var term = card.terminated;
    var exit, headline, reason, eyebrowMs, count, retries, summary;
    if (term) {
      summary = term.payload.summary;
      exit = term.payload.exit;
      headline = summary.headline;
      reason = h ? h.reason : term.reason;
      eyebrowMs = summary.elapsed_ms;
      count = summary.event_count;
      retries = summary.retries;
    } else {
      exit = h.payload.exit_determination;
      retries = card.retry;
      headline = headlineFor(exit, retries.count);
      reason = h.reason;
      eyebrowMs = F.tsMs(h.ts) - view.startMs;
      count = h.seq;
    }
    var main = [
      el('div', { class: 'term-eyebrow', text: (term ? 'Run ended · ' : 'Ready for approval · ') + F.fmtClock(eyebrowMs) }),
      el('div', { class: 'term-headline', text: headline }),
      el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Orchestrator reason:' }), ' ' + reason])
    ];
    if (summary && summary.missing && summary.missing.length) {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'What is missing:' })]));
      main.push(el('ul', { class: 'term-missing' }, summary.missing.map(function (m) {
        return el('li', {}, [m.item, m.note ? el('span', { class: 'term-missing-note', text: ' · ' + m.note }) : null]);
      })));
    }
    if (summary && summary.readiness_verdict && exit !== 'not_ready') {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Readiness verdict:' }), ' ' + summary.readiness_verdict.replace(/_/g, ' ')]));
    }
    if (exit === 'retry_exhausted' && summary && summary.stop_reason) {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Review stopped:' }), ' ' + (STOP_REASON_TEXT[summary.stop_reason] || summary.stop_reason)]));
    }
    if (summary && summary.unresolved_findings && summary.unresolved_findings.length) {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Notes carried to Handoff:' }), ' ' + summary.unresolved_findings.length]));
    }
    if (exit === 'cost_ceiling' && summary) {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Estimated spend:' }), ' ' + F.fmtUsd(summary.est_cost || 0) + ' against a ceiling of ' + F.fmtUsd(view.ceiling || 0)]));
    }
    if (summary && summary.human_decision) {
      main.push(el('div', { class: 'term-reason' }, [el('span', { class: 'term-reason-k', text: 'Your decision:' }), ' ' + summary.human_decision]));
    }
    return [
      el('div', { class: 'term-main' }, main),
      el('div', { class: 'term-side' }, [
        el('span', { class: 'exit-pill', text: 'exit: ' + exit }),
        el('span', { text: 'retries ' + retries.count + ' of ' + retries.budget + ' · ' + count + ' events' })
      ])
    ];
  }

  function buildCard(card, view, ui, ctx) {
    var attrs = { class: 'card', 'data-kind': card.kind, 'data-card': card.id };
    var children;
    switch (card.kind) {
      case 'orchestrator-note': children = noteCard(card, view, ui, ctx); break;
      case 'agent-message':
        if (card.role === 'intake') { attrs['data-live'] = String(!!card.live); }
        attrs['data-event-id'] = card.event.event_id;
        children = intakeCard(card, view, ui);
        break;
      case 'assumption': children = assumptionCard(card, view, ui); break;
      case 'question': children = questionCard(card, view, ui); break;
      case 'human-answer': children = answerCard(card, view, ui); break;
      case 'specialist-thread':
        attrs['data-agent'] = card.agentId;
        attrs['data-status'] = card.status;
        attrs['data-live'] = String(!!card.live);
        /* A provenance marker points at the specialist's completed output (spec 2.6). */
        if (card.completed) { attrs['data-event-id'] = card.completed.event_id; }
        children = threadCard(card, view, ui);
        break;
      case 'draft-committed': children = draftCard(card, view, ui); break;
      case 'verdict': attrs['data-verdict'] = card.event.payload.verdict; children = verdictCard(card, view, ui); break;
      case 'blocker': children = blockerCard(card, view, ui); break;
      case 'termination':
        var exit = card.terminated ? card.terminated.payload.exit : card.handoff.payload.exit_determination;
        attrs['data-exit'] = exit;
        attrs['data-tone'] = exit === 'reviewer_pass' ? 'pass' : 'stop';
        children = terminationCard(card, view);
        break;
      default: children = [];
    }
    if (card.kind !== 'termination') { attrs['data-action'] = 'toggle'; }
    return el('article', attrs, children);
  }

  /* Page parts */

  function renderFeed(view, ui, ctx) {
    var feed = document.getElementById('feed');
    var empty = document.getElementById('feed-empty');
    empty.hidden = view.hasRun;
    var existing = {};
    Array.prototype.forEach.call(feed.querySelectorAll('article.card'), function (node) { existing[node.getAttribute('data-card')] = node; });
    var appended = false;
    var previous = null;
    var keep = {};
    view.cards.forEach(function (card) {
      var fresh = buildCard(card, view, ui, ctx);
      var html = fresh.outerHTML;
      var node = existing[card.id];
      keep[card.id] = true;
      if (node) {
        if (node.__html !== html) {
          fresh.__html = html;
          node.replaceWith(fresh);
          node = fresh;
        }
      } else {
        fresh.__html = html;
        node = fresh;
        appended = true;
      }
      var expectedNext = previous ? previous.nextSibling : empty.nextSibling;
      if (node !== expectedNext) { feed.insertBefore(node, expectedNext); }
      previous = node;
    });
    Object.keys(existing).forEach(function (id) { if (!keep[id]) { existing[id].remove(); } });
    if (appended && ui.autoScroll) { feed.scrollTop = feed.scrollHeight; }
  }

  var GLYPH = { idle: '○', active: '●', complete: '✓', paused: '!', bypassed: '○' };

  function renderLoop(view, ui) {
    document.querySelectorAll('.node[data-stage]').forEach(function (node) {
      var state = view.nodes[node.getAttribute('data-stage')] || 'idle';
      if (node.getAttribute('data-state') !== state) {
        node.setAttribute('data-state', state);
        node.querySelector('.node-glyph').textContent = GLYPH[state];
      }
    });
    var badge = document.querySelector('.retry-badge');
    if (badge.textContent !== view.retryText) { badge.textContent = view.retryText; }
    /* Forward connectors fill once crossed and pulse once per transition, keyed to the event id so a
       replay fires them exactly as the live run did. A jump over several nodes pulses them in sequence. */
    var order = [];
    document.querySelectorAll('.fwd[data-link]').forEach(function (span) {
      var link = span.getAttribute('data-link');
      var eventId = view.forwardFired[link] || null;
      span.setAttribute('data-filled', String(!!eventId));
      if (eventId && ui.animatedArrows['fwd:' + link] !== eventId) {
        ui.animatedArrows['fwd:' + link] = eventId;
        var delay = order.filter(function (id) { return id === eventId; }).length * 150;
        order.push(eventId);
        span.classList.remove('is-firing');
        void span.getBoundingClientRect();
        if (ui.animate) { span.style.animationDelay = delay + 'ms'; span.classList.add('is-firing'); }
      }
      if (!eventId) { span.classList.remove('is-firing'); delete ui.animatedArrows['fwd:' + link]; }
    });
    var reason = document.getElementById('loop-reason');
    var stageName = view.currentStage ? F.STAGE_LABEL[view.currentStage] : (view.terminated ? 'Run ended' : '');
    var reasonText = view.stageReason || '';
    reason.hidden = !reasonText;
    var reasonHtml = stageName + ' · ' + reasonText;
    if (reason.__text !== reasonHtml) {
      reason.__text = reasonHtml;
      reason.textContent = '';
      reason.appendChild(el('span', { class: 'loop-reason-k', text: stageName }));
      reason.appendChild(document.createTextNode(' · ' + reasonText));
      reason.title = reasonText;
    }
    ['review-work', 'review-assemble', 'work-intake'].forEach(function (key) {
      var fired = !!view.fired[key];
      var path = document.querySelector('path[data-arrow="' + key + '"]');
      var label = document.querySelector('text[data-arrow="' + key + '"]');
      path.setAttribute('data-fired', String(fired));
      label.setAttribute('data-fired', String(fired));
      path.setAttribute('marker-end', fired ? 'url(#bk-fired)' : 'url(#bk-grey)');
      var eventId = view.firedEventIds[key];
      if (fired && eventId && ui.animatedArrows[key] !== eventId) {
        ui.animatedArrows[key] = eventId;
        path.classList.remove('is-firing');
        void path.getBoundingClientRect();
        if (ui.animate) { path.classList.add('is-firing'); }
      }
      if (!fired) { path.classList.remove('is-firing'); delete ui.animatedArrows[key]; }
    });
  }

  function renderBanner(view, ui) {
    var banner = document.getElementById('banner');
    if (!view.banner) { banner.hidden = true; ui.bannerAskId = null; return; }
    banner.hidden = false;
    var n = view.banner.questions.length;
    var intake = view.roster.intake ? view.roster.intake.name : 'Intake';
    document.getElementById('banner-text').textContent = intake + ' paused Intake with ' + n + ' blocking ' + F.plural(n, 'question') + '. Defaults are filled in; change what you need and resume.';
    var askId = view.banner.askEvent.event_id;
    var box = document.getElementById('banner-questions');
    if (ui.bannerAskId !== askId) {
      ui.bannerAskId = askId;
      box.innerHTML = '';
      view.banner.questions.forEach(function (q) {
        box.appendChild(el('div', { class: 'banner-q', 'data-part': 'banner-question' }, [
          el('div', { class: 'banner-q-text', text: q.question }),
          el('input', { class: 'text-input', type: 'text', value: q.proposed_default, 'data-question': q.question_id }),
          el('div', { class: 'banner-why' }, [el('span', { class: 'banner-why-k', text: 'Why it matters:' }), ' ' + q.why_it_matters])
        ]));
      });
    }
    var live = ui.mode === 'live';
    box.querySelectorAll('input').forEach(function (input) { input.readOnly = !live; });
    document.getElementById('banner-resume').disabled = !live || ui.submitting;
  }

  function meterFor(view, id) {
    return view.meters[id] || { tokens: 0, tokensIn: 0, tokensOut: 0, cost: 0, calls: 0, wallMs: 0, lastEvent: 'none' };
  }

  function renderMeters(view, ui, ctx) {
    var roster = view.hasRun ? view.roster : ctx.idleRoster || {};
    var box = document.getElementById('agent-meters');
    var html = '';
    var nodes = ROSTER_ORDER.filter(function (id) { return roster[id]; }).map(function (id) {
      var m = meterFor(view, id);
      return el('button', { class: 'meter', type: 'button', 'data-part': 'agent-meter', 'data-open': String(ui.meterOpen === id), 'data-action': 'meter', 'data-agent': id }, [
        el('div', { class: 'meter-left' }, [agentCard(roster[id], 'meter')]),
        el('div', { class: 'meter-nums' }, [el('div', { text: F.fmtTok(m.tokens) }), el('div', { class: 'meter-cost', text: F.fmtUsd(m.cost) })])
      ]);
    });
    nodes.forEach(function (n) { html += n.outerHTML; });
    if (box.__html !== html) { box.innerHTML = html; box.__html = html; }

    document.getElementById('elapsed').textContent = F.fmtClock(view.elapsedMs);
    document.getElementById('run-total').textContent = F.fmtUsd(view.totalCost);
    document.getElementById('ceiling-label').textContent = 'Ceiling $' + (ctx.costCeiling || 5).toFixed(2);
    document.getElementById('ceiling-fill').style.width = view.ceilingPct;
    document.getElementById('ceiling-pct').textContent = view.ceilingPct;

    var detail = document.getElementById('meter-detail');
    if (!ui.meterOpen || !roster[ui.meterOpen]) { detail.hidden = true; detail.__html = ''; return; }
    var md = meterFor(view, ui.meterOpen);
    var stats = [
      ['Calls', String(md.calls)],
      ['Tokens in / out', md.tokens ? F.fmtTok(md.tokensIn) + ' / ' + F.fmtTok(md.tokensOut) : '0 / 0'],
      ['Cost', F.fmtUsd(md.cost) + (md.cost === 0 && md.tokens ? ' (local)' : '')],
      ['Wall time', F.fmtWall(md.wallMs)],
      ['Last event', md.lastEvent]
    ];
    var dnodes = [agentCard(roster[ui.meterOpen])].concat(stats.map(function (s) {
      return el('div', { class: 'stat' }, [el('span', { class: 'stat-label', text: s[0] }), el('span', { class: 'stat-value', text: s[1] })]);
    }), [el('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Close', 'data-action': 'meter-close', text: '✕' })]);
    var dhtml = dnodes.map(function (n) { return n.outerHTML; }).join('');
    if (detail.__html !== dhtml) { detail.innerHTML = dhtml; detail.__html = dhtml; }
    detail.hidden = false;
  }

  function renderRaw(view, ui) {
    document.getElementById('raw-label').textContent = 'Raw turns · ' + view.eventCount + ' events';
    document.getElementById('raw-chev').textContent = ui.rawOpen ? '▾' : '▸';
    var pre = document.getElementById('raw-pre');
    pre.hidden = !ui.rawOpen;
    if (ui.rawOpen && pre.__count !== view.eventCount) {
      pre.textContent = view.raw.map(function (e) { return JSON.stringify(e); }).join('\n');
      pre.__count = view.eventCount;
    }
  }

  function runFileUrl(runId, path) {
    return '/api/runs/' + encodeURIComponent(runId) + '/files/' + path.split('/').map(encodeURIComponent).join('/');
  }

  /* The compiled pages of the latest artifact.compiled (S4). Images are replaced in place by index,
     so a new version swaps under the presenter's eyes without an empty frame and keeps the scroll. */
  function renderPages(view, ui) {
    var empty = document.getElementById('artifact-empty');
    var scroll = document.getElementById('pages-scroll');
    var list = document.getElementById('pages');
    var title = document.getElementById('artifact-title');
    var version = document.getElementById('artifact-version');
    var compiled = view.latestCompiled;
    if (!compiled) {
      scroll.hidden = true;
      empty.hidden = false;
      empty.textContent = view.latestDraft
        ? 'This recording predates compiled pages.'
        : 'Deliverable appears here after the first draft.';
      title.textContent = 'Deliverable';
      version.textContent = '';
      if (list.__key) { list.__key = null; list.textContent = ''; }
      return;
    }
    empty.hidden = true;
    scroll.hidden = false;
    title.textContent = 'Deliverable · pages';
    version.textContent = 'v' + compiled.version + ' · ' + compiled.pageImages.length + ' ' + F.plural(compiled.pageImages.length, 'page');
    var key = compiled.runId + '/' + compiled.eventId;
    if (list.__key === key) { return; }
    list.__key = key;
    var top = scroll.scrollTop;
    var figures = list.querySelectorAll('figure.page');
    compiled.pageImages.forEach(function (path, i) {
      var figure = figures[i];
      if (!figure) {
        figure = el('figure', { class: 'page', 'data-part': 'page', 'data-page': String(i + 1) }, [
          el('img', { class: 'page-img', loading: i < 2 ? 'eager' : 'lazy', alt: 'Page ' + (i + 1) }),
          el('figcaption', { class: 'page-num', text: 'Page ' + (i + 1) })
        ]);
        list.appendChild(figure);
      }
      var img = figure.querySelector('img');
      var url = runFileUrl(compiled.runId, path);
      if (img.getAttribute('src') !== url) { img.setAttribute('src', url); }
    });
    for (var j = compiled.pageImages.length; j < figures.length; j += 1) { figures[j].remove(); }
    scroll.scrollTop = top;
  }

  /* Provenance markers over the page images (spec 2.6, S4 decision 2a). markers.json beside the pages
     carries each marker's page and pixel position at 150 ppi; the overlay places it as a percentage
     of the image's natural size, so it stays put at any panel width. Hover is wired in demo.js. */
  function loadMarkers(compiled, ui) {
    var key = compiled.runId + '/' + compiled.eventId;
    var entry = ui.markers[key];
    if (entry) { return entry; }
    entry = ui.markers[key] = { status: 'loading', list: [] };
    var folder = compiled.pageImages[0].split('/').slice(0, -1).join('/');
    fetch(runFileUrl(compiled.runId, folder + '/markers.json'))
      .then(function (response) { if (!response.ok) { throw new Error(String(response.status)); } return response.json(); })
      .then(function (list) { entry.status = 'loaded'; entry.list = list; if (ui.schedule) { ui.schedule(); } })
      .catch(function () { entry.status = 'missing'; if (ui.schedule) { ui.schedule(); } });
    return entry;
  }

  function placeMarkers(figure, img, markers, tags) {
    var layer = figure.querySelector('.marker-layer');
    if (!layer) { layer = el('div', { class: 'marker-layer', 'data-part': 'marker-layer' }); figure.appendChild(layer); }
    var key = markers.length + ':' + img.naturalWidth + ':' + Object.keys(tags).length;
    if (layer.__key === key) { return; }
    layer.__key = key;
    layer.textContent = '';
    if (!img.naturalWidth || !img.naturalHeight) { layer.__key = null; return; }
    markers.forEach(function (m) {
      var source = tags[m.tag_id] || null;
      var attrs = {
        class: 'marker', type: 'button', 'data-part': 'marker', 'data-marker': String(m.n), 'data-tag': m.tag_id,
        title: source ? 'Source of this figure' : 'Unresolved source',
        style: 'left:' + (m.x / img.naturalWidth * 100).toFixed(3) + '%;top:' + (m.y / img.naturalHeight * 100).toFixed(3) + '%',
        text: String(m.n)
      };
      if (source) { attrs['data-source-event'] = source; } else { attrs['data-unresolved'] = 'true'; }
      layer.appendChild(el('button', attrs));
    });
  }

  function renderMarkers(view, ui) {
    var compiled = view.latestCompiled;
    if (!compiled || !compiled.pageImages.length) { return; }
    var entry = loadMarkers(compiled, ui);
    if (entry.status !== 'loaded') { return; }
    var tags = view.draftTags[compiled.version] || {};
    document.querySelectorAll('#pages figure.page').forEach(function (figure) {
      var pageNo = Number(figure.getAttribute('data-page'));
      var img = figure.querySelector('img');
      var mine = entry.list.filter(function (m) { return m.page === pageNo; });
      if (img.complete && img.naturalWidth) {
        placeMarkers(figure, img, mine, tags);
      } else if (!img.__markerHook) {
        img.__markerHook = true;
        img.addEventListener('load', function () { placeMarkers(figure, img, mine, tags); });
      }
    });
  }

  function renderArtifact(view, ui) {
    renderPages(view, ui);
    renderMarkers(view, ui);
    var actions = document.getElementById('handoff-actions');
    var term = view.cards.filter(function (c) { return c.kind === 'termination' && c.handoff; })[0];
    actions.hidden = !term;
    document.getElementById('btn-approve').disabled = !(view.handoffPending && ui.mode === 'live') || ui.submitting;
    document.getElementById('compare-chev').textContent = ui.compareOpen ? '▾' : '▸';
    document.getElementById('compare-body').hidden = !ui.compareOpen;
    document.getElementById('raw-btn').setAttribute('aria-expanded', String(ui.rawOpen));
  }

  function renderComposer(view, ui, ctx) {
    var busy = ui.mode === 'live' ? !view.terminated : ui.mode === 'replay' ? !view.terminated : false;
    var runBtn = document.getElementById('btn-run');
    runBtn.disabled = busy || !ctx.selectedDataset;
    var select = document.getElementById('dataset-select');
    select.classList.toggle('is-locked', busy);
    var ds = (ctx.datasets || []).filter(function (d) { return d.id === ctx.selectedDataset; })[0];
    document.getElementById('dataset-value').textContent = ds ? ds.label : 'Choose a dataset';
    var replayBtn = document.getElementById('btn-replay');
    var canReplay = ds && ds.replay_source;
    replayBtn.disabled = !canReplay;
    replayBtn.setAttribute('aria-disabled', String(busy));
    replayBtn.title = canReplay ? 'Replays the ' + (ds.replay_source === 'recording' ? 'most recent recording' : 'golden log') + ' for this dataset' : 'No recording or golden log for this dataset yet';
    replayBtn.setAttribute('aria-pressed', String(ui.mode === 'replay' && !view.terminated));
    /* Presenter controls: only for a run this page started and follows (data-model.md control states). */
    var following = ui.mode === 'live' && ui.following && !!view.hasRun && !view.terminated;
    var waiting = !!view.banner || !!view.blockerPending || view.handoffPending;
    var pauseBtn = document.getElementById('btn-pause');
    pauseBtn.disabled = !following || (waiting && !view.pausedByHuman);
    pauseBtn.textContent = view.pausedByHuman ? 'Resume' : 'Pause';
    pauseBtn.setAttribute('data-action', view.pausedByHuman ? 'control-resume' : 'control-pause');
    document.getElementById('btn-stop').disabled = !following;
    var dryLocked = busy || ui.mode === 'replay' || (ui.mode === 'live' && !ui.following && view.hasRun);
    document.getElementById('dry-intake').classList.toggle('is-disabled', dryLocked);
    ['dry-off', 'dry-on'].forEach(function (id) {
      var btn = document.getElementById(id);
      btn.disabled = dryLocked;
      btn.setAttribute('aria-pressed', String(id === 'dry-on' ? ui.dryIntake : !ui.dryIntake));
    });
    document.getElementById('speed-1').setAttribute('aria-pressed', String(ui.speed === 1));
    document.getElementById('speed-4').setAttribute('aria-pressed', String(ui.speed === 4));
  }

  function renderAll(view, ui, ctx) {
    renderLoop(view, ui);
    renderBanner(view, ui);
    renderComposer(view, ui, ctx);
    renderFeed(view, ui, ctx);
    renderArtifact(view, ui);
    renderMeters(view, ui, ctx);
    renderRaw(view, ui);
  }

  global.S1Render = { renderAll: renderAll, agentCard: agentCard };
})(window);
