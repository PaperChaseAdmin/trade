"""Generate HTML wrapper pages + Market Sentinel page."""
import os, json, shutil
from bot_profiles import BOT_PROFILES

def escape_js(text):
    """Replace { and } with safe placeholders that don't interfere with .format()"""
    return text.replace('{', 'LBRACE').replace('}', 'RBRACE')

def unescape_js(text):
    return text.replace('LBRACE', '{').replace('RBRACE', '}')

DETAIL_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>BOTNAME · AI Trading Bot · PaperChase</title>
<meta name="description" content="Watch BOTNAME, an AI-powered trading bot with a BOTSTRATEGY strategy. Real portfolio, live trades, transparent AI decisions on PaperChase."/>
<meta name="robots" content="index, follow"/>
<link rel="canonical" href="https://paperchase.online/trade/BOTID/"/>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-W3V49QCMT0"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-W3V49QCMT0');
</script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
<script src="/trade/assets/i18n.js"></script>
<script src="/trade/assets/supabase-client.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
  const BOT_ID='BOTID',BOT_COLOR='BOTCOLOR',BOT_NAME='BOTNAME';
  const BOT_AVATAR='BOTAVATAR',BOT_BIO='BOTBIO',BOT_STRATEGY='BOTSTRATEGY';
  const BOT_RISK='BOTRISK',BOT_RISK_BAR=BOTRISKBAR;
  const BOT_MODEL='BOTMODEL',BOT_FALLBACK='BOTFALLBACK';
  const BOT_WATCHLIST=BOTWATCHLIST;
  const BOT_MAX_POSITION=BOTMAXPOSITION,BOT_MAX_TRADES=BOTMAXTRADES,BOT_MIN_CASH=BOTMINCASH;
</script>
</head>
<body>
<div class="bg-overlay"></div>

<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">PaperChase</a>
  <div class="topbar-nav">
    <a class="nav-link" href="/" data-i18n="nav_home">Home</a>
    <a class="nav-link active" href="/trade/" data-i18n="nav_trading">AI Trading</a>
    <a class="nav-link" href="/market-sentinel/" data-i18n="nav_sentinel">Market Sentinel</a>
    <a class="nav-link" href="/trade/polymarket/" data-i18n="nav_polymarket">Polymarket</a>
  </div>
  <div style="flex:1"></div>
  <div class="lang-switcher" style="position:relative">
    <button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="background:var(--tv-surface-2);border:1px solid var(--tv-border-2);border-radius:var(--tv-radius-sm);padding:4px 10px;cursor:pointer;font-size:12px;color:var(--tv-text-2);font-family:var(--tv-font)">🌐 <span data-i18n="nav_lang">Language</span> ▾</button>
    <div style="display:none;position:absolute;top:100%;right:0;background:var(--tv-surface);border:1px solid var(--tv-border);border-radius:var(--tv-radius-sm);min-width:150px;z-index:200;margin-top:4px;overflow:hidden">
      <div onclick="localStorage.setItem('pap_tfav_lang','en');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇬🇧 <span data-i18n="lang_en">English</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','tc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇭🇰 <span data-i18n="lang_tc">繁體中文</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','sc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇨🇳 <span data-i18n="lang_sc">简体中文</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','ja');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇯🇵 <span data-i18n="lang_ja">日本語</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','fr');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇫🇷 <span data-i18n="lang_fr">Français</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','es');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇪🇸 <span data-i18n="lang_es">Español</span></div>
    </div>
  </div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login" id="nav-login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register" id="nav-register">Register</a>
  <a class="nav-link" href="/trade/account/" data-i18n="nav_account" id="nav-account" style="display:none">Account</a>
  <a class="nav-link" href="#" onclick="if(window.PaperChaseAuth)PaperChaseAuth.signOut()" data-i18n="nav_logout" id="nav-logout" style="display:none">Log Out</a>
