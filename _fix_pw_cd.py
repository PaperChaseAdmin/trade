#!/usr/bin/env python3
"""Add countdown function to Poly Watch"""
path = "/mnt/c/Hermes/paper_trading/polymarket/index.html"
with open(path) as f:
    c = f.read()

# Read countdown function from Trading Arena
with open("/mnt/c/Hermes/paper_trading/index.html") as f2:
    ta = f2.read()

# Extract countdown function code (lines between 'function startCountdown' and the closing brace before the next function)
import re
m = re.search(r'(let _cdTimer = null;.*?function startCountdown\(\) \{.*?\n\})', ta, re.DOTALL)
if m:
    cd_code = m.group(1)
    print(f"Countdown function: {len(cd_code)} chars")
else:
    print("ERROR: Could not extract countdown function")
    exit(1)

# Insert before renderPredHist
c = c.replace(
    "function renderPredHist(history) {",
    cd_code + "\n\n\nfunction renderPredHist(history) {")

# Add startCountdown() call after renderTopPick
if "startCountdown();" not in c:
    c = c.replace(
        "renderTopPick(allMarkets);\n    \n    // Load prediction history",
        "renderTopPick(allMarkets);\n    startCountdown();\n    \n    // Load prediction history")

with open(path, "w") as f:
    f.write(c)

# Verify
with open(path) as f:
    final = f.read()
print(f"startCountdown function: {'function startCountdown' in final}")
print(f"startCountdown() call: {'startCountdown();' in final}")
print(f"_cdTimer: {'let _cdTimer' in final}")
