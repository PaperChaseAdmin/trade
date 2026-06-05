#!/usr/bin/env python3
"""Add Top Pick section + 10-day history to Poly Watch."""
path = "/mnt/c/Hermes/paper_trading/polymarket/index.html"
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add Top Pick + History HTML (after stats bar, before filter bar)
old_html = '''  <!-- Stats -->
  <div class="stats-bar" id="statsBar"></div>

  <!-- Filters -->'''

new_html = '''  <!-- Stats -->
  <div class="stats-bar" id="statsBar"></div>

  <!-- TOP PICK -->
  <div id="topPickSection" style="display:none;margin-bottom:20px">
    <div class="section-title" style="font-size:12px;margin-bottom:8px;display:flex;align-items:center;gap:8px">
      <span>🏆 TODAY'S TOP PICK</span>
      <span id="topPickDate" style="font-size:10px;color:var(--tv-text-3);font-weight:400"></span>
    </div>
    <div id="topPickCard" style="background:var(--tv-surface);border:2px solid var(--tv-green);border-radius:var(--tv-radius);padding:18px;box-shadow:0 4px 20px rgba(0,0,0,0.3);cursor:pointer" onclick="toggleAI(this)">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px">
        <div style="flex:1">
          <div id="topPickQuestion" style="font-size:15px;font-weight:600;color:var(--tv-text);line-height:1.4;margin-bottom:6px"></div>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span id="topPickAction" style="font-size:13px;font-weight:700;padding:3px 10px;border-radius:4px;display:inline-block"></span>
            <span id="topPickProb" style="font-size:13px;color:var(--tv-text-2)"></span>
            <span id="topPickVol" style="font-size:12px;color:var(--tv-text-3)"></span>
            <span id="topPickTag" style="font-size:10px;font-weight:600;padding:1px 6px;border-radius:2px;background:var(--tv-surface-3);color:var(--tv-text-3)"></span>
          </div>
        </div>
        <div id="topPickScore" style="font-size:24px;font-weight:800;font-family:var(--tv-mono);color:var(--tv-green);flex-shrink:0;text-align:right"></div>
      </div>
      <div id="topPickAI" class="market-card-ai" style="display:none">
        <span id="topPickAIOutlook" class="ai-outlook"></span>
        <span id="topPickAIConf" class="ai-conf"></span>
        <span id="topPickAIAnalysis"></span>
      </div>
    </div>
  </div>

  <!-- 10-DAY PREDICTION HISTORY -->
  <div id="predHistSection" style="display:none;margin-bottom:20px">
    <div class="section-title" style="font-size:12px;margin-bottom:8px;display:flex;align-items:center;gap:8px">
      <span>📊 10-DAY PREDICTION TRACK RECORD</span>
      <span id="predHistAcc" style="font-size:11px;color:var(--tv-text-3);font-weight:400"></span>
    </div>
    <div id="predHistTable" style="display:flex;flex-direction:column;gap:2px">
      <div style="color:var(--tv-text-2);padding:8px;font-size:12px;text-align:center">No prediction history yet — predictions recorded daily</div>
    </div>
  </div>

  <!-- Filters -->'''

c = c.replace(old_html, new_html)

# 2. Add Top Pick CSS (add after .market-card-ai styles)
old_css = '/* Loading */'
new_css = '''/* Top Pick */
.section-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--tv-text-2)}
/* Loading */'''
c = c.replace(old_css, new_css)

