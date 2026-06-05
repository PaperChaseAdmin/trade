#!/usr/bin/env python3
"""Add countdown to Poly Watch"""
with open("/mnt/c/Hermes/paper_trading/polymarket/index.html") as f:
    c = f.read()

# Countdown function code (from Trading Arena)
cd_fn = r"""
let _cdTimer = null;

function startCountdown() {
  clearInterval(_cdTimer);
  const el = document.getElementById('countdown-wrap');
  if (!el) return;
  
  function nextMarketOpen() {
    const now = new Date();
    const day = now.getUTCDay();
    const hour = now.getUTCHours();
    const min = now.getUTCMinutes();
    const next = new Date(now);
    
    if (day === 0 || day === 6 || (day === 5 && hour >= 21)) {
      const daysUntilMonday = day === 0 ? 1 : day === 6 ? 2 : (8 - day);
      next.setDate(next.getDate() + daysUntilMonday);
      next.setUTCHours(13, 30, 0, 0);
    } else if (hour < 13 || (hour === 13 && min < 30)) {
      next.setUTCHours(13, 30, 0, 0);
    } else if (hour >= 21) {
      next.setDate(next.getDate() + 1);
      next.setUTCHours(13, 30, 0, 0);
    } else {
      const nextHalf = Math.ceil((hour * 60 + min) / 30) * 30;
      next.setUTCHours(Math.floor(nextHalf/60), nextHalf%60, 0, 0);
    }
    return next;
  }
  
  const target = nextMarketOpen();
  
  function tick() {
    const diff = target - Date.now();
    if (diff <= 0) { el.innerHTML = '<span class="countdown-lbl" data-i18n="next_review">Next Review</span><span class="countdown-num" data-i18n="checking_now">Checking now...</span>'; __retranslate(); return; }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    
    if (h >= 24) {
      const d = Math.floor(h / 24);
      el.innerHTML = '<span class="countdown-lbl" data-i18n="next_review">Next Review</span><span class="countdown-num">' + d + 'd ' + (h%24) + 'h ' + m + 'm</span>';
    } else if (h >= 1) {
      el.innerHTML = '<span class="countdown-lbl" data-i18n="next_review">Next Review</span><span class="countdown-num">' + h + 'h ' + m + 'm ' + s + 's</span>';
    } else {
      el.innerHTML = '<span class="countdown-lbl" data-i18n="next_review">Next Review</span><span class="countdown-num">' + m + 'm ' + s + 's</span>';
    }
  }
  tick();
  _cdTimer = setInterval(tick, 1000);
}

"""

# Insert before renderPredHist
c = c.replace("function renderPredHist(history) {", cd_fn + "function renderPredHist(history) {")

# Verify startCountdown() call already exists
if "startCountdown();" not in c:
    c = c.replace(
        "renderTopPick(allMarkets);\n    \n    // Load prediction history",
        "renderTopPick(allMarkets);\n    startCountdown();\n    \n    // Load prediction history")

with open("/mnt/c/Hermes/paper_trading/polymarket/index.html", "w") as f:
    f.write(c)

# Verify
with open("/mnt/c/Hermes/paper_trading/polymarket/index.html") as f:
    final = f.read()
print(f"startCountdown function: {'function startCountdown' in final}")
print(f"startCountdown() call: {'startCountdown();' in final}")
print(f"_cdTimer declared: {'let _cdTimer' in final}")
print(f"container 80px: {'padding:0 20px 80px}' in final}")
print(f"page-header fixed: {'padding:28px 0 0;display' in final}")
