// ── Globals ───────────────────────────────────────────────────
let chartInstance    = null;
let currentChartData = null; // { dates: [], prices: [] }

// ── Screen Management ─────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.remove('active');
    s.style.display = 'none';
  });
  const el = document.getElementById(id);
  el.style.display = 'flex';
  el.offsetHeight; // reflow for CSS transition
  el.classList.add('active');
}
function showSplash()    { showScreen('splash'); }
function showDashboard() { showScreen('dashboard'); }

// ── Dashboard ─────────────────────────────────────────────────
async function loadDashboard() {
  showScreen('dashboard');
  const grid = document.getElementById('cardGrid');
  grid.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Fetching live data for 12 NSE stocks…</p></div>`;

  try {
    const res  = await fetch('/recommend');
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<div class="loading-state"><div class="error-box">No data returned. Is the backend running?</div></div>`;
      return;
    }
    grid.innerHTML = '';
    data.forEach((stock, i) => {
      const card = buildCard(stock);
      card.style.animationDelay = `${i * 0.05}s`;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div class="loading-state"><div class="error-box">Could not connect to server.<br><small>${err.message}</small></div></div>`;
  }
}

function buildCard(s) {
  const riskClass = (s.risk || 'unknown').toLowerCase();
  const changePos = (s.change_pct || 0) >= 0;
  const changeStr = (changePos ? '+' : '') + (s.change_pct ?? 0) + '%';
  const rsiVal    = Math.min(100, Math.max(0, s.rsi ?? 0));

  const div = document.createElement('div');
  div.className = `stock-card ${riskClass}`;
  div.onclick   = () => loadDetail(s.full_symbol || s.symbol + '.NS');

  div.innerHTML = `
    <div class="card-header">
      <div>
        <div class="card-symbol">${esc(s.symbol)}</div>
        <div class="card-name">${esc(s.name)}</div>
        <div class="card-sector">${esc(s.sector)}</div>
      </div>
      <span class="risk-badge ${riskClass}">${s.risk || 'N/A'}</span>
    </div>
    <div class="card-price">₹${fmt(s.current_price)}</div>
    <div class="card-change ${changePos ? 'pos' : 'neg'}">${changeStr} today</div>
    <div class="card-metrics">
      <div class="metric-pill"><div class="label">RSI</div><div class="value">${s.rsi ?? 'N/A'}</div></div>
      <div class="metric-pill"><div class="label">SMA 14</div><div class="value">₹${fmt(s.sma)}</div></div>
    </div>
    <div class="rsi-bar-wrap">
      <div class="rsi-bar-label"><span>Oversold</span><span>RSI</span><span>Overbought</span></div>
      <div class="rsi-track">
        <div class="rsi-zones">
          <div class="rsi-zone-low"></div><div class="rsi-zone-mid"></div><div class="rsi-zone-high"></div>
        </div>
        <div class="rsi-dot" style="left:${rsiVal}%"></div>
      </div>
    </div>
    <div class="card-footer">
      <span class="rec-badge ${s.recommendation}">${s.recommendation}</span>
      <span class="card-cta">Deep Analysis
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </span>
    </div>`;
  return div;
}

// ── Detail View ───────────────────────────────────────────────
async function loadDetail(fullSymbol) {
  showScreen('detail');
  const content = document.getElementById('detailContent');
  const sym = fullSymbol.replace('.NS','').replace('.BSE','');
  content.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Analysing ${esc(sym)} — fetching 2 years of data &amp; news…</p></div>`;

  try {
    const res  = await fetch('/analyze', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ symbol: fullSymbol })
    });
    const data = await res.json();
    if (data.error) {
      content.innerHTML = `<div class="error-box">❌ ${esc(data.error)}</div>`;
      return;
    }
    renderDetail(data);
  } catch (err) {
    content.innerHTML = `<div class="error-box">Could not connect to server.<br><small>${err.message}</small></div>`;
  }
}