# 3. Add JS functions before loadData()
old_js_end = '''async function loadData() {'''
new_js = r'''// ── TOP PICK ───────────────────────────────────────────────────────────
function renderTopPick(markets) {
  const section = document.getElementById('topPickSection');
  // Find the market with highest heuristic score
  const scored = markets.filter(m => m.heuristic && m.heuristic.score > 0)
    .sort((a, b) => (b.heuristic.score || 0) - (a.heuristic.score || 0));
  
  if (scored.length === 0) { section.style.display = 'none'; return; }
  
  const top = scored[0];
  const h = top.heuristic || {};
  const ai = top.ai || {};
  const pct = (top.yes_price * 100).toFixed(1);
  const betYes = top.yes_price >= 0.5;
  
  document.getElementById('topPickDate').textContent = new Date().toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});
  document.getElementById('topPickQuestion').textContent = top.question;
  
  const actionEl = document.getElementById('topPickAction');
  actionEl.textContent = betYes ? '▸ BET YES' : '▸ BET NO';
  actionEl.style.background = betYes ? 'rgba(8,153,129,0.2)' : 'rgba(242,54,69,0.2)';
  actionEl.style.color = betYes ? '#089981' : '#f23645';
  actionEl.style.border = '1px solid ' + (betYes ? 'rgba(8,153,129,0.3)' : 'rgba(242,54,69,0.3)');
  
  document.getElementById('topPickProb').innerHTML = 'Yes: <strong>' + pct + '%</strong>';
  document.getElementById('topPickVol').textContent = 'Vol: ' + fmt(top.volume);
  document.getElementById('topPickTag').textContent = (top.tag || '').toUpperCase();
  document.getElementById('topPickScore').textContent = h.score || '';
  
  // AI analysis
  if (ai.ai_analysis) {
    document.getElementById('topPickAIOutlook').textContent = (ai.ai_outlook||'neutral').toUpperCase();
    document.getElementById('topPickAIOutlook').style.color = ai.ai_outlook==='yes' ? '#089981' : '#f23645';
    document.getElementById('topPickAIConf').textContent = '(' + (ai.ai_confidence||0) + '% confidence)';
    document.getElementById('topPickAIAnalysis').textContent = ' — ' + ai.ai_analysis;
  }
  
  section.style.display = 'block';
  
  // Save to localStorage prediction history
  savePrediction(top, betYes);
}

// ── PREDICTION HISTORY (localStorage) ──
function savePrediction(market, betYes) {
  const today = new Date().toISOString().split('T')[0];
  let history = JSON.parse(localStorage.getItem('polywatch_predictions') || '[]');
  
  // Don't save duplicate for today
  if (history.length > 0 && history[0].date === today) return;
  
  history.unshift({
    date: today,
    question: market.question,
    bet: betYes ? 'YES' : 'NO',
    prob: (market.yes_price * 100).toFixed(1) + '%',
    tag: market.tag || '',
    score: (market.heuristic || {}).score || 0,
    result: null,  // Unknown until tomorrow
    correct: null
  });
  
  // Keep max 15 entries
  history = history.slice(0, 15);
  localStorage.setItem('polywatch_predictions', JSON.stringify(history));
  renderPredHist(history);
}

function renderPredHist(history) {
  const section = document.getElementById('predHistSection');
  if (!history || history.length === 0) { section.style.display = 'none'; return; }
  
  // Calculate accuracy
  const resolved = history.filter(h => h.correct !== null);
  const correct = resolved.filter(h => h.correct).length;
  const total = resolved.length;
  const accPct = total > 0 ? Math.round(correct / total * 100) : 0;
  
  document.getElementById('predHistAcc').textContent = total > 0 ? accPct + '% accuracy (' + correct + '/' + total + ')' : '';
  
  const tableHtml = history.slice(0, 10).map(h => {
    const isResolved = h.correct !== null;
    const resultColor = h.correct ? '#089981' : '#f23645';
    const resultIcon = h.correct ? '✅' : '❌';
    const resultText = h.correct ? 'CORRECT' : 'WRONG';
    const betColor = h.bet === 'YES' ? '#089981' : '#f23645';
    
    return '<div style="display:grid;grid-template-columns:80px 1fr 55px 50px;gap:6px;align-items:center;padding:6px 10px;border-radius:var(--tv-radius-sm);background:' +
      (isResolved ? (h.correct ? 'rgba(8,153,129,0.05)' : 'rgba(242,54,69,0.05)') : 'var(--tv-surface-2)') +
      ';font-size:11px;border:1px solid var(--tv-border)">' +
      '<span style="color:var(--tv-text-3);font-weight:600;font-size:10px">' + h.date.slice(5) + '</span>' +
      '<span style="color:var(--tv-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + h.question + '</span>' +
      '<span style="font-weight:700;color:' + betColor + ';text-align:center">' + h.bet + '</span>' +
      (isResolved
        ? '<span style="color:' + resultColor + ';font-weight:600;text-align:right;font-size:11px">' + resultIcon + ' ' + resultText + '</span>'
        : '<span style="color:var(--tv-text-3);text-align:right;font-size:10px">⏳ Pending</span>') +
    '</div>';
  }).join('');
  
  document.getElementById('predHistTable').innerHTML = tableHtml;
  section.style.display = 'block';
}

async function loadData() {'''

c = c.replace(old_js_end, new_js)

# 4. Add renderTopPick call inside loadData (after stats)
old_load = '''    renderMarkets();
  } catch(e) {'''
new_load = '''    renderMarkets();
    renderTopPick(allMarkets);
    
    // Load prediction history
    const history = JSON.parse(localStorage.getItem('polywatch_predictions') || '[]');
    renderPredHist(history);
  } catch(e) {'''

c = c.replace(old_load, new_load)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print("Poly Watch updated!")
