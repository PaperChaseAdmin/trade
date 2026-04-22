#!/usr/bin/env python3
"""
PaperChase Trading Bot Runner
Executes AI paper trading bots during US market hours.
Each bot independently analyses market data and makes trading decisions via Groq LLM.
"""

import os
import json
import requests
import yfinance as yf
from datetime import datetime, date
import pytz
from groq import Groq
from bot_profiles import BOT_PROFILES
import time
import random

# ─── Constants ────────────────────────────────────────────────────────────────
DATA_DIR = "data/bots"
LEADERBOARD_FILE = "data/leaderboard.json"
MARKET_SENTINEL_URL = "https://paperchase.online/market-sentinel/data/market_data.json"
ET = pytz.timezone("America/New_York")


# ─── Market Hours ─────────────────────────────────────────────────────────────
def is_market_open() -> bool:
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    open_t  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_t <= now <= close_t


# ─── Data Fetching ────────────────────────────────────────────────────────────
def get_stock_prices(tickers: list) -> dict:
    """Fetch latest prices for a list of tickers using yfinance."""
    prices = {}
    if not tickers:
        return prices

    # yfinance handles BRK-B fine; download all at once
    ticker_str = " ".join(tickers)
    try:
        data = yf.download(
            ticker_str,
            period="1d",
            interval="5m",
            progress=False,
            auto_adjust=True,
            threads=True
        )
        if data.empty:
            raise ValueError("Empty data returned")

        close = data["Close"] if "Close" in data.columns else data
        if len(tickers) == 1:
            last = close.dropna().iloc[-1]
            prices[tickers[0]] = round(float(last), 4)
        else:
            for t in tickers:
                try:
                    last = close[t].dropna().iloc[-1]
                    prices[t] = round(float(last), 4)
                except Exception:
                    pass
    except Exception as e:
        print(f"  ⚠ yfinance batch error: {e}. Trying individually...")
        for t in tickers:
            try:
                d = yf.Ticker(t).history(period="1d", interval="5m")
                if not d.empty:
                    prices[t] = round(float(d["Close"].iloc[-1]), 4)
                time.sleep(0.3)
            except Exception:
                pass
    return prices


def get_market_data() -> dict:
    """Fetch Market Sentinel sentiment data."""
    try:
        r = requests.get(MARKET_SENTINEL_URL, timeout=15)
        return r.json()
    except Exception as e:
        print(f"  ⚠ Market Sentinel unavailable: {e}")
        return {}


# ─── Portfolio I/O ────────────────────────────────────────────────────────────
def load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)

