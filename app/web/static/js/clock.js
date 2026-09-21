/* The Elapsed clock's arithmetic (constitution II, 1.3.0: the one display-only clock).
   The reducer gives the run's working time at its latest event; this adds the time since that
   event while the run works. Pure: no timer, no DOM, no state. demo.js holds the anchor and the
   interval that calls it. */
(function (global) {
  'use strict';

  /* clock:  view.clock from the reducer { workMs, lastTsMs, running, ended, workAtHandoffMs }.
     anchor: null for a fixed view; live { kind: 'live', runNowMs, pace, receivedAt } from the
             server's reading of the run's own clock; replay { kind: 'replay', arrivedAt, speed }
             from the moment the latest event arrived.
     nowMs:  performance.now() on the same time base as receivedAt and arrivedAt. */
  function valueAt(clock, anchor, nowMs) {
    if (!clock) { return 0; }
    if (!anchor || !clock.running) { return clock.workMs; }
    if (anchor.kind === 'live') {
      var runNow = anchor.runNowMs + (nowMs - anchor.receivedAt) * anchor.pace;
      return clock.workMs + Math.max(0, runNow - clock.lastTsMs);
    }
    if (anchor.kind === 'replay') {
      return clock.workMs + Math.max(0, (nowMs - anchor.arrivedAt) * anchor.speed);
    }
    return clock.workMs;
  }

  global.S1Clock = { valueAt: valueAt };
})(window);
