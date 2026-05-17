"""Generate HTML wrapper pages + Market Sentinel page."""
import os, json, shutil
from bot_profiles import BOT_PROFILES

DETAIL_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{name} · AI Trading Bot · PaperChase</title>
<meta name="description" content="Watch {name}, an AI-powered trading bot with a {strategy} strategy. Real portfolio, live trades, transparent AI decisions on PaperChase."/>
<meta name="robots" content="index, follow"/>
<link rel="canonical" href="https://paperchase.online/trade/{bot_id}/"/>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-W3V49QCMT0"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-W3V49QCMT0');
</script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="/trade/assets/i18n.js"></script>
<script src="/trade/assets/supabase-client.js"></script>
</head>
<body>
<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">PaperChase</a>
  <div class="topbar-nav">
    <a class="nav-link" href="/" data-i18n="nav.home">Home</a>
    <a class="nav-link" href="/trade/" data-i18n="nav.ai_trading">AI Trading</a>
    <a class="nav-link" href="/market-sentinel/" data-i18n="nav.market_sentinel">Market Sentinel</a>
    <a class="nav-link" href="/trade/polymarket/" data-i18n="nav.polymarket">Polymarket</a>
    <a class="nav-link" href="/login" data-i18n="nav.login">Login</a>
    <a class="nav-link" href="/register" data-i18n="nav.register">Register</a>
  </div>
  <div class="lang-switcher">
    <select id="lang-select" onchange="switchLang(this.value)">
      <option value="en">EN</option>
      <option value="ja">JA</option>
      <option value="ko">KO</option>
      <option value="zh">ZH</option>
      <option value="es">ES</option>
      <option value="fr">FR</option>
    </select>
  </div>
</div></nav>
<div class="container">
  <a class="back-link" href="/trade/" data-i18n="nav.all_bots">← All Bots</a>
  <div class="favourite-bar" style="display:flex;justify-content:flex-end;align-items:center;padding:8px 0">
    <button id="favBtn" class="fav-btn" onclick="toggleFavourite()" style="background:none;border:1px solid var(--tv-border-2,#363a45);border-radius:var(--tv-radius-sm,4px);padding:6px 12px;cursor:pointer;font-size:13px;color:var(--tv-text-2,#787b86);display:none">
      <span id="favIcon">☆</span> <span id="favLabel" data-i18n="favourite_add">Add to Favourites</span>
    </button>
  </div>
  <div id="loading" style="text-align:center;padding:40px;color:var(--tv-text-2)" data-i18n="loading.bot">Loading {name}...</div>
  <div id="app" style="display:none">
    <div id="hero"></div>
    <div id="outlook"></div>
    <div id="prices-bar"></div>
    <div id="last-session"></div>
    <div id="specs"></div>
    <div id="follow"></div>
    <div class="chart-wrap"><canvas id="chart"></canvas></div>
    <div class="section-title" data-i18n="detail.current_positions">Current Positions</div>
    <div id="positions" style="margin-bottom:16px"></div>
    <div class="section-title" data-i18n="detail.recent_trades">Recent Trades</div>
    <div id="trades"></div>
    <div style="margin-top:20px;display:flex;gap:16px">
      <a class="back-link" href="/trade/" data-i18n="nav.leaderboard">← Leaderboard</a>
      <a class="back-link" href="/trade/{bot_id}/records/" data-i18n="nav.full_records">Full Records →</a>
    </div>
  </div>