def save_json(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def portfolio_path(bot_id): return f"{DATA_DIR}/{bot_id}/portfolio.json"
def trades_path(bot_id):    return f"{DATA_DIR}/{bot_id}/trades.json"


# ─── Portfolio Calculations ───────────────────────────────────────────────────
def calc_value(portfolio: dict, prices: dict) -> float:
    total = portfolio["cash"]
    for ticker, pos in portfolio["positions"].items():
        p = prices.get(ticker, pos.get("current_price", pos["avg_cost"]))
        total += pos["shares"] * p
    return round(total, 2)

def sync_prices(portfolio: dict, prices: dict):
    for ticker in portfolio["positions"]:
        if ticker in prices:
            portfolio["positions"][ticker]["current_price"] = prices[ticker]


# ─── Trade Execution ──────────────────────────────────────────────────────────
def execute_trade(portfolio: dict, trade: dict, prices: dict, profile: dict):
    """Execute a single paper trade. Returns (record, error_str)."""
    ticker  = str(trade.get("ticker", "")).upper().strip()
    action  = str(trade.get("action",  "")).upper().strip()
    shares  = int(trade.get("shares",  0))

    if not ticker or action not in ("BUY", "SELL") or shares <= 0:
        return None, f"Invalid trade: {trade}"

    price = prices.get(ticker)
    if not price:
        return None, f"No price for {ticker}"

    total_val   = calc_value(portfolio, prices)
    max_pos_val = total_val * profile["max_position_pct"]
    min_cash    = profile["min_cash_reserve"]

    if action == "BUY":
        available = portfolio["cash"] - min_cash
        if available <= 0:
            return None, "Below cash reserve limit"

        # Enforce position-size cap
        existing_val = portfolio["positions"].get(ticker, {}).get("shares", 0) * price
        room = max_pos_val - existing_val
        if room <= 0:
            return None, f"Position cap reached for {ticker}"
        shares = min(shares, int(min(room, available) / price))
        if shares <= 0:
            return None, "After sizing, 0 shares available"

        cost = round(shares * price, 2)
        portfolio["cash"] = round(portfolio["cash"] - cost, 2)

        if ticker in portfolio["positions"]:
            old = portfolio["positions"][ticker]
            new_shares = old["shares"] + shares
            avg = (old["shares"] * old["avg_cost"] + shares * price) / new_shares
            portfolio["positions"][ticker] = {
                "shares": new_shares,
                "avg_cost": round(avg, 4),
                "current_price": price
            }
        else:
            portfolio["positions"][ticker] = {
                "shares": shares,
                "avg_cost": round(price, 4),
                "current_price": price
            }

    elif action == "SELL":
        pos = portfolio["positions"].get(ticker)
        if not pos:
            return None, f"No position in {ticker}"
        shares = min(shares, pos["shares"])
        proceeds = round(shares * price, 2)
        portfolio["cash"] = round(portfolio["cash"] + proceeds, 2)
        if shares >= pos["shares"]:
            del portfolio["positions"][ticker]
        else:
            portfolio["positions"][ticker]["shares"] -= shares

    return {
        "action":      action,
        "ticker":      ticker,
        "shares":      shares,
        "price":       price,
        "total_value": round(shares * price, 2),
        "reasoning":   str(trade.get("reasoning", ""))[:300]
    }, None


# ─── LLM Decision ─────────────────────────────────────────────────────────────
def get_decision(bot_id: str, profile: dict, portfolio: dict,
                 prices: dict, market_data: dict) -> dict:
    """Ask Groq to make a trading decision for this bot."""

    total_val  = calc_value(portfolio, prices)
    return_pct = (total_val - profile["initial_capital"]) / profile["initial_capital"] * 100

    # Build positions display with unrealised P&L
    pos_display = {}
    for t, pos in portfolio["positions"].items():
        cur = prices.get(t, pos.get("current_price", pos["avg_cost"]))
        pnl = (cur - pos["avg_cost"]) * pos["shares"]
        pos_display[t] = {
            "shares":       pos["shares"],
            "avg_cost":     pos["avg_cost"],
            "current":      cur,
            "unrealised_pnl": round(pnl, 2),
            "pnl_pct":      round((cur - pos["avg_cost"]) / pos["avg_cost"] * 100, 2)
        }

    # Market Sentinel summary
    stocks  = market_data.get("stocks",  {})
    crypto  = market_data.get("crypto",  {})
    fg      = crypto.get("fear_greed",   {})
    indices = stocks.get("indices",      []) or []
    news    = stocks.get("news",         []) or []

    sp500_chg, vix_val = None, None
    for idx in indices:
        if idx.get("symbol") == "^GSPC":
            sp500_chg = idx.get("change_pct")
        elif idx.get("symbol") == "^VIX":
            vix_val = idx.get("price")

    headlines = [n.get("title","") for n in news[:4]]
    trending  = [m.get("ticker","") for m in (stocks.get("top_mentioned") or [])[:5]]

    # Available watchlist prices
    avail_prices = {t: prices[t] for t in profile["watchlist"] if t in prices}

    prompt = f"""You are {profile['display_name']}, a paper trader on the PaperChase Trading Arena.

PERSONALITY & STRATEGY:
{profile['prompt_persona']}

YOUR PORTFOLIO (right now):
  Cash:           ${portfolio['cash']:.2f}
  Total Value:    ${total_val:.2f}  (started at ${profile['initial_capital']:,})
  Overall Return: {return_pct:+.2f}%

CURRENT POSITIONS:
{json.dumps(pos_display, indent=2) if pos_display else "  None (all cash)"}

WATCHLIST LIVE PRICES:
{json.dumps(avail_prices, indent=2)}

MARKET CONDITIONS (from Market Sentinel):
  Fear & Greed Index : {fg.get('value','N/A')} — {fg.get('value_classification','N/A')}
  Market Mood        : {stocks.get('market_mood','N/A')}
  S&P 500 today      : {sp500_chg}%
  VIX                : {vix_val}
  Trending stocks    : {', '.join(str(t) for t in trending)}
  Top headlines      : {' | '.join(headlines[:3])}

HARD RULES (you must obey):
  1. Only BUY from your watchlist: {', '.join(profile['watchlist'])}
  2. Max {int(profile['max_position_pct']*100)}% of total portfolio in any one stock
  3. Always keep ≥ ${profile['min_cash_reserve']} cash
  4. Maximum {profile['max_trades_per_session']} trades this session
  5. You can only trade stocks with prices listed above

Decide: BUY, SELL, or do nothing. Be true to your personality.

Reply ONLY with valid JSON (no markdown, no explanation outside JSON):
{{
  "trades": [
    {{"action": "BUY", "ticker": "TSLA", "shares": 5, "reasoning": "one sentence"}},
    {{"action": "SELL", "ticker": "NVDA", "shares": 3, "reasoning": "one sentence"}}
  ],
  "market_outlook": "one sentence on your current view"
}}
If no trades: {{"trades": [], "market_outlook": "..."}}"""

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.75,
        max_tokens=900,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)


