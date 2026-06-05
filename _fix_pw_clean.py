#!/usr/bin/env python3
with open("/mnt/c/Hermes/paper_trading/polymarket/index.html") as f:
    c = f.read()

# 1. Fix container padding
c = c.replace(
    ".container{max-width:1200px;margin:0 auto;padding:0 20px 60px}",
    ".container{max-width:1200px;margin:0 auto;padding:0 20px 80px}")

# 2. Fix page-header padding
c = c.replace(
    "padding:28px 0 20px;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px",
    "padding:28px 0 0;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px")

# 3. Change subtitle
c = c.replace(
    '<div class="page-sub" data-i18n="page_sub_polymarket">AI-powered prediction market analysis \u00b7 High-confidence bet finder</div>',
    '<div class="page-sub" style="font-size:12px;color:var(--tv-text-2)"><span class="live"></span> \U0001f3c6 Top pick shown first \u2192 Filter by category \u2192 Click any market for AI analysis</div>')

with open("/mnt/c/Hermes/paper_trading/polymarket/index.html", "w") as f:
    f.write(c)
print("CSS + subtitle fixed")
