  const CHART_OPTS = (h) => ({
    layout: { background: { color: '#161b22' }, textColor: '#8b949e' },
    grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
    timeScale: { borderColor: '#21262d', timeVisible: true, rightOffset: 30 },
    rightPriceScale: { borderColor: '#21262d' },
    width: 0, height: h,
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });

  function makeChart(elId, h) {
    const el = document.getElementById(elId);
    const c = LightweightCharts.createChart(el, { ...CHART_OPTS(h), width: el.clientWidth });
    new ResizeObserver(() => c.applyOptions({ width: el.clientWidth })).observe(el);
    return c;
  }

  const PRICE_H = () => {
    if (window.innerWidth >= 768) return Math.max(400, window.innerHeight - 220);
    // Móvil: mide el espacio real desde el chart-wrap hasta el borde de pantalla
    const wrap = document.getElementById('chart-price');
    if (wrap) {
      const top = wrap.getBoundingClientRect().top;
      return Math.max(200, window.innerHeight - top - 78);
    }
    return window.innerHeight - 185;
  };
  const priceChart = makeChart('chart-price', PRICE_H());
  window.addEventListener('resize', () => {
    priceChart.applyOptions({ height: PRICE_H(), width: document.getElementById('chart-price').clientWidth });
  });
  const candleSeries  = priceChart.addCandlestickSeries({ upColor:'#3fb950', downColor:'#da3633', borderUpColor:'#3fb950', borderDownColor:'#da3633', wickUpColor:'#3fb950', wickDownColor:'#da3633' });
  const bbUpperSeries = priceChart.addLineSeries({ color:'#58a6ff', lineWidth:1, priceLineVisible:false, lastValueVisible:false });
  const bbMidSeries   = priceChart.addLineSeries({ color:'#58a6ff55', lineWidth:1, lineStyle:1, priceLineVisible:false, lastValueVisible:false });
  const bbLowerSeries = priceChart.addLineSeries({ color:'#58a6ff', lineWidth:1, priceLineVisible:false, lastValueVisible:false });
  const emaFastSeries  = priceChart.addLineSeries({ color:'#f0883e', lineWidth:1.5, priceLineVisible:false, lastValueVisible:true });
  const emaSlowSeries  = priceChart.addLineSeries({ color:'#bc8cff', lineWidth:1.5, priceLineVisible:false, lastValueVisible:true });
  const volumeSeries   = priceChart.addHistogramSeries({
    priceScaleId: 'vol', priceLineVisible:false, lastValueVisible:false,
  });
  priceChart.priceScale('vol').applyOptions({
    scaleMargins: { top: 0.85, bottom: 0.0 }, visible: false, borderVisible: false,
  });

  // ---- Sub-pane overlay series (visibles: false por defecto) ----
  const overlayRsiSeries = priceChart.addLineSeries({ priceScaleId:'ov-rsi', color:'#f0883e', lineWidth:1.5, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayRsiOB     = priceChart.addLineSeries({ priceScaleId:'ov-rsi', color:'#da3633cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayRsiOS     = priceChart.addLineSeries({ priceScaleId:'ov-rsi', color:'#3fb950cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:false, visible:false });

  const overlayMacdLine   = priceChart.addLineSeries({ priceScaleId:'ov-macd', color:'#58a6ff', lineWidth:1.5, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayMacdSignal = priceChart.addLineSeries({ priceScaleId:'ov-macd', color:'#f0883e', lineWidth:1, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayMacdHist   = priceChart.addHistogramSeries({ priceScaleId:'ov-macd', priceLineVisible:false, lastValueVisible:false, visible:false });

  const overlayStochK  = priceChart.addLineSeries({ priceScaleId:'ov-stoch', color:'#3fb950', lineWidth:1.5, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayStochD  = priceChart.addLineSeries({ priceScaleId:'ov-stoch', color:'#f0883e', lineWidth:1, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayStoch80 = priceChart.addLineSeries({ priceScaleId:'ov-stoch', color:'#da3633cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:false, visible:false });
  const overlayStoch20 = priceChart.addLineSeries({ priceScaleId:'ov-stoch', color:'#3fb950cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:false, visible:false });

  const rsiChart    = makeChart('chart-rsi', 160);
  const rsiSeries   = rsiChart.addLineSeries({ color:'#f0883e', lineWidth:2, priceLineVisible:false });
  const rsiMaSeries = rsiChart.addLineSeries({ color:'#bc8cff', lineWidth:1.5, priceLineVisible:false, lastValueVisible:true });
  const rsiLineOB   = rsiChart.addLineSeries({ color:'#da3633cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:true });
  const rsiLineOS   = rsiChart.addLineSeries({ color:'#3fb950cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:true });

  const macdChart        = makeChart('chart-macd', 160);
  const macdLineSeries   = macdChart.addLineSeries({ color:'#58a6ff', lineWidth:2, priceLineVisible:false });
  const macdSignalSeries = macdChart.addLineSeries({ color:'#f0883e', lineWidth:1.5, priceLineVisible:false });
  const macdHistSeries   = macdChart.addHistogramSeries({ priceLineVisible:false, lastValueVisible:false });

  const stochChart   = makeChart('chart-stoch', 140);
  const stochKSeries = stochChart.addLineSeries({ color:'#3fb950', lineWidth:2, priceLineVisible:false, lastValueVisible:true });
  const stochDSeries = stochChart.addLineSeries({ color:'#f0883e', lineWidth:1.5, priceLineVisible:false, lastValueVisible:true });
  const stochLine80  = stochChart.addLineSeries({ color:'#da3633cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:true });
  const stochLine20  = stochChart.addLineSeries({ color:'#3fb950cc', lineWidth:1.5, lineStyle:2, priceLineVisible:false, lastValueVisible:true });

  function syncCharts(master, ...slaves) {
    master.timeScale().subscribeVisibleLogicalRangeChange(r => { if(r) slaves.forEach(s => s.timeScale().setVisibleLogicalRange(r)); });
    slaves.forEach(slave => {
      slave.timeScale().subscribeVisibleLogicalRangeChange(r => {
        if(r) { master.timeScale().setVisibleLogicalRange(r); slaves.filter(s=>s!==slave).forEach(s=>s.timeScale().setVisibleLogicalRange(r)); }
      });
    });
  }
  syncCharts(priceChart, rsiChart, macdChart, stochChart);

  // ---- Crosshair sync (líneas verticales sincronizadas) ----
  // Almacenamos los datos para buscar valores por tiempo
  let _rsiData = [], _macdData = [], _ohlcvData = [], _stochData = [];

  function findByTime(arr, time) {
    return arr.find(d => d.time === time) || null;
  }

  function setupCrosshairSync() {
    const charts = [
      { chart: priceChart,  series: candleSeries,    getData: t => { const d = findByTime(_ohlcvData, t); return d ? d.close : null; } },
      { chart: rsiChart,    series: rsiSeries,        getData: t => { const d = findByTime(_rsiData, t);  return d ? d.value  : null; } },
      { chart: macdChart,   series: macdLineSeries,   getData: t => { const d = findByTime(_macdData, t); return d ? d.macd   : null; } },
      { chart: stochChart,  series: stochKSeries,     getData: t => { const d = findByTime(_stochData, t); return d ? d.k     : null; } },
    ];

    charts.forEach(({ chart, series, getData }, idx) => {
      chart.subscribeCrosshairMove(param => {
        const time = param.time;
        charts.forEach(({ chart: other, series: otherSeries, getData: otherGet }, jdx) => {
          if (jdx === idx) return;
          if (!time || !param.point) {
            other.clearCrosshairPosition();
            return;
          }
          const val = otherGet(time);
          if (val !== null) other.setCrosshairPosition(val, time, otherSeries);
        });
      });
    });
  }

  setupCrosshairSync();

  const EMOJIS = { RSI:'📉', MACD:'📈', 'Bollinger Bands':'🔵' };

  async function loadStatus() {
    const res = await fetch(`/api/status?interval=${currentInterval}`);
    const data = await res.json();
    const cfg = data.config;

    document.getElementById('price-badge').textContent = '$' + data.price.toLocaleString();
    document.getElementById('last-update').textContent = 'Actualizado: ' + new Date().toLocaleTimeString('es-PE');

    document.getElementById('price-title').textContent = 'BTC-USD';
    document.getElementById('rsi-title').textContent =
      `RSI (${cfg.rsi_period}) — sobreventa <${cfg.rsi_oversold} · sobrecompra >${cfg.rsi_overbought}`;
    document.getElementById('macd-title').textContent =
      `MACD (${cfg.macd_fast}, ${cfg.macd_slow}, ${cfg.macd_signal})`;

    // Guardar datos para crosshair lookup
    _ohlcvData  = data.ohlcv;
    _rsiData    = data.rsi;
    _macdData   = data.macd;
    _stochData  = data.stoch;

    candleSeries.setData(data.ohlcv);
    bbUpperSeries.setData(data.bb_upper);
    bbMidSeries.setData(data.bb_mid);
    bbLowerSeries.setData(data.bb_lower);
    emaFastSeries.setData(data.ema_fast);
    emaSlowSeries.setData(data.ema_slow);
    volumeSeries.setData(data.volume);
    if (_initialLoad) {
      const now  = Math.floor(Date.now() / 1000);
      const ivr  = IV_RANGE[currentInterval] || IV_RANGE['1d'];
      const from = now - ivr.histDays * 24 * 3600;
      const to   = now + ivr.padDays  * 24 * 3600;
      const margin = Math.round(ivr.histDays * 0.2);
      priceChart.timeScale().setVisibleRange({
        from: from - margin * 24 * 3600,
        to:   to   + margin * 24 * 3600,
      });
      priceChart.priceScale('right').applyOptions({
        autoScale: true,
        scaleMargins: { top: 0.2, bottom: 0.2 },
      });
      _initialLoad = false;
    }

    rsiSeries.setData(data.rsi);
    rsiMaSeries.setData(data.rsi_ma);
    const rsiTimes = data.rsi.map(d => d.time);
    if (rsiTimes.length) {
      rsiLineOB.setData(rsiTimes.map(t => ({ time:t, value: data.rsi_overbought })));
      rsiLineOS.setData(rsiTimes.map(t => ({ time:t, value: data.rsi_oversold  })));
    }

    macdLineSeries.setData(data.macd.map(d => ({ time:d.time, value:d.macd })));
    macdSignalSeries.setData(data.macd.map(d => ({ time:d.time, value:d.signal })));
    macdHistSeries.setData(data.macd.map(d => ({ time:d.time, value:d.histogram, color: d.histogram>=0?'#3fb95088':'#da363388' })));

    stochKSeries.setData(data.stoch.map(d => ({ time:d.time, value:d.k })));
    stochDSeries.setData(data.stoch.map(d => ({ time:d.time, value:d.d })));
    const stochTimes = data.stoch.map(d => d.time);
    if (stochTimes.length) {
      stochLine80.setData(stochTimes.map(t => ({ time:t, value:80 })));
      stochLine20.setData(stochTimes.map(t => ({ time:t, value:20 })));
    }

    // ---- Poblar series overlay del chart de precio ----
    overlayRsiSeries.setData(data.rsi);
    const rsiTimesOv = data.rsi.map(d => d.time);
    if (rsiTimesOv.length) {
      overlayRsiOB.setData(rsiTimesOv.map(t => ({ time:t, value: data.rsi_overbought })));
      overlayRsiOS.setData(rsiTimesOv.map(t => ({ time:t, value: data.rsi_oversold  })));
    }
    overlayMacdLine.setData(data.macd.map(d => ({ time:d.time, value:d.macd })));
    overlayMacdSignal.setData(data.macd.map(d => ({ time:d.time, value:d.signal })));
    overlayMacdHist.setData(data.macd.map(d => ({ time:d.time, value:d.histogram, color: d.histogram>=0?'#3fb95088':'#da363388' })));
    overlayStochK.setData(data.stoch.map(d => ({ time:d.time, value:d.k })));
    overlayStochD.setData(data.stoch.map(d => ({ time:d.time, value:d.d })));
    const stochTimesOv = data.stoch.map(d => d.time);
    if (stochTimesOv.length) {
      overlayStoch80.setData(stochTimesOv.map(t => ({ time:t, value:80 })));
      overlayStoch20.setData(stochTimesOv.map(t => ({ time:t, value:20 })));
    }

    // Confluencia
    const sc = data.score;
    const threshold = data.config.confluence_threshold;
    document.getElementById('bull-score').textContent = `${sc.bull_score}/${sc.max_score}`;
    document.getElementById('bear-score').textContent = `${sc.bear_score}/${sc.max_score}`;
    document.getElementById('bull-bar').style.width = `${sc.bull_score / sc.max_score * 100}%`;
    document.getElementById('bear-bar').style.width = `${sc.bear_score / sc.max_score * 100}%`;
    document.getElementById('bull-tags').innerHTML = sc.bull_signals.map(s =>
      `<span class="conf-tag bull">+${s.points} ${s.name}</span>`).join('');
    document.getElementById('bear-tags').innerHTML = sc.bear_signals.map(s =>
      `<span class="conf-tag bear">+${s.points} ${s.name}</span>`).join('');
    const alertEl = document.getElementById('conf-alert');
    if (sc.bull_score >= threshold && sc.bull_score >= sc.bear_score) {
      alertEl.className = 'conf-alert bull';
      alertEl.textContent = `🟢 Alta confianza ALCISTA — Score ${sc.bull_score}/${sc.max_score}`;
    } else if (sc.bear_score >= threshold) {
      alertEl.className = 'conf-alert bear';
      alertEl.textContent = `🔴 Alta confianza BAJISTA — Score ${sc.bear_score}/${sc.max_score}`;
    } else {
      alertEl.className = 'conf-alert none';
      alertEl.textContent = `Sin confluencia suficiente (umbral: ${threshold} pts)`;
    }

    const panel = document.getElementById('signals-panel');
    panel.innerHTML = data.signals.map(s => {
      const cls = s.triggered ? 'green' : 'red';
      const label = s.triggered ? 'ALCISTA' : 'BAJISTA';
      return `<div class="signal-card ${cls}">
        <span class="signal-dot"></span>
        <div class="signal-info">
          <div class="signal-name">${EMOJIS[s.name]||'✨'} ${s.name}</div>
          <div class="signal-detail" title="${s.detail}">${s.detail}</div>
        </div>
        <span class="signal-label">${label}</span>
      </div>`;
    }).join('');
  }

  async function loadHistory() {
    const res = await fetch('/api/history');
    const items = await res.json();
    const body = document.getElementById('history-body');
    if (!items.length) { body.innerHTML = '<p style="color:#484f58;font-size:.8rem;text-align:center;padding:18px">Sin alertas registradas aún.</p>'; return; }
    const rows = items.map(item => {
      const dt = new Date(item.timestamp);
      return `<tr><td>${dt.toLocaleDateString('es-PE')} ${dt.toLocaleTimeString('es-PE')}</td><td><strong>${item.symbol}</strong></td><td><span class="badge">${item.indicator}</span></td><td>${item.detail}</td></tr>`;
    }).join('');
    body.innerHTML = `<table id="history-table"><thead><tr><th>Fecha/Hora</th><th>Símbolo</th><th>Indicador</th><th>Detalle</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  async function loadAll() { await Promise.all([loadStatus(), loadHistory()]); }

  // ---- Sub-pane margin engine ----
  const CANDLE_MIN_H      = 300;  // px mínimos para las velas
  const OVERLAY_PANE_PX   = 120;  // px fijos por cada sub-pane de indicador
  const OVERLAY_GAP_PX    = 8;
  const BASE_CHART_H      = () => PRICE_H();

  function recomputeOverlayMargins() {
    const active   = ['rsi', 'macd', 'stoch'].filter(k => overlayState[k]);
    const count    = active.length;
    const isMobile = window.innerWidth < 768;

    // Móvil: altura fija (pantalla completa), overlays dentro del mismo espacio
    // Escritorio: el chart crece para acomodar los overlays
    const totalH = isMobile
      ? PRICE_H()
      : count > 0
        ? CANDLE_MIN_H + count * OVERLAY_PANE_PX + count * OVERLAY_GAP_PX
        : BASE_CHART_H();

    const el = document.getElementById('chart-price');
    priceChart.applyOptions({ height: totalH, width: el.clientWidth });

    // En móvil cada overlay ocupa 18% del alto; en escritorio px fijos
    const paneFrac   = isMobile ? 0.18 : OVERLAY_PANE_PX / totalH;
    const gapFrac    = isMobile ? 0.02 : OVERLAY_GAP_PX  / totalH;
    const candleFrac = isMobile
      ? Math.max(0.3, 1 - count * (paneFrac + gapFrac))
      : CANDLE_MIN_H / totalH;
    const SLOT = paneFrac + gapFrac;

    priceChart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.02, bottom: count > 0 ? 1 - candleFrac + 0.02 : 0.02 },
    });

    active.forEach((key, i) => {
      const ri     = count - 1 - i;
      const bottom = ri * SLOT + gapFrac;
      const top    = 1.0 - (ri + 1) * paneFrac - ri * gapFrac - gapFrac;
      priceChart.priceScale(`ov-${key}`).applyOptions({
        scaleMargins: { top, bottom },
        visible: false,
        borderVisible: false,
      });
    });
  }

  // ---- Overlay toggles ----
  const overlayState = { vol: true, bb: true, ema: true, rsi: false, macd: false, stoch: false };

  function toggleOverlay(key) {
    overlayState[key] = !overlayState[key];
    const visible = overlayState[key];
    document.getElementById('btn-' + key)?.classList.toggle('active', visible);
    document.getElementById('m-btn-' + key)?.classList.toggle('active', visible);

    if (key === 'vol') {
      volumeSeries.applyOptions({ visible });
    } else if (key === 'bb') {
      [bbUpperSeries, bbMidSeries, bbLowerSeries].forEach(s => s.applyOptions({ visible }));
    } else if (key === 'ema') {
      [emaFastSeries, emaSlowSeries].forEach(s => s.applyOptions({ visible }));
    } else if (key === 'rsi') {
      [overlayRsiSeries, overlayRsiOB, overlayRsiOS].forEach(s => s.applyOptions({ visible }));
      recomputeOverlayMargins();
    } else if (key === 'macd') {
      [overlayMacdLine, overlayMacdSignal, overlayMacdHist].forEach(s => s.applyOptions({ visible }));
      recomputeOverlayMargins();
    } else if (key === 'stoch') {
      [overlayStochK, overlayStochD, overlayStoch80, overlayStoch20].forEach(s => s.applyOptions({ visible }));
      recomputeOverlayMargins();
    }
  }

  // ---- MACD preset ----
  function applyMacdPreset(val) {
    if (!val) return;
    const [fast, slow, signal] = val.split(',');
    document.getElementById('c-macd_fast').value   = fast;
    document.getElementById('c-macd_slow').value   = slow;
    document.getElementById('c-macd_signal').value = signal;
  }

  function syncMacdPreset(fast, slow, signal) {
    const val = `${fast},${slow},${signal}`;
    const sel = document.getElementById('macd-preset');
    sel.value = [...sel.options].some(o => o.value === val) ? val : '';
  }

  // ---- Config modal ----
  async function openConfig() {
    if (window.innerWidth <= 768) _closeAllMobilePanels('cfg');
    const res = await fetch('/api/config');
    const cfg = await res.json();
    for (const [k, v] of Object.entries(cfg)) {
      const el = document.getElementById('c-' + k);
      if (el) el.value = v;
    }
    syncMacdPreset(cfg.macd_fast, cfg.macd_slow, cfg.macd_signal);
    document.getElementById('cfg-overlay').classList.add('open');
  }

  function closeConfig() { document.getElementById('cfg-overlay').classList.remove('open'); }

  function openInfo() {
    if (window.innerWidth <= 768) _closeAllMobilePanels('info');
    const ov = document.getElementById('info-overlay');
    ov.classList.add('open');
    if (window.innerWidth <= 768) {
      ov.style.background = 'transparent';
      ov.style.backdropFilter = 'none';
      ov.style.pointerEvents = 'none';
      document.getElementById('info-panel').style.pointerEvents = 'all';
    }
  }
  function closeInfo() {
    const ov = document.getElementById('info-overlay');
    ov.classList.remove('open');
    ov.style.background = '';
    ov.style.backdropFilter = '';
    ov.style.pointerEvents = '';
  }

  async function saveConfig() {
    const keys = ['rsi_period','rsi_ma_period','rsi_oversold','rsi_overbought',
                  'macd_fast','macd_slow','macd_signal','bb_period','bb_std',
                  'ema_fast','ema_slow','confluence_threshold'];
    const body = {};
    for (const k of keys) body[k] = document.getElementById('c-' + k).value;
    await fetch('/api/config', { method:'POST', body: JSON.stringify(body) });
    closeConfig();
    loadAll();
  }

  // ---- Maximizar chart ----
  const chartMap = {
    'chart-price': priceChart,
    'chart-rsi':   rsiChart,
    'chart-macd':  macdChart,
    'chart-stoch': stochChart,
  };
  const defaultHeights = { 'chart-price': 380, 'chart-rsi': 160, 'chart-macd': 160, 'chart-stoch': 140 };

  function toggleMax(cardId, chartId, normalH) {
    const card  = document.getElementById(cardId);
    const chart = chartMap[chartId];
    const btn   = card.querySelector('.btn-maximize');
    const isMax = card.classList.toggle('maximized');

    if (isMax) {
      btn.textContent = '✕';
      btn.title = 'Restaurar';
      document.body.style.overflow = 'hidden';
      // Espera un tick para que el flexbox calcule la altura real del chart-wrap
      requestAnimationFrame(() => {
        const wrap = document.getElementById(chartId);
        chart.applyOptions({ height: wrap.clientHeight || (window.innerHeight - 80) });
      });
      // Escape key closes
      document._maxEsc = e => { if (e.key === 'Escape') toggleMax(cardId, chartId, normalH); };
      document.addEventListener('keydown', document._maxEsc);
    } else {
      btn.textContent = '⛶';
      btn.title = 'Maximizar';
      document.body.style.overflow = '';
      chart.applyOptions({ height: normalH });
      if (document._maxEsc) document.removeEventListener('keydown', document._maxEsc);
    }
    chart.applyOptions({ width: document.getElementById(chartId).clientWidth });
    const now = Math.floor(Date.now() / 1000);
    chart.timeScale().setVisibleRange({ from: now - 365 * 24 * 3600, to: now + 122 * 24 * 3600 });
  }

  // ---- Drawing tool ----
  const svgEl       = document.getElementById('drawing-svg');
  const overlayEl   = document.getElementById('chart-overlay');
  const colorInput  = document.getElementById('draw-color');
  const hintEl      = document.getElementById('draw-hint');

  let drawingMode       = null;
  let pendingTrendPoint = null;
  let previewMousePos   = null;
  let savedDrawings     = [];
  let selectedId        = null;
  let dragging          = null;
  let dragEndpoint      = null; // { id, point:'p1'|'p2' }
  let _activeHandle     = null; // { id, point } — endpoint activo visualmente

  const DRAW_HINTS = {
    horizontal: 'Clic para colocar línea horizontal',
    vertical:   'Clic para colocar línea vertical',
    trend:      'Clic punto 1 — luego clic punto 2',
    delete:     'Clic sobre una línea para borrarla',
  };

  function toggleDrawToolbar() {
    const tb = document.getElementById('draw-toolbar');
    const isOpen = tb.classList.contains('open');
    if (isOpen && drawingMode) {
      if (!confirm('¿Salir del modo de dibujo? Los trazos ya guardados se conservan.')) return;
    }
    tb.classList.toggle('open');
    document.getElementById('btn-draw-toggle').style.color = tb.classList.contains('open') ? '#f0883e' : '';
    if (!tb.classList.contains('open')) setDrawMode(null);
  }

  function saveAndExitDraw() {
    selectedId = null;
    setDrawMode(null);
    toggleDrawToolbar();
  }

  function setDrawMode(mode) {
    drawingMode = drawingMode === mode ? null : mode;
    pendingTrendPoint = null;
    ['h','v','t','del'].forEach(k => document.getElementById('db-'+k)?.classList.remove('active','del-mode'));
    const map = { horizontal:'db-h', vertical:'db-v', trend:'db-t', delete:'db-del' };
    if (drawingMode && map[drawingMode]) {
      const btn = document.getElementById(map[drawingMode]);
      btn.classList.add(drawingMode === 'delete' ? 'del-mode' : 'active');
    }
    // En modo borrar: ocultar overlay para que los clics lleguen al SVG
    overlayEl.style.display      = (drawingMode && drawingMode !== 'delete') ? 'block' : 'none';
    overlayEl.style.pointerEvents = drawingMode === 'delete' ? 'none' : 'all';
    svgEl.style.pointerEvents    = drawingMode === 'delete' ? 'all' : 'none';
    hintEl.textContent        = drawingMode ? DRAW_HINTS[drawingMode] : '';
    overlayEl.style.cursor    = drawingMode === 'delete' ? 'default' : 'crosshair';
    redrawLines();
  }

  function getColor() { return colorInput.value; }

  // ---- SVG rendering ----
  function makeLine(x1, y1, x2, y2, color, drawing) {
    const id       = drawing?.id;
    const selected  = id && id === selectedId;
    const draggingLine = dragging && dragging.id === id;

    // Visible line
    const vis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    vis.setAttribute('x1',x1); vis.setAttribute('y1',y1);
    vis.setAttribute('x2',x2); vis.setAttribute('y2',y2);
    vis.setAttribute('stroke', draggingLine ? '#58a6ff' : selected ? '#fff' : color);
    vis.setAttribute('stroke-width', draggingLine ? '2.5' : selected ? '2' : '1.5');
    if (selected && !draggingLine) vis.setAttribute('stroke-dasharray','6,3');

    if (!id) return vis;

    // Wide hit area
    const hit = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    hit.setAttribute('x1',x1); hit.setAttribute('y1',y1);
    hit.setAttribute('x2',x2); hit.setAttribute('y2',y2);
    hit.setAttribute('stroke','transparent'); hit.setAttribute('stroke-width','12');
    hit.style.cursor = 'move';

    const g = document.createElementNS('http://www.w3.org/2000/svg','g');
    g.style.pointerEvents = 'all';
    g.appendChild(vis); g.appendChild(hit);

    g.addEventListener('mouseenter', () => { if(!dragging) vis.setAttribute('stroke-width','2.5'); });
    g.addEventListener('mouseleave', () => { if(!dragging) vis.setAttribute('stroke-width', selected?'2':'1.5'); });

    function startLineDrag(clientX, clientY) {
      selectedId = id;
      redrawLines();
      if (drawingMode === 'delete') { deleteDrawing(id); return; }
      const rect = svgEl.getBoundingClientRect();
      dragging = {
        id, drawing: JSON.parse(JSON.stringify(drawing)),
        startX: clientX - rect.left,
        startY: clientY - rect.top,
      };
      document.body.style.cursor = 'move';
      document.body.style.userSelect = 'none';
    }
    g.addEventListener('mousedown', e => {
      e.stopPropagation(); e.preventDefault();
      startLineDrag(e.clientX, e.clientY);
    });
    g.addEventListener('touchstart', e => {
      e.stopPropagation(); e.preventDefault();
      startLineDrag(e.touches[0].clientX, e.touches[0].clientY);
      if (!dragging) return;
      priceChart.applyOptions({ handleScroll: false, handleScale: false });
      function onMove(ev) {
        ev.preventDefault(); ev.stopPropagation();
        onDragMove(ev.touches[0].clientX, ev.touches[0].clientY);
      }
      function onEnd() {
        priceChart.applyOptions({ handleScroll: true, handleScale: true });
        onDragEnd();
        document.removeEventListener('touchmove', onMove);
        document.removeEventListener('touchend',  onEnd);
      }
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend',  onEnd);
    }, { passive: false });

    return g;
  }

  function _clearHandleOverlays() {} // no-op — ya no usamos overlay HTML

  function _makeTrendHandle(cx, cy, drawing, point) {
    const ns       = 'http://www.w3.org/2000/svg';
    const selected = drawing.id === selectedId;
    const active   = _activeHandle && _activeHandle.id === drawing.id && _activeHandle.point === point;
    const g = document.createElementNS(ns, 'g');

    if (active) {
      // Halo exterior amarillo al tocar el endpoint
      const halo = document.createElementNS(ns, 'circle');
      halo.setAttribute('cx', cx); halo.setAttribute('cy', cy); halo.setAttribute('r', 18);
      halo.setAttribute('fill', '#f1c40f44'); halo.setAttribute('stroke', '#f1c40f');
      halo.setAttribute('stroke-width', '2'); halo.setAttribute('opacity', '0.8');
      g.appendChild(halo);
    }

    if (selected || active) {
      const vis = document.createElementNS(ns, 'circle');
      vis.setAttribute('cx', cx); vis.setAttribute('cy', cy);
      vis.setAttribute('r', active ? 10 : 8);
      vis.setAttribute('fill', active ? '#f1c40f' : '#fff');
      vis.setAttribute('stroke', active ? '#fff' : drawing.color);
      vis.setAttribute('stroke-width', '2');
      vis.setAttribute('opacity', '0.95');
      g.appendChild(vis);
    }
    return g;
  }

  // ---- Detección de endpoints por proximidad (touch móvil) ----
  // Se engancha en el contenedor del chart — no depende de pointer-events del SVG
  const _chartContainer = document.querySelector('#chart-price').parentElement;
  const HANDLE_THRESHOLD = 50; // px de radio de detección

  function _findNearestEndpoint(tx, ty) {
    for (const d of savedDrawings) {
      if (d.type !== 'trend') continue;
      const x1 = priceChart.timeScale().timeToCoordinate(d.p1.time);
      const y1 = candleSeries.priceToCoordinate(d.p1.price);
      const x2 = priceChart.timeScale().timeToCoordinate(d.p2.time);
      const y2 = candleSeries.priceToCoordinate(d.p2.price);
      for (const [px, py, pt] of [[x1,y1,'p1'],[x2,y2,'p2']]) {
        if (px == null || py == null) continue;
        if (Math.hypot(tx - px, ty - py) < HANDLE_THRESHOLD)
          return { drawing: d, point: pt };
      }
    }
    return null;
  }

  _chartContainer.addEventListener('touchstart', e => {
    if (drawingMode) return; // no interferir con modo dibujo
    const rect   = svgEl.getBoundingClientRect();
    const tx     = e.touches[0].clientX - rect.left;
    const ty     = e.touches[0].clientY - rect.top;
    const hit    = _findNearestEndpoint(tx, ty);
    if (!hit) {
      // Toque en zona vacía → deseleccionar línea
      if (selectedId) { selectedId = null; redrawLines(); }
      return;
    }

    e.preventDefault();
    e.stopPropagation();
    selectedId    = hit.drawing.id;
    dragEndpoint  = { id: hit.drawing.id, point: hit.point };
    _activeHandle = { id: hit.drawing.id, point: hit.point }; // highlight amarillo
    priceChart.applyOptions({ handleScroll: false, handleScale: false });
    redrawLines();

    function onMove(ev) {
      ev.preventDefault();
      if (!dragEndpoint) return;
      const newTime  = priceChart.timeScale().coordinateToTime(ev.touches[0].clientX - rect.left);
      const newPrice = candleSeries.coordinateToPrice(ev.touches[0].clientY - rect.top);
      const idx = savedDrawings.findIndex(s => s.id === dragEndpoint.id);
      if (idx !== -1 && newTime && newPrice != null) {
        savedDrawings[idx][dragEndpoint.point] = { time: newTime, price: parseFloat(newPrice.toFixed(2)) };
        redrawLines();
      }
    }
    function onEnd() {
      _activeHandle = null; // quitar highlight amarillo
      priceChart.applyOptions({ handleScroll: true, handleScale: true });
      onDragEnd();
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('touchend',  onEnd);
    }
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend',  onEnd);
  }, { passive: false });

  function _makePriceLabel(w, y, price, color) {
    const LW = 78, LH = 17, LR = 3, PAD = 6;
    const lx = w - LW - PAD;
    const ly = y - LH / 2;
    const ns = 'http://www.w3.org/2000/svg';
    const bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('x', lx);  bg.setAttribute('y', ly);
    bg.setAttribute('width', LW); bg.setAttribute('height', LH);
    bg.setAttribute('rx', LR); bg.setAttribute('fill', color);
    bg.setAttribute('opacity', '0.88');
    const txt = document.createElementNS(ns, 'text');
    txt.setAttribute('x', lx + LW / 2); txt.setAttribute('y', y + 1);
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('dominant-baseline', 'middle');
    txt.setAttribute('fill', '#fff');
    txt.setAttribute('font-size', '11');
    txt.setAttribute('font-family', 'monospace');
    txt.setAttribute('pointer-events', 'none');
    txt.textContent = Number(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const g = document.createElementNS(ns, 'g');
    g.appendChild(bg); g.appendChild(txt);
    return g;
  }

  function redrawLines() {
    while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);
    _clearHandleOverlays();
    const w = svgEl.clientWidth;
    const h = svgEl.clientHeight;

    for (const d of savedDrawings) {
      let el = null;
      if (d.type === 'horizontal') {
        const y = candleSeries.priceToCoordinate(d.price);
        if (y == null) continue;
        el = makeLine(0, y, w, y, d.color, d);
        if (el) {
          svgEl.appendChild(el);
          svgEl.appendChild(_makePriceLabel(w, y, d.price, d.color));
        }
        continue;
      } else if (d.type === 'vertical') {
        const x = priceChart.timeScale().timeToCoordinate(d.time);
        if (x == null) continue;
        el = makeLine(x, 0, x, h, d.color, d);
      } else if (d.type === 'trend') {
        const x1 = priceChart.timeScale().timeToCoordinate(d.p1.time);
        const y1 = candleSeries.priceToCoordinate(d.p1.price);
        const x2 = priceChart.timeScale().timeToCoordinate(d.p2.time);
        const y2 = candleSeries.priceToCoordinate(d.p2.price);
        if (x1==null||y1==null||x2==null||y2==null) continue;
        el = makeLine(x1, y1, x2, y2, d.color, d);
        if (el) {
          svgEl.appendChild(el);
          svgEl.appendChild(_makeTrendHandle(x1, y1, d, 'p1'));
          svgEl.appendChild(_makeTrendHandle(x2, y2, d, 'p2'));
        }
        continue;
      }
      if (el) svgEl.appendChild(el);
    }

    // Punto pendiente de tendencia + preview hacia el mouse
    if (pendingTrendPoint) {
      const px = priceChart.timeScale().timeToCoordinate(pendingTrendPoint.time);
      const py = candleSeries.priceToCoordinate(pendingTrendPoint.price);
      if (px!=null && py!=null) {
        // Línea fantasma de p1 al cursor (finita, sin extender)
        if (previewMousePos) {
          const ghost = document.createElementNS('http://www.w3.org/2000/svg','line');
          ghost.setAttribute('x1',px); ghost.setAttribute('y1',py);
          ghost.setAttribute('x2',previewMousePos.x); ghost.setAttribute('y2',previewMousePos.y);
          ghost.setAttribute('stroke', getColor());
          ghost.setAttribute('stroke-width','1.5');
          ghost.setAttribute('stroke-dasharray','7,4');
          ghost.setAttribute('opacity','0.6');
          svgEl.appendChild(ghost);
          // Círculo en el punto del mouse
          const cm = document.createElementNS('http://www.w3.org/2000/svg','circle');
          cm.setAttribute('cx',previewMousePos.x); cm.setAttribute('cy',previewMousePos.y); cm.setAttribute('r',4);
          cm.setAttribute('fill',getColor()); cm.setAttribute('opacity','0.55');
          svgEl.appendChild(cm);
        }
        // Círculo del primer punto
        const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
        c.setAttribute('cx',px); c.setAttribute('cy',py); c.setAttribute('r',5);
        c.setAttribute('fill',getColor()); c.setAttribute('opacity','0.9');
        svgEl.appendChild(c);
      }
    }
  }

  priceChart.timeScale().subscribeVisibleLogicalRangeChange(() => redrawLines());

  // Redibujar líneas al arrastrar eje de precios (zoom vertical)
  let _rafPending = false;
  function _scheduleRedraw() {
    if (_rafPending) return;
    _rafPending = true;
    requestAnimationFrame(() => { _rafPending = false; redrawLines(); });
  }
  let _mouseDown = false;
  document.addEventListener('mousedown', () => { _mouseDown = true; });
  document.addEventListener('mouseup',   () => { _mouseDown = false; });
  document.addEventListener('mousemove', () => { if (_mouseDown) _scheduleRedraw(); });
  // Touch (móvil)
  document.addEventListener('touchmove', _scheduleRedraw, { passive: true });

  // ---- Drag handlers (mouse + touch) ----
  function onDragMove(clientX, clientY) {
    if (dragEndpoint) {
      const rect = svgEl.getBoundingClientRect();
      const curX = clientX - rect.left;
      const curY = clientY - rect.top;
      const newTime  = priceChart.timeScale().coordinateToTime(curX);
      const newPrice = candleSeries.coordinateToPrice(curY);
      const idx = savedDrawings.findIndex(s => s.id === dragEndpoint.id);
      if (idx !== -1 && newTime && newPrice != null) {
        savedDrawings[idx][dragEndpoint.point] = { time: newTime, price: parseFloat(newPrice.toFixed(2)) };
        redrawLines();
      }
      return;
    }
    if (!dragging) return;
    const rect = svgEl.getBoundingClientRect();
    const curX = clientX - rect.left;
    const curY = clientY - rect.top;
    const dx   = curX - dragging.startX;
    const dy   = curY - dragging.startY;
    const d    = dragging.drawing;
    const idx  = savedDrawings.findIndex(s => s.id === dragging.id);
    if (idx === -1) return;
    if (d.type === 'horizontal') {
      const origY = candleSeries.priceToCoordinate(d.price);
      if (origY == null) return;
      const newPrice = candleSeries.coordinateToPrice(origY + dy);
      if (newPrice != null) savedDrawings[idx].price = parseFloat(newPrice.toFixed(2));
    } else if (d.type === 'vertical') {
      const origX = priceChart.timeScale().timeToCoordinate(d.time);
      if (origX == null) return;
      const newTime = priceChart.timeScale().coordinateToTime(origX + dx);
      if (newTime != null) savedDrawings[idx].time = newTime;
    } else if (d.type === 'trend') {
      const ox1 = priceChart.timeScale().timeToCoordinate(d.p1.time);
      const oy1 = candleSeries.priceToCoordinate(d.p1.price);
      const ox2 = priceChart.timeScale().timeToCoordinate(d.p2.time);
      const oy2 = candleSeries.priceToCoordinate(d.p2.price);
      if (ox1==null||oy1==null||ox2==null||oy2==null) return;
      const nt1 = priceChart.timeScale().coordinateToTime(ox1+dx);
      const np1 = candleSeries.coordinateToPrice(oy1+dy);
      const nt2 = priceChart.timeScale().coordinateToTime(ox2+dx);
      const np2 = candleSeries.coordinateToPrice(oy2+dy);
      if (nt1&&np1&&nt2&&np2) {
        savedDrawings[idx].p1 = { time:nt1, price:parseFloat(np1.toFixed(2)) };
        savedDrawings[idx].p2 = { time:nt2, price:parseFloat(np2.toFixed(2)) };
      }
    }
    redrawLines();
  }

  async function onDragEnd() {
    if (dragEndpoint) {
      const id  = dragEndpoint.id;
      const idx = savedDrawings.findIndex(s => s.id === id);
      dragEndpoint = null;
      document.body.style.cursor = ''; document.body.style.userSelect = '';
      if (idx !== -1) {
        const { type, p1, p2, color } = savedDrawings[idx];
        await fetch(`/api/drawings/${id}`, { method:'PATCH', body:JSON.stringify({ type, p1, p2, color }) });
      }
      redrawLines(); return;
    }
    if (!dragging) return;
    const id  = dragging.id;
    const idx = savedDrawings.findIndex(s => s.id === id);
    dragging  = null;
    document.body.style.cursor = ''; document.body.style.userSelect = '';
    if (idx !== -1) {
      const { type, price, time, p1, p2, color } = savedDrawings[idx];
      await fetch(`/api/drawings/${id}`, { method:'PATCH', body:JSON.stringify({ type, price, time, p1, p2, color }) });
    }
    redrawLines();
  }

  document.addEventListener('mousemove', e => onDragMove(e.clientX, e.clientY));
  document.addEventListener('mouseup',   () => onDragEnd());
  document.addEventListener('touchmove', e => {
    if (!dragging && !dragEndpoint) return;
    e.preventDefault();
    onDragMove(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: false });
  document.addEventListener('touchend', () => onDragEnd());

  // ---- Delete key ----
  document.addEventListener('keydown', e => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
      const activeEl = document.activeElement;
      if (activeEl && (activeEl.tagName==='INPUT'||activeEl.tagName==='TEXTAREA')) return;
      deleteDrawing(selectedId);
      selectedId = null;
    }
    if (e.key === 'Escape') {
      if (pendingTrendPoint) {
        // Cancela el punto 1 sin salir del modo tendencia
        pendingTrendPoint = null; previewMousePos = null;
        hintEl.textContent = DRAW_HINTS.trend;
        redrawLines();
      } else {
        selectedId = null; redrawLines();
      }
    }
  });

  // ---- Preview de tendencia al mover el mouse ----
  overlayEl.addEventListener('mousemove', e => {
    if (drawingMode !== 'trend' || !pendingTrendPoint) return;
    const rect = overlayEl.getBoundingClientRect();
    previewMousePos = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    redrawLines();
  });

  overlayEl.addEventListener('mouseleave', () => {
    if (previewMousePos) { previewMousePos = null; redrawLines(); }
  });

  // ---- Click handler ----
  overlayEl.addEventListener('click', e => {
    if (!drawingMode || drawingMode === 'delete') return;
    const rect  = overlayEl.getBoundingClientRect();
    const x     = e.clientX - rect.left;
    const y     = e.clientY - rect.top;
    const time  = priceChart.timeScale().coordinateToTime(x);
    const price = candleSeries.coordinateToPrice(y);
    if (time == null || price == null) return;
    const color = getColor();

    if (drawingMode === 'horizontal') {
      saveDrawing({ type:'horizontal', price:parseFloat(price.toFixed(2)), color });
    } else if (drawingMode === 'vertical') {
      saveDrawing({ type:'vertical', time, color });
    } else if (drawingMode === 'trend') {
      if (!pendingTrendPoint) {
        pendingTrendPoint = { time, price: parseFloat(price.toFixed(2)) };
        hintEl.textContent = 'Clic punto 2 para completar';
        redrawLines();
      } else {
        saveDrawing({ type:'trend', p1:pendingTrendPoint, p2:{time, price:parseFloat(price.toFixed(2))}, color });
        pendingTrendPoint = null;
        previewMousePos   = null;
        hintEl.textContent = DRAW_HINTS.trend;
      }
    }
  });

  // ---- CRUD ----
  async function loadDrawings() {
    const res = await fetch('/api/drawings');
    savedDrawings = await res.json();
    redrawLines();
  }

  async function saveDrawing(drawing) {
    const res   = await fetch('/api/drawings', { method:'POST', body:JSON.stringify(drawing) });
    const saved = await res.json();
    savedDrawings.push(saved);
    // Seleccionar la línea recién creada y salir del modo dibujo (estilo TradingView)
    selectedId = saved.id;
    setDrawMode(null);
    if (document.getElementById('draw-toolbar').classList.contains('open')) {
      document.getElementById('draw-toolbar').classList.remove('open');
      document.getElementById('btn-draw-toggle').style.color = '';
      // En móvil
      if (window.innerWidth <= 768) {
        document.getElementById('draw-toolbar').style.display = 'none';
        document.getElementById('m-tab-draw')?.classList.remove('active');
      }
    }
    redrawLines();
  }

  async function deleteDrawing(id) {
    await fetch(`/api/drawings/${id}`, { method:'DELETE' });
    savedDrawings = savedDrawings.filter(d => d.id !== id);
    redrawLines();
  }

  async function clearAllDrawings() {
    if (!confirm('¿Borrar todas las líneas?')) return;
    for (const d of [...savedDrawings]) await fetch(`/api/drawings/${d.id}`, { method:'DELETE' });
    savedDrawings = [];
    redrawLines();
  }

  // ---- Resize handles ----
  const MIN_H = 80;

  document.querySelectorAll('.resize-handle').forEach(handle => {
    const chartId = handle.dataset.chart;
    const chart   = chartMap[chartId];
    let startY, startH;

    function startResize(clientY) {
      startY = clientY;
      startH = document.getElementById(chartId).clientHeight;
      handle.classList.add('dragging');
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'ns-resize';
    }
    function doResize(clientY) {
      const newH = Math.max(MIN_H, startH + (clientY - startY));
      chart.applyOptions({ height: newH, width: document.getElementById(chartId).clientWidth });
    }
    function endResize() {
      handle.classList.remove('dragging');
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }

    // Mouse
    handle.addEventListener('mousedown', e => {
      startResize(e.clientY);
      function onMove(e) { doResize(e.clientY); }
      function onUp()    { endResize(); document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    // Touch
    handle.addEventListener('touchstart', e => {
      e.preventDefault();
      startResize(e.touches[0].clientY);
      function onMove(e) { e.preventDefault(); doResize(e.touches[0].clientY); }
      function onEnd()   { endResize(); document.removeEventListener('touchmove', onMove); document.removeEventListener('touchend', onEnd); }
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend', onEnd);
    }, { passive: false });
  });

  let _initialLoad     = true;
  let currentInterval  = '1d';

  // Rango inicial visible por intervalo (días de historia + días vacíos a la derecha)
  const IV_RANGE = {
    '1d':  { histDays: 90, padDays: 10 },
    '4h':  { histDays: 90, padDays: 10 },
    '1wk': { histDays: 90, padDays: 10 },
  };

  function setTimeframe(iv) {
    if (iv === currentInterval) return;
    currentInterval = iv;
    document.querySelectorAll('.iv-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.iv === iv)
    );
    const chartEl = document.getElementById('chart-price');
    chartEl.style.transition = 'opacity 0.18s ease';
    chartEl.style.opacity = '0';
    _initialLoad = true;
    loadAll().then(() => {
      chartEl.style.opacity = '1';
    });
  }

  // ---- Mobile tab bar ----
  // Cierra todos los paneles móviles excepto el indicado
  function _closeAllMobilePanels(except) {
    if (except !== 'ind') {
      document.getElementById('mobile-ind-panel').classList.remove('open');
      document.getElementById('m-tab-ind').classList.remove('active');
    }
    if (except !== 'sig') {
      document.getElementById('sidebar').classList.add('hidden');
      document.getElementById('m-tab-sig').classList.remove('active');
    }
    if (except !== 'draw') {
      const tb = document.getElementById('draw-toolbar');
      tb.classList.remove('open');
      tb.style.display = 'none';
      document.getElementById('m-tab-draw').classList.remove('active');
      setDrawMode(null);
    }
    if (except !== 'info') {
      document.getElementById('info-overlay').classList.remove('open');
    }
    if (except !== 'cfg') {
      document.getElementById('cfg-overlay').classList.remove('open');
    }
  }

  function toggleMobileDraw() {
    const tab = document.getElementById('m-tab-draw');
    const tb  = document.getElementById('draw-toolbar');
    const isOpen = tb.classList.contains('open');
    if (!isOpen) {
      _closeAllMobilePanels('draw');
      tb.style.display = 'flex';
      tb.classList.add('open');
      tab.classList.add('active');
    } else {
      tb.classList.remove('open');
      tb.style.display = 'none';
      tab.classList.remove('active');
      setDrawMode(null);
    }
  }

  function toggleMobileInd() {
    const panel  = document.getElementById('mobile-ind-panel');
    const tab    = document.getElementById('m-tab-ind');
    const isOpen = panel.classList.contains('open');
    if (!isOpen) {
      _closeAllMobilePanels('ind');
      panel.classList.add('open');
      tab.classList.add('active');
    } else {
      panel.classList.remove('open');
      tab.classList.remove('active');
    }
  }

  function toggleMobileSig() {
    const sb     = document.getElementById('sidebar');
    const tab    = document.getElementById('m-tab-sig');
    const isOpen = !sb.classList.contains('hidden');
    if (!isOpen) {
      _closeAllMobilePanels('sig');
      sb.classList.remove('hidden');
      tab.classList.add('active');
    } else {
      sb.classList.add('hidden');
      tab.classList.remove('active');
    }
  }

  // Sincronizar botones del panel móvil con los del desktop
  function syncMobileButtons() {
    ['vol','bb','ema','rsi','macd','stoch'].forEach(k => {
      const desktop = document.getElementById('btn-' + k);
      const mobile  = document.getElementById('m-btn-' + k);
      if (desktop && mobile) {
        mobile.className = desktop.className.replace('btn-', 'm-btn-');
        mobile.className = desktop.className;
      }
    });
  }

  // ---- Sidebar toggle ----
  function toggleSidebar() {
    const sb  = document.getElementById('sidebar');
    const btn = document.getElementById('sidebar-toggle');
    const open = sb.classList.toggle('hidden');
    btn.classList.toggle('open', !open);
    btn.textContent = open ? 'Señales ◀' : 'Señales ▶';
    // Resize charts after transition
    setTimeout(() => {
      priceChart.applyOptions({ width: document.getElementById('chart-price').clientWidth });
    }, 280);
  }

  recomputeOverlayMargins();
  loadDrawings();
  loadAll();
  setInterval(loadAll, 5 * 60 * 1000);

  // Registrar Service Worker para PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }

  // En móvil: ocultar todo excepto gráfica + tab bar
  if (window.innerWidth <= 768) {
    document.querySelectorAll(
      '.chart-card h2, .legend, #draw-toolbar, .resize-handle, #card-rsi, #card-macd, #card-stoch, #history-section'
    ).forEach(el => el.style.display = 'none');

    // Quitar bordes del card para que ocupe toda la pantalla
    const card = document.getElementById('card-price');
    card.style.cssText += ';border:none;border-radius:0;background:transparent;';
    // Mostrar botón refresh flotante
    document.getElementById('mobile-refresh-btn').style.display = 'block';

    // Forzar ancho usando window.innerWidth (clientWidth puede ser 0 en este punto)
    const mobileW = window.innerWidth;
    const ivBarH = document.querySelector('.iv-bar')?.offsetHeight || 34;
    const mobileH = window.innerHeight - 120 - ivBarH;
    priceChart.applyOptions({ width: mobileW, height: mobileH });

    // Segunda pasada tras layout completo
    setTimeout(() => {
      const ivH = document.querySelector('.iv-bar')?.offsetHeight || 34;
      priceChart.applyOptions({ width: window.innerWidth, height: window.innerHeight - 120 - ivH });
    }, 50);
  }
