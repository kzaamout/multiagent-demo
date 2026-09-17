/* Chat with an agent (spec 2.7). Opens from an agent card when the run is paused, finished, or replayed.
   The conversation lives in this panel only: it is posted to an out-of-band endpoint, never becomes an
   event, and is dropped when the panel closes. Markup follows the export's chat panel (chatOpen state). */
(function () {
  'use strict';
  var F = window.S1Format;
  var el = F.el;
  var chat = { open: false, agent: null, runId: null, messages: [], busy: false, tokens: 0, cost: 0, error: '' };

  function state() { return window.__s1 || {}; }

  function available() {
    var s = state();
    var view = s.view, ui = s.ui;
    if (!view || !ui || !view.hasRun) { return false; }
    if (ui.mode === 'replay') { return true; }
    return !!(view.terminated || view.pausedByHuman || view.banner || view.blockerPending || view.handoffPending);
  }

  function agentFor(agentId) {
    var view = state().view;
    return view && view.roster ? view.roster[agentId] : null;
  }

  function post(path, body) {
    return fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) { throw new Error(data.error || response.statusText); }
          return data;
        });
      });
  }

  function render() {
    var panel = document.getElementById('chat-panel');
    panel.hidden = !chat.open;
    if (!chat.open) { return; }
    var agent = agentFor(chat.agent);
    var card = document.getElementById('chat-card');
    card.innerHTML = '';
    if (agent) { card.appendChild(window.S1Render.agentCard(agent)); }
    var box = document.getElementById('chat-messages');
    box.innerHTML = '';
    chat.messages.forEach(function (m) {
      box.appendChild(el('div', { class: 'chat-msg ' + (m.role === 'user' ? 'chat-msg-user' : 'chat-msg-agent'), text: m.text }));
    });
    if (chat.busy) { box.appendChild(el('div', { class: 'chat-msg-note', text: 'Thinking.' })); }
    if (chat.error) { box.appendChild(el('div', { class: 'chat-msg-note', text: chat.error })); }
    box.scrollTop = box.scrollHeight;
    var input = document.getElementById('chat-text');
    input.placeholder = agent ? 'Ask ' + agent.name + ' about this run' : 'Ask about this run';
    input.disabled = chat.busy;
    document.getElementById('chat-send').disabled = chat.busy;
    /* The conversation's own tokens and cost ride on the note line once there is a reply; the meters never move. */
    document.getElementById('chat-note').textContent = 'Read-only with respect to the run. Cleared when this run closes.' + (chat.tokens ? ' This conversation: ' + F.fmtTok(chat.tokens) + ' · ' + F.fmtUsd(chat.cost) + '.' : '');
  }

  function open(agentId) {
    var view = state().view;
    chat.open = true;
    chat.agent = agentId;
    chat.runId = view ? view.runId : null;
    chat.messages = [];
    chat.tokens = 0;
    chat.cost = 0;
    chat.error = '';
    render();
    document.getElementById('chat-text').focus();
  }

  function close() {
    chat.open = false;
    chat.messages = [];
    chat.tokens = 0;
    chat.cost = 0;
    chat.error = '';
    render();
  }

  function send(text) {
    if (chat.busy || !text.trim() || !chat.runId) { return; }
    chat.messages.push({ role: 'user', text: text.trim() });
    chat.busy = true;
    chat.error = '';
    render();
    post('/api/chat', { run_id: chat.runId, agent_id: chat.agent, messages: chat.messages }).then(function (data) {
      chat.messages.push({ role: 'assistant', text: data.text });
      chat.tokens += (data.tokens_in || 0) + (data.tokens_out || 0);
      chat.cost += data.est_cost || 0;
      chat.busy = false;
      render();
    }).catch(function (error) {
      chat.error = error && error.message ? error.message : String(error);
      chat.busy = false;
      render();
    });
  }

  document.addEventListener('click', function (e) {
    if (e.target.closest('#chat-close')) { close(); return; }
    var card = e.target.closest('[data-part="agent-card"][data-agent]');
    /* Meter cards open the detail row (S1); Settings rows swap models; neither opens a chat. */
    if (!card || e.target.closest('#chat-panel') || e.target.closest('#seat-rows') || card.closest('.meter, #meter-detail')) { return; }
    var agentId = card.getAttribute('data-agent');
    if (agentId === 'human' || !agentFor(agentId)) { return; }
    if (!available()) {
      window.alertless(new Error('Chat is available when the run is paused or finished.'));
      return;
    }
    e.stopPropagation();
    open(agentId);
  }, true);

  document.getElementById('chat-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var input = document.getElementById('chat-text');
    var text = input.value;
    input.value = '';
    send(text);
  });

  window.__s1chat = {
    state: chat,
    open: open,
    close: close,
    /* Used only by the screenshot capture to show a conversation without a model call. */
    seed: function (agentId, messages) { open(agentId); chat.messages = messages.slice(); render(); }
  };
})();
