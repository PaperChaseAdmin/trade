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

async function load(){
  const [pf, tr] = await Promise.all([
    fetch(BASE+'portfolio.json?t='+Date.now()).then(r=>r.json()),
    fetch(BASE+'trades.json?t='+Date.now()).then(r=>r.json())
  ]);
  renderHero(pf);
  renderOutlook(pf);
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
    rows+=`<tr><td class="mono" style="color:var(--text-2);white-space:nowrap">${fmtTs(t.timestamp)}</td><td>${badge}</td><td class="mono" style="font-weight:600">${t.ticker}</td><td class="mono">${t.shares}</td><td class="mono">${fmt(t.price)}</td><td class="mono">${fmt(t.total_value)}</td><td style="color:var(--text-2);font-size:12px;max-width:240px">${t.reasoning||'—'}</td></tr>`;
  });
  el.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Time (UTC)</th><th>Action</th><th>Ticker</th><th>Shares</th><th>Price</th><th>Total</th><th>Reasoning</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

document.addEventListener('DOMContentLoaded',()=>{
  document.title=`${BOT_NAME} · PaperChase Trading Arena`;
  $('app').style.display='none';
  load().catch(e=>{ $('loading').textContent='Error: '+e.message; });
});