</div>
<script>
const BOT_ID='{bot_id}',BOT_COLOR='{color}',BOT_NAME='{name}';
const BOT_AVATAR='{avatar}',BOT_BIO='{bio}',BOT_STRATEGY='{strategy}';
const BOT_RISK='{risk_level}',BOT_RISK_BAR={risk_bar};
const BOT_MODEL='{model}';
const BOT_FALLBACK='{fallback_model}';
const BOT_WATCHLIST={watchlist};
const BOT_MAX_POSITION={max_position_pct},BOT_MAX_TRADES={max_trades},BOT_MIN_CASH={min_cash};
</script>
<script src="/trade/assets/bot-detail.js"></script>
<script>
// ── Favourite Toggle ──
async function checkFavStatus() {{
  if (!window.PaperChaseAuth) return;
  var session = await PaperChaseAuth.getSession();
  var btn = document.getElementById('favBtn');
  if (!btn) return;
  if (!session) {{ btn.style.display = 'none'; return; }}
  btn.style.display = '';
  var isFav = await PaperChaseAuth.isFavourite(BOT_ID);
  document.getElementById('favIcon').textContent = isFav ? '★' : '☆';
  document.getElementById('favLabel').textContent = isFav ? 'Remove from Favourites' : 'Add to Favourites';
}}
async function toggleFavourite() {{
  if (!window.PaperChaseAuth) return;
  var session = await PaperChaseAuth.getSession();
  if (!session) {{ alert('Please log in to add favourites.'); return; }}
  var isFav = await PaperChaseAuth.isFavourite(BOT_ID);
  if (isFav) {{
    await PaperChaseAuth.removeFavourite(BOT_ID);
  }} else {{
    await PaperChaseAuth.addFavourite(BOT_ID, BOT_NAME, BOT_AVATAR);
  }}
  checkFavStatus();
}}
checkFavStatus();
</script>
</body></html>
"""

RECORDS_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{name} Trade Records · PaperChase</title>
<meta name="description" content="Complete trade history for {name} AI trading bot on PaperChase. View all past trades, win rate, and performance."/>
<meta name="robots" content="noindex, follow"/>
<link rel="canonical" href="https://paperchase.online/trade/{bot_id}/records/"/>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-W3V49QCMT0"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-W3V49QCMT0');
</script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
<script src="/trade/assets/i18n.js"></script>
</head>
<body>
<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">PaperChase</a>
  <div class="topbar-nav">
    <a class="nav-link" href="/" data-i18n="nav.home">Home</a>
    <a class="nav-link" href="/trade/" data-i18n="nav.ai_trading">AI Trading</a>
    <a class="nav-link" href="/market-sentinel/" data-i18n="nav.market_sentinel">Market Sentinel</a>
    <a class="nav-link" href="/trade/polymarket/" data-i18n="nav.polymarket">Polymarket</a>
    <a class="nav-link" href="/login" data-i18n="nav.login">Login</a>
    <a class="nav-link" href="/register" data-i18n="nav.register">Register</a>
  </div>
  <div class="lang-switcher">
    <select id="lang-select" onchange="switchLang(this.value)">
      <option value="en">EN</option>
      <option value="ja">JA</option>
      <option value="ko">KO</option>
      <option value="zh">ZH</option>
      <option value="es">ES</option>
      <option value="fr">FR</option>
    </select>
  </div>
</div></nav>
<div class="container">
  <a class="back-link" href="/trade/{bot_id}/" data-i18n="records.back_to_bot">← {avatar} {name}</a>
  <div class="page-header">
    <div style="font-size:20px;font-weight:600;color:var(--tv-text)" data-i18n="records.title">{avatar} {name} — Trade Records</div>
    <div class="page-sub" data-i18n="records.subtitle">Complete history · All times UTC</div>
  </div>
  <div id="stats" class="stats-grid" style="grid-template-columns:repeat(4,1fr)"></div>
  <div style="display:flex;gap:8px;margin-bottom:12px">
    <button class="nav-link active" onclick="setFilter('all',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface);color:var(--tv-text)" data-i18n="records.filter_all">All</button>
    <button class="nav-link" onclick="setFilter('BUY',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface)" data-i18n="records.filter_buys">Buys</button>
    <button class="nav-link" onclick="setFilter('SELL',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface)" data-i18n="records.filter_sells">Sells</button>
    <span style="font-size:11px;color:var(--tv-text-2);margin-left:auto" id="count"></span>
  </div>
  <div id="records"></div>
</div>
<script>
const BOT_ID='{bot_id}',BOT_COLOR='{color}',BOT_NAME='{name}',BOT_AVATAR='{avatar}';
</script>
<script src="/trade/assets/records.js"></script>
</body></html>
"""

count = 0
for bot_id, p in BOT_PROFILES.items():
    os.makedirs(f"{bot_id}", exist_ok=True)
    with open(f"{bot_id}/index.html", "w", encoding="utf-8") as f:
        f.write(DETAIL_TMPL.format(
            bot_id=bot_id, name=p["display_name"], color=p["color"],
            avatar=p["avatar"], bio=p["bio"], strategy=p["strategy"],
            risk_level=p["risk_level"], risk_bar=p["risk_bar"],
            model=p.get("model", "gemini"),
            fallback_model=p.get("fallback_model", ""),
            watchlist=json.dumps(p["watchlist"]),
            max_position_pct=p["max_position_pct"],
            max_trades=p["max_trades_per_session"],
            min_cash=p["min_cash_reserve"],
        ))
    os.makedirs(f"{bot_id}/records", exist_ok=True)
    with open(f"{bot_id}/records/index.html", "w", encoding="utf-8") as f:
        f.write(RECORDS_TMPL.format(
            bot_id=bot_id, name=p["display_name"], color=p["color"], avatar=p["avatar"],
        ))
    count += 1

# Copy sentinel page
# shutil.copy("sentinel.html", "sentinel/index.html")
# print(f"✅ Sentinell page generated")

print(f"\n{count} bots × 2 pages = {count*2} HTML files + sentinel.html generated.")
