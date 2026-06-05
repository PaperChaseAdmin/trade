#!/usr/bin/env python3
"""Fix Poly Watch: add countdown, unify padding"""
import re

path = "/mnt/c/Hermes/paper_trading/polymarket/index.html"
with open(path) as f:
    c = f.read()

# 1. Fix container padding: 60px -> 80px
c = c.replace(
    '.container{max-width:1200px;margin:0 auto;padding:0 20px 60px}',
    '.container{max-width:1200px;margin:0 auto;padding:0 20px 80px}')

# 2. Fix page-header: padding:28px 0 20px -> padding:28px 0 0
c = c.replace(
    'padding:28px 0 20px;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px',
    'padding:28px 0 0;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:20px')

# 3. Add startCountdown function from Trading Arena
# Read the Trading Arena countdown code
with open("/mnt/c/Hermes/paper_trading/index.html") as f2:
    ta = f2.read()

cd_start = ta.find("// ── Countdown")
cd_end = ta.find("\nfunction renderPredHist", ta.find("// ── Countdown"))
if cd_end < 0:
    cd_end = ta.find("// Initial load", cd_start)
cd_code = ta[cd_start:cd_end]

# Insert countdown code before renderPredHist
c = c.replace(
    "function renderPredHist(history) {",
    cd_code.strip() + "\n\n\nfunction renderPredHist(history) {")

# 4. Add startCountdown() call in loadData
c = c.replace(
    "renderTopPick(allMarkets);\n    startCountdown();",
    "renderTopPick(allMarkets);")
c = c.replace(
    "renderTopPick(allMarkets);\n    \n    // Load prediction history",
    "renderTopPick(allMarkets);\n    startCountdown();\n    \n    // Load prediction history")

with open(path, "w") as f:
    f.write(c)

# Verify
with open(path) as f:
    final = f.read()
print(f"startCountdown: {'✅' if 'function startCountdown' in final else '❌'}")
print(f"container 80px: {'✅' if 'padding:0 20px 80px}' in final else '❌'}")
print(f"page-header padding: {'✅' if 'padding:28px 0 0;display' in final else '❌'}")
print(f"startCountdown() call: {'✅' if 'startCountdown();' in final else '❌'}")
print(f"File size: {len(final)} bytes")
