#!/usr/bin/env python3
"""Update all i18n locale files with new subtitle text"""
import os, json

base = "/mnt/c/Hermes/paper_trading/assets/i18n"
langs = ["en.json", "tc.json", "sc.json", "ja.json", "fr.json", "es.json"]

for lang in langs:
    path = os.path.join(base, lang)
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    
    c = c.replace(
        '"page_sub_trade": "20 AI bots \u00b7 $10,000 each \u00b7 Real market data \u00b7 Transparent decisions"',
        '"page_sub_trade": "Browse 20 bots \u2192 Click any to see trades, strategy & portfolio"'
    )
    c = c.replace(
        '"page_sub_sentinel": "Crowd sentiment dashboard"',
        '"page_sub_sentinel": "Switch tabs: Crypto prices \u00b7 Stock indices \u00b7 ETF outlooks \u00b7 Predictions"'
    )
    c = c.replace(
        '"page_sub_polymarket": "AI-powered prediction market analysis \u00b7 High-confidence bet finder"',
        '"page_sub_polymarket": "\U0001f3c6 Top pick first \u2192 Filter by category \u2192 Click for AI analysis"'
    )
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"  {lang}: updated")
