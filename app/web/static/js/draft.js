/* Draft text view for the artifact panel (S2 interim until compiled pages arrive in S4).
   A small, safe markdown renderer: text is escaped first, then headings, lists, tables,
   emphasis, and provenance tags ({{value|src:id}}) are formatted. */
(function (global) {
  'use strict';

  function escapeHtml(text) {
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function inline(text) {
    var html = escapeHtml(text);
    html = html.replace(/\{\{\s*([^|{}]+?)\s*\|\s*src:\s*([A-Za-z0-9_.:-]+)\s*\}\}/g, function (_, value, source) {
      return '<span class="prov" data-source="' + source + '">' + value + '</span>';
    });
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(^|[^*])_([^_]+)_/g, '$1<em>$2</em>');
    return html;
  }

  function renderMarkdown(markdown) {
    var lines = String(markdown).replace(/\r\n/g, '\n').split('\n');
    var out = [];
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];
      if (!line.trim()) { i += 1; continue; }
      var heading = /^(#{1,3})\s+(.*)$/.exec(line);
      if (heading) {
        var level = heading[1].length;
        out.push('<h' + level + '>' + inline(heading[2]) + '</h' + level + '>');
        i += 1;
        continue;
      }
      if (/^\s*[-*]\s+/.test(line)) {
        var items = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
          items.push('<li>' + inline(lines[i].replace(/^\s*[-*]\s+/, '')) + '</li>');
          i += 1;
        }
        out.push('<ul>' + items.join('') + '</ul>');
        continue;
      }
      if (/^\s*\|/.test(line)) {
        var rows = [];
        while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(lines[i]); i += 1; }
        var cells = function (row) { return row.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); }); };
        var body = rows.filter(function (r) { return !/^\s*\|?\s*:?-{3,}/.test(r); });
        var head = body.shift();
        var table = '<table><thead><tr>' + cells(head).map(function (c) { return '<th>' + inline(c) + '</th>'; }).join('') + '</tr></thead><tbody>';
        table += body.map(function (r) { return '<tr>' + cells(r).map(function (c) { return '<td>' + inline(c) + '</td>'; }).join('') + '</tr>'; }).join('');
        out.push(table + '</tbody></table>');
        continue;
      }
      var para = [];
      while (i < lines.length && lines[i].trim() && !/^(#{1,3})\s+/.test(lines[i]) && !/^\s*[-*|]\s*/.test(lines[i])) {
        para.push(lines[i].trim());
        i += 1;
      }
      if (!para.length) { para.push(line.trim()); i += 1; }
      out.push('<p>' + inline(para.join(' ')) + '</p>');
    }
    return out.join('\n');
  }

  global.S1Draft = { renderMarkdown: renderMarkdown, escapeHtml: escapeHtml };
})(window);
