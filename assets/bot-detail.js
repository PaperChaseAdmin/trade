/* Bot detail page — shared logic. Requires BOT_ID and BOT_COLOR globals. */
'use strict';

const BASE = `/trade/data/bots/${BOT_ID}/`;
let chart = null;

const $ = id => document.getElementById(id);
function fmt(v){ return '$'+Math.abs(+v).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function sign(v){ const c=+v>=0?'profit':'loss'; return `<span class="${c}">${+v>=0?'+':'-'}${fmt(Math.abs(+v))}</span>`; }
function signPct(v){ const c=+v>=0?'profit':'loss'; return `<span class="${c}">${+v>=0?'+':''}${(+v).toFixed(2)}%</span>`; }
function ago(ts){ const m=Math.floor((Date.now()-new Date(ts))/60000); return m<1?'just now':m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`; }
function fmtTs(ts){ const d=new Date(ts); return d.toLocaleDateString('en-US',{month:'short',day:'numeric'})+' '+d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false})+' UTC'; }

function renderSpecs(){
  if(typeof BOT_WATCHLIST==='undefined') return;
  const pct=(BOT_MAX_POSITION*100).toFixed(0);
  const tickers=BOT_WATCHLIST.map(t=>
    `<a class="ticker-chip" href="https://finance.yahoo.com/quote/${t}" target="_blank" rel="noopener">${t}</a>`
  ).join('');
  $('specs').innerHTML=`
    <div class="spec-card">
      <div class="spec-card-title">Bot Specifications</div>
      <div class="spec-grid">
        <div class="spec-item">
          <div class="spec-label">AI Engine</div>
          <div class="spec-val">Gemini 2.0 Flash</div>
          <div class="spec-sub">Google DeepMind</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Market Data</div>
          <div class="spec-val">Yahoo Finance</div>
          <div class="spec-sub">~15 min delayed</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Update Frequency</div>
          <div class="spec-val">Every 30 min</div>
          <div class="spec-sub">During market hours</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Active Hours</div>
          <div class="spec-val">Mon–Fri</div>
          <div class="spec-sub">09:00–17:00 ET</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Max Position Size</div>
          <div class="spec-val">${pct}%</div>
          <div class="spec-sub">of portfolio per stock</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Max Trades / Session</div>
          <div class="spec-val">${BOT_MAX_TRADES}</div>
          <div class="spec-sub">per 30-min run</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Min Cash Reserve</div>
          <div class="spec-val">${fmt(BOT_MIN_CASH)}</div>
          <div class="spec-sub">always kept liquid</div>
        </div>
        <div class="spec-item">
          <div class="spec-label">Starting Capital</div>
          <div class="spec-val">$10,000</div>
          <div class="spec-sub">paper money</div>
        </div>
      </div>
      <div class="spec-label" style="margin:20px 0 10px">Watchlist — ${BOT_WATCHLIST.length} tickers monitored each session</div>
      <div class="ticker-list">${tickers}</div>
    </div>`;
}

function renderFollowGuide(){
  $('follow').innerHTML=`
    <div class="follow-card">
      <div class="spec-card-title">How to Follow This Bot</div>
      <div class="follow-steps">
        <div class="follow-step">
          <span class="follow-num">1</span>
          <span>Scroll down to <strong>Recent Trades</strong> — the bot's latest signals appear here. The page auto-refreshes every 90 seconds.</span>
        </div>
        <div class="follow-step">
          <span class="follow-num">2</span>
          <span>When you see a <span class="badge badge-buy">BUY</span>, consider opening a position at market price in your broker for the same ticker.</span>
        </div>
        <div class="follow-step">
          <span class="follow-num">3</span>
          <span>When you see a <span class="badge badge-sell">SELL</span>, consider closing or trimming your position in that ticker.</span>
        </div>
        <div class="follow-step">
          <span class="follow-num">4</span>
          <span>Read the <strong>Reasoning</strong> column — the AI explains its logic for every trade so you can judge whether it aligns with your own view.</span>
        </div>
        <div class="follow-step">
          <span class="follow-num">5</span>
          <span>Check <a href="/trade/${BOT_ID}/records/" style="color:var(--accent)">Full Trade Records →</a> for the complete history, win rate, and total volume.</span>
        </div>
      </div>
      <div class="follow-warning">
        ⚠ This bot trades with <strong>simulated paper money only</strong>. Past performance does not guarantee future results.
        Nothing on this page is financial advice. Always do your own due diligence before trading real money.
      </div>
    </div>`;
}

async function load(){
  const [pf, tr] = await Promise.all([
    fetch(BASE+'portfolio.json?t='+Date.now()).then(r=>r.json()),
    fetch(BASE+'trades.json?t='+Date.now()).then(r=>r.json())
  ]);
  renderHero(pf);
  renderOutlook(pf);
  renderLastSession(pf);
  renderSpecs();
  renderFollowGuide();
  renderChart(pf);
  renderPositions(pf);
  renderTrades(tr.trades||[]);
  $('loading').style.display='none';
  $('app').style.display='block';
  setTimeout(load,90000);
}

function renderHero(pf){
  const ret=+pf.total_return_pct||0;
  $('hero').innerHTML=`
    <div class="bot-hero" style="--bot-color:${BOT_COLOR}">
      <div class="hero-row">
        <div class="hero-icon">${BOT_AVATAR}</div>
        <div class="hero-meta">
          <div class="hero-name">${BOT_NAME}</div>
          <div class="hero-bio">${BOT_BIO}</div>
          <div class="hero-strategy">${BOT_STRATEGY}</div>
          <div class="risk-meter" style="margin-top:8px">
            <div class="risk-track"><div class="risk-fill" style="width:${BOT_RISK_BAR*10}%;background:${BOT_COLOR}"></div></div>
            <span class="risk-text">${BOT_RISK} RISK</span>
          </div>
        </div>
      </div>
      <div class="metrics-row">
        <div class="metric"><div class="metric-lbl">Portfolio</div><div class="metric-val">${fmt(pf.total_value||0)}</div></div>
        <div class="metric"><div class="metric-lbl">Return</div><div class="metric-val ${ret>=0?'profit':'loss'}">${ret>=0?'+':''}${ret.toFixed(2)}%</div></div>
        <div class="metric"><div class="metric-lbl">P&amp;L</div><div class="metric-val">${sign((pf.total_value||0)-10000)}</div></div>
        <div class="metric"><div class="metric-lbl">Today</div><div class="metric-val">${sign(pf.today_pnl||0)}</div></div>
        <div class="metric"><div class="metric-lbl">Cash</div><div class="metric-val">${fmt(pf.cash||0)}</div></div>
        <div class="metric"><div class="metric-lbl">Positions</div><div class="metric-val">${Object.keys(pf.positions||{}).length}</div></div>
        <div class="metric"><div class="metric-lbl">Trades</div><div class="metric-val">${pf.total_trades||0}</div></div>
        <div class="metric"><div class="metric-lbl">Updated</div><div class="metric-val" style="font-size:12px"><span class="live"></span>${ago(pf.last_updated)}</div></div>
      </div>
    </div>`;
}

function renderOutlook(pf){
  if(!pf.last_action||pf.last_action.startsWith('Init')) return;
  $('outlook').innerHTML=`<div class="outlook" style="--bot-color:${BOT_COLOR}"><div class="outlook-lbl">Latest Thinking</div>${pf.last_action}</div>`;
}

function renderLastSession(pf){
  const s=pf.last_session;
  const el=$('last-session');
  if(!s||!s.at){ el.innerHTML=''; return; }

  // Market condition chips
  const fg=s.fear_greed;
  const fgLabel=s.fear_greed_label||'';
  const fgClass=fg!=null?(fg<30?'fear':fg>70?'greed':''):'';
  const sp=s.sp500_change;
  const spStr=sp!=null?`${sp>=0?'+':''}${Number(sp).toFixed(2)}%`:'N/A';
  const spClass=sp!=null?(sp>=0?'up':'down'):'';
  const vixVal=s.vix!=null?Number(s.vix).toFixed(1):'N/A';

  const chips=[
    `<span class="chip ${fgClass}">Fear&amp;Greed: ${fg??'N/A'} ${fgLabel?`(${fgLabel})`:''}</span>`,
    `<span class="chip ${spClass}">S&amp;P 500: ${spStr}</span>`,
    `<span class="chip">VIX: ${vixVal}</span>`,
  ].join('');

  // Watchlist movers
  const movers=(s.top_movers||[]).map(([t,c])=>{
    const cls=Math.abs(c)<0.1?'flat':c>0?'up':'down';
    return `<span class="mover-chip ${cls}">${t} ${c>=0?'+':''}${Number(c).toFixed(1)}%</span>`;
  }).join('');

  // News
  const newsItems=(s.news_read||[]).map(h=>`<li>${h}</li>`).join('');

  // Domain extra
  const extra=s.domain_extra?`<div class="session-block"><div class="session-block-lbl">Domain Context</div><div class="domain-extra">${s.domain_extra}</div></div>`:'';

  // AI reasoning
  const reasoning=s.ai_analysis?`<div class="session-block"><div class="session-block-lbl">AI Reasoning</div><div class="ai-reasoning" style="--bot-color:${BOT_COLOR}">${s.ai_analysis}</div></div>`:'';

  // Decision badge
  const n=s.trades_made||0;
  const badgeClass=n>0?'traded':'';
  const badgeText=n>0?`${n} trade${n>1?'s':''} executed`:'No trades — held position';

  const sessionAt=new Date(s.at);
  const timeStr=sessionAt.toLocaleDateString('en-US',{month:'short',day:'numeric'})+' '+
    sessionAt.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false})+' UTC';

  el.innerHTML=`
  <div class="session-card" style="--bot-color:${BOT_COLOR}">
    <div class="session-header">
      <span class="session-title">🔍 Last Session Analysis</span>
      <span class="session-time">${timeStr}</span>
    </div>

    <div class="session-block">
      <div class="session-block-lbl">Market Conditions Observed</div>
      <div class="condition-chips">${chips}</div>
      ${movers?`<div class="movers-row" style="margin-top:6px">${movers}</div>`:''}
    </div>

    ${newsItems?`<div class="session-block">
      <div class="session-block-lbl">News Analyzed (filtered to this bot's domain)</div>
      <ul class="session-news">${newsItems}</ul>
    </div>`:''}

    ${extra}
    ${reasoning}

    <div class="session-footer">
      <span class="decision-badge ${badgeClass}">${badgeText}</span>
    </div>
  </div>`;
}

function renderChart(pf){
  const hist=(pf.portfolio_history||[]).slice(-120);
  if(hist.length<2){ $('chart-wrap').innerHTML='<div class="empty">No trading history yet</div>'; return; }
  const labels=hist.map(h=>{ const d=new Date(h.timestamp); return (d.getMonth()+1)+'/'+d.getDate()+' '+String(d.getUTCHours()).padStart(2,'0')+':'+String(d.getUTCMinutes()).padStart(2,'0'); });
  const vals=hist.map(h=>h.value);
  const isUp=vals[vals.length-1]>=10000;
  const color=isUp?'#3fb950':'#f85149';
  if(chart) chart.destroy();
  chart=new Chart($('chart'),{type:'line',data:{labels,datasets:[{data:vals,borderColor:color,backgroundColor:color.replace(')',',0.06)').replace('rgb','rgba'),borderWidth:2,pointRadius:0,fill:true,tension:0.3}]},
    options:{responsive:true,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' $'+ctx.parsed.y.toLocaleString('en-US',{minimumFractionDigits:2})}}},
    scales:{x:{ticks:{color:'#8b949e',maxTicksLimit:8,font:{family:'JetBrains Mono',size:10}},grid:{color:'rgba(255,255,255,.04)'}},
            y:{ticks:{color:'#8b949e',font:{family:'JetBrains Mono',size:10},callback:v=>'$'+v.toLocaleString('en-US',{maximumFractionDigits:0})},grid:{color:'rgba(255,255,255,.04)'}}}}});
}

function renderPositions(pf){
  const pos=pf.positions||{};
  const el=$('positions');
  if(!Object.keys(pos).length){ el.innerHTML='<div class="empty">No open positions — all cash</div>'; return; }
  let rows='';
  for(const [t,p] of Object.entries(pos)){
    const cur=p.current_price||p.avg_cost;
    const pnl=(cur-p.avg_cost)*p.shares;
    const pct=(cur-p.avg_cost)/p.avg_cost*100;
    rows+=`<tr><td class="mono" style="font-weight:600">${t}</td><td class="mono">${p.shares}</td><td class="mono">${fmt(p.avg_cost)}</td><td class="mono">${fmt(cur)}</td><td class="mono">${fmt(p.shares*cur)}</td><td class="mono ${pnl>=0?'profit':'loss'}">${pnl>=0?'+':'-'}${fmt(Math.abs(pnl))} <span style="font-size:11px">(${pct>=0?'+':''}${pct.toFixed(2)}%)</span></td></tr>`;
  }
  el.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Shares</th><th>Avg Cost</th><th>Current</th><th>Mkt Value</th><th>Unrealised P&L</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderTrades(trades){
  const el=$('trades');
  const recent=[...trades].reverse().slice(0,10);
  if(!recent.length){ el.innerHTML='<div class="empty">No trades yet — bot activates when US market opens</div>'; return; }
  let rows='';
  recent.forEach(t=>{
    const badge=t.action==='BUY'?'<span class="badge badge-buy">BUY</span>':'<span class="badge badge-sell">SELL</span>';
    // Build signal context line
    let ctxHtml='';
    const sc=t.signal_context;
    if(sc){
      const parts=[];
      if(sc.ticker_chg_pct!=null){
        const cls=sc.ticker_chg_pct>0?'ctx-up':'ctx-down';
        parts.push(`<span class="ctx-item ${cls}">${t.ticker}: ${sc.ticker_chg_pct>=0?'+':''}${Number(sc.ticker_chg_pct).toFixed(1)}%</span>`);
      }
      if(sc.fg_value!=null) parts.push(`<span class="ctx-item">F&amp;G: ${sc.fg_value} ${sc.fg_label?`(${sc.fg_label})`:''}</span>`);
      if(sc.sp500_chg!=null){
        const cls=sc.sp500_chg>=0?'ctx-up':'ctx-down';
        parts.push(`<span class="ctx-item ${cls}">S&amp;P: ${sc.sp500_chg>=0?'+':''}${Number(sc.sp500_chg).toFixed(1)}%</span>`);
      }
      if(sc.vix!=null) parts.push(`<span class="ctx-item">VIX: ${Number(sc.vix).toFixed(1)}</span>`);
      if(parts.length) ctxHtml=`<div class="signal-ctx">${parts.join('')}</div>`;
    }
    const reasonCell=`<div style="color:var(--text-2);font-size:12px;line-height:1.5;max-width:260px">${t.reasoning||'—'}</div>${ctxHtml}`;
    rows+=`<tr>
      <td class="mono" style="color:var(--text-2);white-space:nowrap">${fmtTs(t.timestamp)}</td>
      <td>${badge}</td>
      <td class="mono" style="font-weight:600">${t.ticker}</td>
      <td class="mono">${t.shares}</td>
      <td class="mono">${fmt(t.price)}</td>
      <td class="mono">${fmt(t.total_value)}</td>
      <td>${reasonCell}</td>
    </tr>`;
  });
  el.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Time (UTC)</th><th>Action</th><th>Ticker</th><th>Shares</th><th>Price</th><th>Total</th><th>Reasoning &amp; Signal</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

document.addEventListener('DOMContentLoaded',()=>{
  document.title=`${BOT_NAME} · PaperChase Trading Arena`;
  $('app').style.display='none';
  load().catch(e=>{ $('loading').textContent='Error: '+e.message; });
});