# ─── Leaderboard Update ───────────────────────────────────────────────────────
def update_leaderboard(all_data: list):
    bots = []
    for portfolio, profile in all_data:
        val     = portfolio["total_value"]
        initial = profile["initial_capital"]
        ret_pct = (val - initial) / initial * 100
        bots.append({
            "bot_id":          profile["bot_id"],
            "display_name":    profile["display_name"],
            "avatar":          profile["avatar"],
            "bio":             profile["bio"],
            "strategy":        profile["strategy"],
            "risk_level":      profile["risk_level"],
            "risk_bar":        profile["risk_bar"],
            "color":           profile["color"],
            "total_value":     val,
            "initial_capital": initial,
            "total_return_pct": round(ret_pct, 2),
            "total_return_usd": round(val - initial, 2),
            "today_pnl":       portfolio.get("today_pnl", 0),
            "today_pnl_pct":   portfolio.get("today_pnl_pct", 0),
            "total_trades":    portfolio.get("total_trades", 0),
            "last_action":     portfolio.get("last_action", ""),
            "last_updated":    portfolio.get("last_updated", ""),
            "cash":            portfolio["cash"],
            "positions":       portfolio["positions"]
        })

    bots.sort(key=lambda b: b["total_return_pct"], reverse=True)
    for i, b in enumerate(bots):
        b["rank"] = i + 1

    save_json(LEADERBOARD_FILE, {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bots": bots
    })
    print(f"  Leaderboard: {[b['display_name'] for b in bots]}")


