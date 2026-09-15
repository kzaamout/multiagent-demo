/* Server-sent event client with resume by seq. Delivers each event once, in order. */
(function (global) {
  'use strict';

  function EventStream(url, options) {
    this.url = url;
    this.lastSeq = options.sinceSeq || 0;
    this.onEvent = options.onEvent;
    this.onClose = options.onClose || function () {};
    this.source = null;
    this.closed = false;
  }

  EventStream.prototype.open = function () {
    var self = this;
    if (self.closed) { return; }
    var sep = self.url.indexOf('?') === -1 ? '?' : '&';
    self.source = new EventSource(self.url + sep + 'since=' + self.lastSeq);
    self.source.onmessage = null;
    var handler = function (message) {
      var event;
      try { event = JSON.parse(message.data); } catch (error) { return; }
      if (typeof event.seq !== 'number' || event.seq <= self.lastSeq) { return; }
      self.lastSeq = event.seq;
      self.onEvent(event);
      if (event.type === 'run.terminated') { self.close(); }
    };
    [
      'run.started', 'stage.changed', 'intake.brief', 'intake.readiness', 'clarification.needed',
      'clarification.asked', 'clarification.answered', 'assumption.accepted', 'plan.created',
      'task.dispatched', 'task.progress', 'tool.called', 'task.completed', 'blocker.raised',
      'draft.committed', 'artifact.compiled', 'review.verdict', 'retry.incremented', 'handoff.ready',
      'human.approved', 'knowledge.appended', 'run.paused', 'run.resumed', 'model.changed',
      'meter.update', 'run.terminated'
    ].forEach(function (type) { self.source.addEventListener(type, handler); });
    self.source.onerror = function () {
      if (self.closed) { return; }
      /* EventSource reconnects on its own; reopen with since= so no event repeats. */
      self.source.close();
      setTimeout(function () { self.open(); }, 1000);
    };
  };

  EventStream.prototype.close = function () {
    if (this.closed) { return; }
    this.closed = true;
    if (this.source) { this.source.close(); }
    this.onClose();
  };

  global.S1EventStream = EventStream;
})(window);
