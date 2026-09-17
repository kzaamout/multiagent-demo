/* Formatting helpers shared by the pages. Formats match the design export. */
(function (global) {
  'use strict';

  var SEAT_COLORS = {
    orchestrator: '#17171c', intake: '#003c33', estimator: '#b45309', pricing: '#1863dc',
    writer: '#071829', reviewer: '#b30000', case: '#2f6b5e', market: '#4a4a8a', single: '#6b5e7a', human: '#75758a'
  };
  var STAGES = ['intake', 'plan', 'work', 'assemble', 'review', 'handoff'];
  var STAGE_LABEL = { intake: 'Intake', plan: 'Plan', work: 'Work', assemble: 'Assemble', review: 'Review', handoff: 'Handoff' };
  var WORKFLOW_LABEL = { electrical_rfp: 'Electrical RFP', appraisal: 'Appraisal' };
  var NUMBER_WORDS = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
  var ACRONYMS = { led: 'LED', bom: 'BOM', mdp: 'MDP', rfp: 'RFP', lp: 'LP' };

  function pad2(n) { return String(n).padStart(2, '0'); }

  var F = {
    SEAT_COLORS: SEAT_COLORS,
    STAGES: STAGES,
    STAGE_LABEL: STAGE_LABEL,
    WORKFLOW_LABEL: WORKFLOW_LABEL,
    fmtTok: function (n) { return n === 0 ? '0 tok' : (n / 1000).toFixed(1) + 'k tok'; },
    fmtUsd: function (n) { return '$' + n.toFixed(2); },
    fmtClock: function (ms) {
      var s = Math.max(0, Math.floor(ms / 1000));
      return pad2(Math.floor(s / 60)) + ':' + pad2(s % 60);
    },
    fmtWall: function (ms) {
      var s = Math.round(ms / 1000);
      return Math.floor(s / 60) + ':' + pad2(s % 60);
    },
    fmtSeconds: function (ms) { return ms >= 1000 ? (ms / 1000).toFixed(1) + ' s' : ms + ' ms'; },
    tsMs: function (ts) { return Date.parse(ts); },
    words: function (n) { return n >= 0 && n < NUMBER_WORDS.length ? NUMBER_WORDS[n] : String(n); },
    plural: function (n, one, many) { return n === 1 ? one : (many || one + 's'); },
    /* "q_led_retrofit_alternate" becomes "LED retrofit alternate" (or lower case when asked). */
    labelFromId: function (id, lower) {
      var words = String(id).replace(/^[a-z]_/, '').split('_');
      return words.map(function (w, i) {
        if (ACRONYMS[w]) { return ACRONYMS[w]; }
        if (i === 0 && !lower) { return w.charAt(0).toUpperCase() + w.slice(1); }
        return w;
      }).join(' ');
    },
    initials: function (name) { return String(name || '?').charAt(0).toUpperCase(); },
    seatColor: function (agentId) { return SEAT_COLORS[agentId] || SEAT_COLORS.human; },
    el: function (tag, attrs, children) {
      var node = document.createElement(tag);
      if (attrs) {
        Object.keys(attrs).forEach(function (key) {
          var value = attrs[key];
          if (value === null || value === undefined || value === false) { return; }
          if (key === 'text') { node.textContent = value; }
          else if (key === 'class') { node.className = value; }
          else if (key.indexOf('on') === 0 && typeof value === 'function') { node.addEventListener(key.slice(2), value); }
          else if (value === true) { node.setAttribute(key, ''); }
          else { node.setAttribute(key, String(value)); }
        });
      }
      (children || []).forEach(function (child) {
        if (child === null || child === undefined || child === false) { return; }
        node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
      });
      return node;
    }
  };

  global.S1Format = F;
})(window);