# ─── Main Bot Run ─────────────────────────────────────────────────────────────
def run_bot(bot_id: str, prices: dict, market_data: dict) -> dict:
    profile   = BOT_PROFILES[bot_id]
    portfolio = load_json(portfolio_path(bot_id))
    trades_db = load_json(trades_path(bot_id))

    print(f"\n  {profile['avatar']} {profile['display_name']}")

    sync_prices(portfolio, prices)

    today_str = date.today().isoformat()
    if portfolio.get("today_date") != today_str:
        portfolio["today_date"]        = today_str
        portfolio["today_start_value"] = calc_value(portfolio, prices)

    today_start = portfolio["today_start_value"]
    new_trades  = []
    outlook     = ""

    try:
        print(f"    Querying Groq...")
        decision = get_decision(bot_id, profile, portfolio, prices, market_data)
        outlook  = decision.get("market_outlook", "")
        print(f"    Outlook: {outlook[:80]}")
        print(f"    Trades proposed: {len(decision.get('trades', []))}")

        for trade in decision.get("trades", []):
            rec, err = execute_trade(portfolio, trade, prices, profile)
            if err:
                print(f"    ✗ Rejected: {err}")
                continue
            rec["timestamp"]      = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            rec["market_outlook"] = outlook
            new_trades.append(rec)
            print(f"    ✓ {rec['action']} {rec['shares']}x {rec['ticker']} @ ${rec['price']:.2f}")

    except Exception as e:
        print(f"    ✗ Decision error: {e}")
        outlook = "Analysis unavailable this session"

    # Update portfolio metrics
    val_after = calc_value(portfolio, prices)
    portfolio["total_value"]      = val_after
    portfolio["total_return_pct"] = round((val_after - profile["initial_capital"]) / profile["initial_capital"] * 100, 2)
    portfolio["today_pnl"]        = round(val_after - today_start, 2)
    portfolio["today_pnl_pct"]    = round((val_after - today_start) / today_start * 100, 2) if today_start else 0
    portfolio["total_trades"]     = portfolio.get("total_trades", 0) + len(new_trades)
    portfolio["last_updated"]     = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    portfolio["last_action"]      = (outlook[:120] if outlook else ("Traded" if new_trades else "Analysed market, no trades"))

    # Append to portfolio history (keep last 500 snapshots)
    portfolio.setdefault("portfolio_history", []).append({
        "timestamp": portfolio["last_updated"],
        "value":     val_after
    })
    portfolio["portfolio_history"] = portfolio["portfolio_history"][-500:]

    save_json(portfolio_path(bot_id), portfolio)

    if new_trades:
        trades_db["trades"].extend(new_trades)
        save_json(trades_path(bot_id), trades_db)

    print(f"    → ${val_after:.2f} ({portfolio['total_return_pct']:+.2f}%) | Today: {portfolio['today_pnl']:+.2f}")
    return portfolio


# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    now_utc = datetime.utcnow()
    now_et  = datetime.now(ET)
    market_open = is_market_open()

    print(f"\n{'═'*60}")
    print(f"  PaperChase Trading Bots  {now_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  ET: {now_et.strftime('%H:%M %Z')}  |  Market: {'OPEN 🟢' if market_open else 'CLOSED 🔴'}")
    print(f"{'═'*60}")

    print("\n[1] Fetching market sentiment...")
    market_data = get_market_data()
    print(f"    Market Sentinel: {'✓ loaded' if market_data else '⚠ unavailable'}")

    # Collect all tickers (watchlists + open positions)
    all_tickers = set()
    for pid, profile in BOT_PROFILES.items():
        all_tickers.update(profile["watchlist"])
        try:
            pf = load_json(portfolio_path(pid))
            all_tickers.update(pf.get("positions", {}).keys())
        except Exception:
            pass

    print(f"\n[2] Fetching prices for {len(all_tickers)} tickers...")
    prices = get_stock_prices(list(all_tickers))
    print(f"    Got {len(prices)}/{len(all_tickers)} prices")

    print("\n[3] Running bots...")
    all_results = []

    for bot_id, profile in BOT_PROFILES.items():
        try:
            if not market_open:
                # Price-only update outside market hours
                pf = load_json(portfolio_path(bot_id))
                sync_prices(pf, prices)
                pf["total_value"]   = calc_value(pf, prices)
                pf["last_updated"]  = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                save_json(portfolio_path(bot_id), pf)
                all_results.append((pf, profile))
                print(f"\n  {profile['avatar']} {profile['display_name']}: price update only (market closed)")
            else:
                pf = run_bot(bot_id, prices, market_data)
                all_results.append((pf, profile))
        except Exception as e:
            print(f"\n  ✗ Bot {bot_id} failed: {e}")

    print("\n[4] Updating leaderboard...")
    if all_results:
        update_leaderboard(all_results)

    print(f"\n{'═'*60}  Done.\n")


if __name__ == "__main__":
    main()