</div></nav>
<script>
function switchLang(lang) {
  if (window.__setLang) window.__setLang(lang);
}
</script>
<div class="container">
  <a class="back-link" href="/trade/" data-i18n="nav_all_bots">← All Bots</a>
  <div class="favourite-bar" style="display:flex;justify-content:flex-end;align-items:center;padding:8px 0">
    <button id="favBtn" class="fav-btn" onclick="toggleFavourite()" style="background:none;border:1px solid var(--tv-border-2,#363a45);border-radius:var(--tv-radius-sm,4px);padding:6px 12px;cursor:pointer;font-size:13px;color:var(--tv-text-2,#787b86);display:none">
      <span id="favIcon">&#9734;</span> <span id="favLabel" data-i18n="favourite_add">Add to Favourites</span>
    </button>
  </div>
  <div id="loading" style="text-align:center;padding:40px;color:var(--tv-text-2)" data-i18n="loading_bot">Loading BOTNAME...</div>
  <div id="app" style="display:none">
    <div id="hero"></div>
    <div id="outlook"></div>
    <div id="prices-bar"></div>
    <div id="last-session"></div>
    <div id="specs"></div>
    <div id="session-chart"></div>
    <div id="positions-section"></div>
    <div id="trades-section"></div>
  </div>
  <a href="/trade/BOTID/records/" class="nav-link" style="display:inline-block;margin-top:12px" data-i18n="nav_full_records">&#128196; Full Trade Records</a>
</div>

<script src="/trade/assets/bot-detail.js"></script>
<script>
async function checkFavStatus() {
  if (!window.PaperChaseAuth) return;
  var session = await PaperChaseAuth.getSession();
  var btn = document.getElementById('favBtn');
  if (!btn) return;
  if (!session) { btn.style.display = 'none'; return; }
  btn.style.display = '';
  var isFav = await PaperChaseAuth.isFavourite(BOT_ID);
  document.getElementById('favIcon').textContent = isFav ? '\u2605' : '\u2606';
  document.getElementById('favLabel').textContent = isFav ? 'Remove from Favourites' : 'Add to Favourites';
}
async function toggleFavourite() {
  if (!window.PaperChaseAuth) return;
  var session = await PaperChaseAuth.getSession();
  if (!session) { alert('Please log in to add favourites.'); return; }
  var isFav = await PaperChaseAuth.isFavourite(BOT_ID);
  if (isFav) {
    await PaperChaseAuth.removeFavourite(BOT_ID);
  } else {
    await PaperChaseAuth.addFavourite(BOT_ID, BOT_NAME, BOT_AVATAR);
  }
  checkFavStatus();
}
checkFavStatus();
</script>
<script>
document.addEventListener('i18nReady', function () {
  if (window.__retranslate) window.__retranslate();
});
</script>
</body></html>
"""

RECORDS_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>BOTNAME Trade Records · PaperChase</title>
<meta name="description" content="Complete trade history for BOTNAME AI trading bot on PaperChase."/>
<meta name="robots" content="index, follow"/>
<link rel="canonical" href="https://paperchase.online/trade/BOTID/records/"/>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-W3V49QCMT0"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-W3V49QCMT0');
</script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"/>
<link rel="stylesheet" href="/trade/assets/style.css"/>
<script src="/trade/assets/i18n.js"></script>
</head>
<body>
<div class="bg-overlay"></div>

<nav class="topbar"><div class="topbar-inner">
  <a class="logo" href="/trade/">PaperChase</a>
  <div class="topbar-nav">
    <a class="nav-link" href="/" data-i18n="nav_home">Home</a>
    <a class="nav-link active" href="/trade/" data-i18n="nav_trading">AI Trading</a>
    <a class="nav-link" href="/market-sentinel/" data-i18n="nav_sentinel">Market Sentinel</a>
    <a class="nav-link" href="/trade/polymarket/" data-i18n="nav_polymarket">Polymarket</a>
  </div>
  <div style="flex:1"></div>
  <div class="lang-switcher" style="position:relative">
    <button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="background:var(--tv-surface-2);border:1px solid var(--tv-border-2);border-radius:var(--tv-radius-sm);padding:4px 10px;cursor:pointer;font-size:12px;color:var(--tv-text-2);font-family:var(--tv-font)">&#127760; <span data-i18n="nav_lang">Language</span> &#9662;</button>
    <div style="display:none;position:absolute;top:100%;right:0;background:var(--tv-surface);border:1px solid var(--tv-border);border-radius:var(--tv-radius-sm);min-width:150px;z-index:200;margin-top:4px;overflow:hidden">
      <div onclick="localStorage.setItem('pap_tfav_lang','en');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127468;&#127463; <span data-i18n="lang_en">English</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','tc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127472;&#127475; <span data-i18n="lang_tc">Traditional Chinese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','sc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127464;&#127475; <span data-i18n="lang_sc">Simplified Chinese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','ja');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127471;&#127477; <span data-i18n="lang_ja">Japanese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','fr');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127467;&#127479; <span data-i18n="lang_fr">French</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','es');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127466;&#127480; <span data-i18n="lang_es">Spanish</span></div>
    </div>
  </div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register">Register</a>
</div></nav>
<div class="container">
  <a class="back-link" href="/trade/BOTID/" data-i18n="records_back_to_bot">&#8592; BOTAVATAR BOTNAME</a>
  <div class="page-header">
    <div class="page-title-wrap">
      <div class="page-title" data-i18n="records_title">BOTAVATAR BOTNAME &#8212; Trade Records</div>
      <div class="page-sub" data-i18n="records_subtitle">Complete history &#183; All times UTC</div>
    </div>
  </div>
  <div id="stats" class="stats-grid" style="grid-template-columns:repeat(4,1fr)"></div>
  <div style="display:flex;gap:8px;margin-bottom:12px">
    <button class="nav-link active" onclick="setFilter('all',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface);color:var(--tv-text)" data-i18n="records_filter_all">All</button>
    <button class="nav-link" onclick="setFilter('buy',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface);color:var(--tv-text)" data-i18n="records_filter_buys">Buys</button>
    <button class="nav-link" onclick="setFilter('sell',this)" style="cursor:pointer;border:none;font-size:12px;background:var(--tv-surface);color:var(--tv-text)" data-i18n="records_filter_sells">Sells</button>
  </div>
  <div id="records-list"></div>
</div>

<script>
  const BOT_ID='BOTID',BOT_COLOR='BOTCOLOR',BOT_NAME='BOTNAME',BOT_AVATAR='BOTAVATAR';
</script>
<script src="/trade/assets/records.js"></script>
<script>
document.addEventListener('i18nReady', function () {
  if (window.__retranslate) window.__retranslate();
});
</script>
</body></html>
"""

