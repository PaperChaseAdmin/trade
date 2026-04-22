"""Generate thin HTML wrapper pages for all bots."""
import os, json
from bot_profiles import BOT_PROFILES

DETAIL_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{name} · PaperChase Trading Arena</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">Paper<span>Chase</span></a>
  <div class="topbar-nav">
    <a class="nav-link" href="/trade/">Leaderboard</a>
    <a class="nav-link" href="/market-sentinel/">Market Sentinel</a>
    <a class="nav-link" href="/">Home</a>
  </div>
</div></nav>
<div class="container">
  <a class="back-link" href="/trade/">← All Bots</a>
  <div id="loading">Loading {name}...</div>
  <div id="app">
    <div id="hero"></div>
    <div id="outlook"></div>
    <div id="specs"></div>
    <div id="follow"></div>
    <div class="chart-card" id="chart-wrap"><canvas id="chart"></canvas></div>
    <div class="section-label">Current Positions</div>
    <div id="positions" style="margin-bottom:24px"></div>
    <div class="section-label">Recent Trades</div>
    <div id="trades"></div>
    <div class="page-footer">
      <a class="footer-link" href="/trade/">← Leaderboard</a>
      <a class="footer-link" href="/trade/{bot_id}/records/">Full Records →</a>
      <a class="footer-link" href="/market-sentinel/">Market Sentinel</a>
    </div>
  </div>
</div>
<script>
const BOT_ID='{bot_id}',BOT_COLOR='{color}',BOT_NAME='{name}';
const BOT_AVATAR='{avatar}',BOT_BIO='{bio}',BOT_STRATEGY='{strategy}';
const BOT_RISK='{risk_level}',BOT_RISK_BAR={risk_bar};
const BOT_WATCHLIST={watchlist};
const BOT_MAX_POSITION={max_position_pct},BOT_MAX_TRADES={max_trades},BOT_MIN_CASH={min_cash};
</script>
<script src="/trade/assets/bot-detail.js"></script>
</body></html>
"""

RECORDS_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{name} Records · PaperChase</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
</head>
<body>
<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">Paper<span>Chase</span></a>
  <div class="topbar-nav">
    <a class="nav-link" href="/trade/">Leaderboard</a>
    <a class="nav-link" href="/market-sentinel/">Market Sentinel</a>
  </div>
</div></nav>
<div class="container">
  <a class="back-link" href="/trade/{bot_id}/">← <span id="bot-avatar"></span> <span id="bot-name"></span></a>
  <div class="page-header">
    <div class="page-title" style="color:{color}">{avatar} {name} — Trade Records</div>
    <div class="page-sub">Complete history · All times UTC</div>
  </div>
  <div id="stats"></div>
  <div class="filters">
    <button class="filter-btn active" onclick="setFilter('all',this)">All</button>
    <button class="filter-btn" onclick="setFilter('BUY',this)">Buys</button>
    <button class="filter-btn" onclick="setFilter('SELL',this)">Sells</button>
    <span class="filter-count" id="count"></span>
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
    # Bot detail page
    os.makedirs(f"{bot_id}", exist_ok=True)
    with open(f"{bot_id}/index.html", "w", encoding="utf-8") as f:
        f.write(DETAIL_TMPL.format(
            bot_id=bot_id, name=p["display_name"], color=p["color"],
            avatar=p["avatar"], bio=p["bio"], strategy=p["strategy"],
            risk_level=p["risk_level"], risk_bar=p["risk_bar"],
            watchlist=json.dumps(p["watchlist"]),
            max_position_pct=p["max_position_pct"],
            max_trades=p["max_trades_per_session"],
            min_cash=p["min_cash_reserve"]
        ))

    # Records page
    os.makedirs(f"{bot_id}/records", exist_ok=True)
    with open(f"{bot_id}/records/index.html", "w", encoding="utf-8") as f:
        f.write(RECORDS_TMPL.format(
            bot_id=bot_id, name=p["display_name"], color=p["color"], avatar=p["avatar"]
        ))
    count += 1
    print(f"  OK {p['display_name']}")

print(f"\n{count} bots × 2 pages = {count*2} HTML files generated.")
