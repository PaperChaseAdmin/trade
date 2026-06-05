#!/usr/bin/env python3
"""Fix Poly Watch: add countdown, unify padding, change subtitle"""
import re

# === POLY WATCH ===
path = "/mnt/c/Hermes/paper_trading/polymarket/index.html"
with open(path) as f:
    c = f.read()

# 1. Container padding 60->80
c = c.replace(
    ".container{max-width:1200px;margin:0 auto;padding:0 20px 60px}",
    ".container{max-width:1200px;margin:0 auto;padding:0 20px 80px}")
print("1. Container padding: done")

# 2. Page-header padding
c = c.replace(
    "padding:28px 0 20px;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px",
    "padding:28px 0 0;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px")
print("2. Page-header padding: done")

# 3. Subtitle
c = c.replace(
    'AI-powered prediction market analysis \u00b7 High-confidence bet finder',
    '\U0001f3c6 Top pick shown first \u2192 Filter by category \u2192 Click any market for AI analysis')
print("3. Subtitle: done")

# 4. Add countdown function
cd_code = """
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

c = c.replace("function renderPredHist(history) {", cd_code + "\n\nfunction renderPredHist(history) {")
print("4. Countdown function: done")

# 5. Add startCountdown() call
if "startCountdown();" not in c:
    c = c.replace(
        "renderTopPick(allMarkets);\n    \n    // Load prediction history",
        "renderTopPick(allMarkets);\n    startCountdown();\n    \n    // Load prediction history")
print("5. startCountdown() call: done")

with open(path, "w") as f:
    f.write(c)

# Verify
print("\n=== Verification ===")
for check in ["function startCountdown", "startCountdown();", "let _cdTimer",
               "padding:0 20px 80px", "padding:28px 0 0;display",
               "Top pick shown first"]:
    with open(path) as f:
        print(f"  {check}: {'OK' if check in f.read() else 'MISSING'}")

# === TRADING ARENA ===
ta_path = "/mnt/c/Hermes/paper_trading/index.html"
with open(ta_path) as f:
    ta = f.read()

# 1. Add .wrap div
if '<div class="wrap">' not in ta:
    ta = ta.replace(
        '<div class="bg-overlay"></div>\n\n<nav class="topbar">',
        '<div class="bg-overlay"></div>\n<div class="wrap">\n<nav class="topbar">')
    ta = ta.replace('</body>', '</div>\n</body>')
    print("\nTrading Arena .wrap: done")

# 2. Add wrap CSS
if '.wrap{position:relative;z-index:1}' not in ta:
    ta = ta.replace(
        'body{background:var(--tv-bg);color:var(--tv-text);',
        'body{background:var(--tv-bg);color:var(--tv-text);.wrap{position:relative;z-index:1}')
    print("Trading Arena wrap CSS: done")

# 3. Page-header padding
if 'padding:28px 0 0' not in ta:
    ta = ta.replace(
        '<div class="page-header">',
        '<div class="page-header" style="padding:28px 0 0">')
    print("Trading Arena page-header: done")

# 4. Change subtitle
ta = ta.replace(
    '20 AI bots \u00b7 $10,000 each \u00b7 Real market data \u00b7 Transparent decisions',
    'Browse 20 AI bots \u2192 Click any to see trades, strategy & live portfolio')
print("Trading Arena subtitle: done")

with open(ta_path, "w") as f:
    f.write(ta)

# Verify Trading Arena
print("\n=== Trading Arena Verification ===")
for check in ['<div class="wrap">', "padding:28px 0 0",
              "Browse 20 AI bots"]:
    with open(ta_path) as f:
        print(f"  {check}: {'OK' if check in f.read() else 'MISSING'}")