function renderDetail(d) {
  const content   = document.getElementById('detailContent');
  const changePos = (d.change_pct || 0) >= 0;
  const riskClass = (d.risk || 'unknown').toLowerCase();
  const rsiVal    = Math.min(100, Math.max(0, d.rsi ?? 0));

  // Store chart data globally for period switching
  currentChartData = d.chart_data || null;

  // Human analysis
  const analysisHTML = (d.human_analysis && d.human_analysis.length > 0)
    ? d.human_analysis.map(p => {
        const styled = p.replace(/^(My verdict: (BUY|SELL|HOLD))/, (_, full, rec) =>
          `<strong class="verdict-${rec}">${full}</strong>`);
        return `<p>${styled}</p>`;
      }).join('')
    : '<p>No analysis available.</p>';

  // News with sentiment indicators
  const newsHTML = (d.news && d.news.length > 0)
    ? d.news.map(n => buildNewsItem(n)).join('')
    : '<p style="color:var(--muted)">No recent news found.</p>';

  content.innerHTML = `
    <!-- Header -->
    <div class="detail-header">
      <div class="detail-top">
        <div>
          <div class="detail-symbol">${esc(d.symbol)}</div>
          <div class="detail-name">${esc(d.name)}</div>
        </div>
        <div class="detail-price-block">
          <span class="detail-sector-tag">${esc(d.sector)}</span>
          <div class="detail-price">₹${fmt(d.current_price)}</div>
          <div class="detail-change ${changePos ? 'pos' : 'neg'}">
            ${changePos ? '▲' : '▼'} ${Math.abs(d.change_pct ?? 0)}% today
          </div>
        </div>
      </div>
    </div>

    <!-- Metrics -->
    <div class="metrics-grid">
      <div class="metric-card"><div class="m-label">RSI</div><div class="m-value">${d.rsi ?? 'N/A'}</div></div>
      <div class="metric-card"><div class="m-label">SMA (14-day)</div><div class="m-value">₹${fmt(d.sma)}</div></div>
      <div class="metric-card"><div class="m-label">Sentiment</div><div class="m-value">${d.sentiment ?? 'N/A'}</div></div>
      <div class="metric-card"><div class="m-label">Risk</div><div class="m-value"><span class="risk-badge ${riskClass}">${d.risk || 'N/A'}</span></div></div>
      <div class="metric-card rec-card ${d.recommendation}">
        <div class="m-label">Recommendation</div>
        <div class="m-value ${d.recommendation}">${d.recommendation}</div>
      </div>
    </div>

    <!-- RSI Gauge -->
    <p class="section-title">RSI Gauge</p>
    <div class="rsi-detail">
      <div class="rsi-detail-track"><div class="rsi-detail-dot" style="left:${rsiVal}%"></div></div>
      <div class="rsi-detail-labels">
        <span>0 — Oversold</span><span>30 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 70</span><span>Overbought — 100</span>
      </div>
    </div>

    <!-- Price Chart -->
    <p class="section-title">Price History</p>
    <div class="period-tabs">
      ${['1M','3M','6M','1Y','2Y'].map(p =>
        `<button class="period-btn${p==='3M'?' active':''}" onclick="switchPeriod('${p}')">${p}</button>`
      ).join('')}
    </div>
    <div class="chart-wrap"><canvas id="priceChart"></canvas></div>
    <div class="chart-stat" id="chartStat"></div>

    <!-- AI Commentary -->
    <p class="section-title">AI Analyst Commentary</p>
    <div class="analysis-box">${analysisHTML}</div>

    <!-- News -->
    <p class="section-title">Recent News</p>
    <div class="news-list">${newsHTML}</div>
  `;

  // Render chart after DOM is ready
  if (currentChartData) {
    setTimeout(() => switchPeriod('3M'), 50);
  }
}

