/**
 * ZKR Analiz Pro — Table Sort & Enhancement
 * Auto-initializes .pro-table with sortable columns.
 * Usage: Add data-sortable to <th> elements.
 */
const ProTable = (function() {
  'use strict';

  function init(scope) {
    const root = scope || document;
    root.querySelectorAll('.pro-table').forEach(function(table) {
      if (table._proTable) return;
      table._proTable = true;

      table.querySelectorAll('th[data-sortable]').forEach(function(th) {
        th.style.cursor = 'pointer';
        th.classList.add('sortable');

        // Add sort arrow
        if (!th.querySelector('.sort-arrow')) {
          var arrow = document.createElement('span');
          arrow.className = 'sort-arrow';
          arrow.textContent = '↕';
          th.appendChild(arrow);
        }

        th.addEventListener('click', function() {
          sortByColumn(table, th);
        });
      });
    });
  }

  function sortByColumn(table, th) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const headers = Array.from(th.parentElement.children);
    const colIndex = headers.indexOf(th);
    const sortType = th.getAttribute('data-sort-type') || 'auto';

    // Determine direction
    let dir = 'asc';
    if (th.classList.contains('sorted') && th.getAttribute('data-sort-dir') === 'asc') {
      dir = 'desc';
    }

    // Clear other sorts
    headers.forEach(function(h) {
      h.classList.remove('sorted');
      h.removeAttribute('data-sort-dir');
      var a = h.querySelector('.sort-arrow');
      if (a) a.textContent = '↕';
    });

    th.classList.add('sorted');
    th.setAttribute('data-sort-dir', dir);
    var arrow = th.querySelector('.sort-arrow');
    if (arrow) arrow.textContent = dir === 'asc' ? '↑' : '↓';

    // Sort rows
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
      const cellA = a.children[colIndex];
      const cellB = b.children[colIndex];
      if (!cellA || !cellB) return 0;

      let valA = (cellA.getAttribute('data-sort-value') || cellA.textContent).trim();
      let valB = (cellB.getAttribute('data-sort-value') || cellB.textContent).trim();

      // Auto-detect numbers
      const numA = parseFloat(valA.replace(/[,%$₺]/g, ''));
      const numB = parseFloat(valB.replace(/[,%$₺]/g, ''));

      let result;
      if (sortType === 'number' || (!isNaN(numA) && !isNaN(numB) && sortType === 'auto')) {
        result = numA - numB;
      } else {
        result = valA.localeCompare(valB, 'tr');
      }

      return dir === 'asc' ? result : -result;
    });

    // Re-append rows
    var fragment = document.createDocumentFragment();
    rows.forEach(function(row) { fragment.appendChild(row); });
    tbody.appendChild(fragment);

    // Fire event
    table.dispatchEvent(new CustomEvent('table-sort', {
      detail: { column: colIndex, direction: dir },
      bubbles: true
    }));
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); });
  } else {
    init();
  }

  return { init: init, sortByColumn: sortByColumn };
})();

window.ProTable = ProTable;
