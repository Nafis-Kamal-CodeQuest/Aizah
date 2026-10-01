/* =============================================================
   AIZAH FMCG - perf-debug.js
   Live FPS overlay. Loaded ONLY when ?perf=1 is in the URL.
   Nothing runs unless that query param is present.
   ============================================================= */
(function () {
  'use strict';
  if (!/[?&]perf=1/.test(location.search)) return;

  var HISTORY_S = 2;   // seconds of frame history to keep
  var UPDATE_HZ = 8;   // overlay update rate (Hz)

  var frames   = [];    // { ts, dt } ring buffer
  var overlay  = null;
  var rafId    = null;
  var lastTs   = performance.now();

  function tick(ts) {
    var dt = ts - lastTs;
    lastTs = ts;
    if (dt > 0 && dt < 5000) {
      frames.push({ ts: ts, dt: dt });
    }
    // Prune frames older than HISTORY_S
    var cutoff = ts - HISTORY_S * 1000;
    while (frames.length && frames[0].ts < cutoff) frames.shift();
    rafId = requestAnimationFrame(tick);
  }

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.id = 'perf-debug-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    Object.assign(overlay.style, {
      position:      'fixed',
      bottom:        '12px',
      right:         '12px',
      zIndex:        '999999',
      background:    'rgba(2, 6, 23, 0.88)',
      color:         '#e2e8f0',
      fontFamily:    'ui-monospace, monospace',
      fontSize:      '11px',
      lineHeight:    '1.5',
      padding:       '8px 12px',
      borderRadius:  '8px',
      border:        '1px solid rgba(6, 182, 212, 0.3)',
      minWidth:      '120px',
      pointerEvents: 'none',
      userSelect:    'none',
    });
    document.body.appendChild(overlay);
  }

  function updateOverlay() {
    if (!overlay || !frames.length) return;
    var n    = frames.length;
    var sum  = 0;
    var worst = 0;
    for (var i = 0; i < n; i++) {
      sum  += frames[i].dt;
      if (frames[i].dt > worst) worst = frames[i].dt;
    }
    var avgDt = sum / n;
    var fps   = Math.round(1000 / avgDt);
    var worstMs = Math.round(worst);
    var fpsColor = fps >= 55 ? '#34d399'   // green
                 : fps >= 40 ? '#fbbf24'   // amber
                             : '#f87171';  // red

    overlay.innerHTML =
      '<span style="color:' + fpsColor + ';font-weight:bold">' + fps + ' fps</span><br>' +
      '<span style="color:#94a3b8">worst ' + worstMs + ' ms</span><br>' +
      '<span style="color:#64748b">last ' + HISTORY_S + 's  n=' + n + '</span>';
  }

  function init() {
    buildOverlay();
    rafId = requestAnimationFrame(tick);
    setInterval(updateOverlay, 1000 / UPDATE_HZ);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