// ── News Item Builder ─────────────────────────────────────────
function buildNewsItem(n) {
  const lbl   = n.sentiment_label || 'neutral';
  const score = n.sentiment_score ?? 0;
  const icons = { positive: '▲ Positive', negative: '▼ Negative', neutral: '— Neutral' };
  return `
    <div class="news-item-row">
      <div class="news-sentiment-bar ${lbl}"></div>
      <div class="news-body">
        <a href="${n.url || '#'}" target="_blank" rel="noopener">${esc(n.title || 'Untitled')}</a>
        <div class="news-meta">
          ${n.source ? `<span class="news-source-txt">${esc(n.source)}</span>` : ''}
          <span class="news-badge ${lbl}">${icons[lbl]}</span>
          <span class="news-score-txt">Score: ${score}</span>
        </div>
      </div>
    </div>`;
}

// ── Chart ─────────────────────────────────────────────────────
function switchPeriod(period) {
  document.querySelectorAll('.period-btn').forEach(b =>
    b.classList.toggle('active', b.textContent === period)
  );
  if (!currentChartData) return;
  renderChart(currentChartData.dates, currentChartData.prices, period);
}

function renderChart(allDates, allPrices, period) {
  const cutoff = new Date();
  switch (period) {
    case '1M': cutoff.setMonth(cutoff.getMonth() - 1);       break;
    case '3M': cutoff.setMonth(cutoff.getMonth() - 3);       break;
    case '6M': cutoff.setMonth(cutoff.getMonth() - 6);       break;
    case '1Y': cutoff.setFullYear(cutoff.getFullYear() - 1); break;
    default:   cutoff.setFullYear(cutoff.getFullYear() - 2); // 2Y
  }

  const dates  = [];
  const prices = [];
  allDates.forEach((d, i) => {
    if (new Date(d) >= cutoff) { dates.push(d); prices.push(allPrices[i]); }
  });

  if (!dates.length) return;

  const canvas = document.getElementById('priceChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }

  const first = prices[0];
  const last  = prices[prices.length - 1];
  const isUp  = last >= first;
  const color = isUp ? '#22c55e' : '#ef4444';
  const changePct = (((last - first) / first) * 100).toFixed(2);
  const changeAmt = (last - first).toFixed(1);

  const grad = ctx.createLinearGradient(0, 0, 0, canvas.offsetHeight || 240);
  grad.addColorStop(0, color + '40');
  grad.addColorStop(1, color + '00');

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        data: prices,
        borderColor: color,
        backgroundColor: grad,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: color,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#1a1a2e',
          borderColor: '#2a2a4a',
          borderWidth: 1,
          titleColor: '#a0a0c0',
          bodyColor: '#e8e8f0',
          callbacks: {
            label: ctx => `₹${Number(ctx.raw).toLocaleString('en-IN', {maximumFractionDigits:2})}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#6b6b8a', maxTicksLimit: 7, font: { size: 11 }, maxRotation: 0 },
          grid:  { display: false },
          border:{ display: false }
        },
        y: {
          ticks: {
            color: '#6b6b8a', font: { size: 11 },
            callback: v => '₹' + Number(v).toLocaleString('en-IN', {maximumFractionDigits:0})
          },
          grid:  { color: '#1e1e35' },
          border:{ display: false }
        }
      },
      interaction: { mode: 'index', intersect: false }
    }
  });

  // Update summary stat below chart
  const stat = document.getElementById('chartStat');
  if (stat) {
    stat.innerHTML = `
      <span>Period: <strong>${period}</strong></span>
      <span>Open: <strong>₹${fmt(first)}</strong></span>
      <span>Current: <strong>₹${fmt(last)}</strong></span>
      <span class="${isUp ? 'up' : 'down'}">${isUp ? '▲' : '▼'} ${Math.abs(changePct)}% (₹${Math.abs(changeAmt)})</span>
    `;
  }
}

// ── Search ────────────────────────────────────────────────────
function searchStock()  {
  const val = document.getElementById('searchInput').value.trim();
  if (val) loadDetail(val);
}
function searchStock2() {
  const val = document.getElementById('searchInput2').value.trim();
  if (val) loadDetail(val);
}

// ── Helpers ───────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmt(n) {
  if (n === null || n === undefined) return 'N/A';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}