# ── GENERATE ──
count = 0
for bot_id, p in BOT_PROFILES.items():
    os.makedirs(f"{bot_id}", exist_ok=True)
    
    replacements = {
        'BOTID': bot_id,
        'BOTNAME': p["display_name"],
        'BOTCOLOR': p["color"],
        'BOTAVATAR': p["avatar"],
        'BOTBIO': p["bio"],
        'BOTSTRATEGY': p["strategy"],
        'BOTRISK': p["risk_level"],
        'BOTRISKBAR': str(p["risk_bar"]),
        'BOTMODEL': p.get("model", "gemini"),
        'BOTFALLBACK': p.get("fallback_model", ""),
        'BOTWATCHLIST': str(p["watchlist"]),
        'BOTMAXPOSITION': str(p["max_position_pct"]),
        'BOTMAXTRADES': str(p["max_trades_per_session"]),
        'BOTMINCASH': str(p["min_cash_reserve"]),
    }
    
    html = DETAIL_TMPL
    for k, v in replacements.items():
        html = html.replace(k, v)
    
    with open(f"{bot_id}/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    os.makedirs(f"{bot_id}/records", exist_ok=True)
    
    rec_html = RECORDS_TMPL
    rec_replacements = {
        'BOTID': bot_id,
        'BOTNAME': p["display_name"],
        'BOTCOLOR': p["color"],
        'BOTAVATAR': p["avatar"],
    }
    for k, v in rec_replacements.items():
        rec_html = rec_html.replace(k, v)
    
    with open(f"{bot_id}/records/index.html", "w", encoding="utf-8") as f:
        f.write(rec_html)
    
    count += 1

print(f"\n{count} bots × 2 pages = {count*2} HTML files generated")
