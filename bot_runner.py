#!/usr/bin/env python3
"""
PaperChase Trading Bot Runner
Runs AI paper trading bots during US market hours using Gemini 2.0 Flash.
"""

import os, json, time, requests, yfinance as yf
from datetime import datetime, date
import pytz
from google import genai
from google.genai import types as genai_types
from bot_profiles import BOT_PROFILES

ET = pytz.timezone("America/New_York")
DATA_DIR          = "data/bots"
LEADERBOARD_FILE  = "data/leaderboard.json"
MARKET_SENTINEL   = "https://paperchase.online/market-sentinel/data/market_data.json"
RATE_LIMIT_DELAY  = 5   # seconds between Gemini calls — keeps throughput ~10 RPM (free tier: 15 RPM)


# ── Market Hours ──────────────────────────────────────────────────────────────
def is_market_open():
    """Check NYSE is currently open — handles weekends, holidays, and early closes."""
    now_et = datetime.now(ET)
    # Fast reject: weekends
    if now_et.weekday() >= 5:
        return False
    # Fast reject: outside possible trading hours
    if now_et.hour < 9 or now_et.hour >= 16:
        return False
    if now_et.hour == 9 and now_et.minute < 30:
        return False
    # Full check: NYSE calendar (handles US holidays + early close days)
    try:
        import exchange_calendars as xcals
        import pandas as pd
        cal = xcals.get_calendar("XNYS")
        return bool(cal.is_open_at_time(pd.Timestamp.now('UTC')))
    except Exception as e:
        print(f"  WARN Calendar check failed ({e}), falling back to time check")
        return True


# ── Prices ────────────────────────────────────────────────────────────────────
def get_prices(tickers):
    prices = {}
    try:
        data = yf.download(" ".join(tickers), period="1d", interval="5m",
                           progress=False, auto_adjust=True, threads=True)
        if data.empty: raise ValueError("empty")
        close = data["Close"]
        if len(tickers) == 1:
            prices[tickers[0]] = round(float(close.dropna().iloc[-1]), 4)
        else:
            for t in tickers:
                try: prices[t] = round(float(close[t].dropna().iloc[-1]), 4)
                except: pass
    except Exception as e:
        print(f"  WARN yfinance batch: {e} — trying individually")
        for t in tickers:
            try:
                d = yf.Ticker(t).history(period="1d", interval="5m")
                if not d.empty: prices[t] = round(float(d["Close"].iloc[-1]), 4)
                time.sleep(0.3)
            except: pass
    return prices


# ── Daily Price Changes ───────────────────────────────────────────────────────
def get_price_changes(tickers: list) -> dict:
    """Return {ticker: daily_change_pct} vs previous close."""
    changes = {}
    try:
        data = yf.download(" ".join(tickers), period="5d", interval="1d",
                           progress=False, auto_adjust=True, threads=True)
        if data.empty: return changes
        close = data["Close"]
        if len(tickers) == 1:
            vals = close.dropna()
            if len(vals) >= 2:
                changes[tickers[0]] = round((float(vals.iloc[-1]) - float(vals.iloc[-2])) / float(vals.iloc[-2]) * 100, 2)
        else:
            for t in tickers:
                try:
                    vals = close[t].dropna()
                    if len(vals) >= 2:
                        changes[t] = round((float(vals.iloc[-1]) - float(vals.iloc[-2])) / float(vals.iloc[-2]) * 100, 2)
                except: pass
    except Exception as e:
        print(f"  WARN price changes: {e}")
    return changes


# ── Per-Bot Domain Context ─────────────────────────────────────────────────────
_DOMAIN_KEYWORDS = {
    "elon":    ["tesla","nvidia","ai","chip","electric","autonomous","space","robotics","openai"],
    "cathie":  ["genomics","crispr","ai","disruption","innovation","fintech","space","biotech"],
    "tony":    ["semiconductor","ai","chip","robotics","defense","quantum","nvidia","amd"],
    "nancy":   ["semiconductor","nvidia","intel","chip","legislation","tech","government","contract"],
    "satoshi": ["bitcoin","crypto","blockchain","ethereum","mining","btc","exchange","digital","defi"],
    "jordan":  ["short squeeze","meme","momentum","breakout","surge","rally","parabolic"],
    "xi":      ["china","chinese","beijing","alibaba","stimulus","us-china","tariff","trade war"],
    "donald":  ["defense","military","oil","energy","tariff","america","steel","aerospace"],
    "jerome":  ["fed","interest rate","inflation","cpi","fomc","monetary","treasury","yield"],
    "ray":     ["macro","gold","bond","yield","recession","inflation","dollar","commodity","gdp"],
    "george":  ["crash","bubble","overvalued","systemic","hedge","macro","dislocation","currency"],
    "warren":  ["earnings","dividend","moat","valuation","consumer","banking","berkshire","buyback"],
    "kevin":   ["dividend","yield","reit","income","payout","telecom","pharma"],
    "scrooge": ["dividend","yield","reit","income","gold","bdc","mlp"],
    "michael": ["undervalued","contrarian","beaten","low pe","recovery","turnaround","oversold"],
    "jamie":   ["bank","financial","interest rate","fed","jpmorgan","lending","credit","mortgage"],
    "gordon":  ["restructuring","activist","takeover","layoffs","ceo","spinoff","acquisition","merger"],
    "patrick": ["luxury","premium","consumer","brand","apple","retail","lifestyle","fashion"],
    "thanos":  ["sector","rotation","rebalance","etf","allocation","diversif","balance"],
    "yoda":    ["index","s&p500","market","passive","long-term","etf","vanguard"],
}

def build_bot_context(bot_id: str, profile: dict, prices: dict, changes: dict, market_data: dict) -> dict:
    """Build per-bot enriched research context from filtered news + watchlist movers."""
    stocks = market_data.get("stocks", {})
    crypto = market_data.get("crypto", {})

    all_news = (
        [n.get("title", "") for n in (stocks.get("news") or [])[:12]] +
        [n.get("title", "") for n in (crypto.get("news") or [])[:6]]
    )

    keywords = _DOMAIN_KEYWORDS.get(bot_id, [])
    domain_news, other_news = [], []
    for h in all_news:
        if any(k in h.lower() for k in keywords):
            domain_news.append(h)
        else:
            other_news.append(h)
    selected_news = (domain_news[:4] + other_news[:1]) if domain_news else other_news[:4]

    # Top movers within this bot's watchlist
    wl_changes = [(t, changes.get(t, 0.0)) for t in profile["watchlist"] if t in prices]
    top_movers = sorted(wl_changes, key=lambda x: abs(x[1]), reverse=True)[:6]

    # Domain-specific extra context
    extra_lines = []
    idx = stocks.get("indices", {})

    if bot_id in ("satoshi", "jordan"):
        cs = crypto.get("news_summary") or crypto.get("reddit_summary") or ""
        if cs:
            extra_lines.append(f"CRYPTO SENTIMENT: {cs[:250]}")

    if bot_id == "xi":
        china = [h for h in all_news if any(k in h.lower() for k in ["china","chinese","beijing","alibaba","baidu","pdd"])]
        if china:
            extra_lines.append("CHINA FOCUS: " + " | ".join(china[:2]))

    if bot_id in ("jerome", "ray", "george"):
        if isinstance(idx, dict):
            n_chg = idx.get("nasdaq", {}).get("change_24h", "N/A")
            d_chg = idx.get("dow", {}).get("change_24h", "N/A")
            vix_v = float(idx.get("vix", {}).get("value", 20) or 20)
            vix_state = "ELEVATED — risk-off" if vix_v > 25 else "LOW — risk-on" if vix_v < 15 else "NORMAL"
            extra_lines.append(f"MACRO: NASDAQ {n_chg:+.2f}%  DOW {d_chg:+.2f}%  VIX {vix_v:.1f} ({vix_state})")
        mkt_reddit = stocks.get("reddit_summary") or ""
        if mkt_reddit:
            extra_lines.append(f"MARKET REDDIT: {mkt_reddit[:200]}")

    if bot_id in ("warren", "michael", "kevin", "scrooge"):
        fg = crypto.get("fear_greed", {})
        fg_v = fg.get("value", 50)
        fg_l = fg.get("label", "Neutral")
        meaning = (
            "Oversold — potential value opportunity" if fg_v < 30 else
            "Extreme greed — valuations stretched, be selective" if fg_v > 75 else
            "Moderate sentiment — stick to fundamentals"
        )
        extra_lines.append(f"VALUE CONTEXT: Fear&Greed={fg_v} ({fg_l}) — {meaning}")

    return {
        "selected_news": selected_news,
        "top_movers":    top_movers,
        "domain_extra":  "\n".join(extra_lines),
    }


# ── Market Sentinel Data ──────────────────────────────────────────────────────
def get_market_data():
    try: return requests.get(MARKET_SENTINEL, timeout=15).json()
    except Exception as e:
        print(f"  WARN Market Sentinel: {e}")
        return {}


# ── Portfolio I/O ─────────────────────────────────────────────────────────────
def load_json(p): return json.load(open(p))
def save_json(p, d): json.dump(d, open(p,"w"), indent=2)
def pf_path(b): return f"{DATA_DIR}/{b}/portfolio.json"
def tr_path(b): return f"{DATA_DIR}/{b}/trades.json"


# ── Portfolio Math ────────────────────────────────────────────────────────────
def calc_value(pf, prices):
    return round(pf["cash"] + sum(
        pos["shares"] * prices.get(t, pos.get("current_price", pos["avg_cost"]))
        for t, pos in pf["positions"].items()
    ), 2)

def sync_prices(pf, prices):
    for t in pf["positions"]:
        if t in prices: pf["positions"][t]["current_price"] = prices[t]


# ── Trade Execution ───────────────────────────────────────────────────────────
def execute(pf, trade, prices, profile):
    ticker = str(trade.get("ticker","")).upper().strip()
    action = str(trade.get("action","")).upper().strip()
    shares = int(trade.get("shares", 0))
    if not ticker or action not in ("BUY","SELL") or shares <= 0:
        return None, f"invalid: {trade}"
    price = prices.get(ticker)
    if not price: return None, f"no price for {ticker}"

    total_val = calc_value(pf, prices)
    max_pos   = total_val * profile["max_position_pct"]
    min_cash  = profile["min_cash_reserve"]

    if action == "BUY":
        avail = pf["cash"] - min_cash
        if avail <= 0: return None, "below cash reserve"
        existing = pf["positions"].get(ticker, {}).get("shares", 0) * price
        room = max_pos - existing
        if room <= 0: return None, f"position cap for {ticker}"
        shares = min(shares, int(min(room, avail) / price))
        if shares <= 0: return None, "0 shares after sizing"
        cost = round(shares * price, 2)
        pf["cash"] = round(pf["cash"] - cost, 2)
        if ticker in pf["positions"]:
            old = pf["positions"][ticker]
            ns  = old["shares"] + shares
            pf["positions"][ticker] = {"shares": ns, "current_price": price,
                "avg_cost": round((old["shares"]*old["avg_cost"] + shares*price)/ns, 4)}
        else:
            pf["positions"][ticker] = {"shares": shares, "avg_cost": round(price,4), "current_price": price}

    elif action == "SELL":
        pos = pf["positions"].get(ticker)
        if not pos: return None, f"no position in {ticker}"
        shares = min(shares, pos["shares"])
        pf["cash"] = round(pf["cash"] + shares * price, 2)
        if shares >= pos["shares"]: del pf["positions"][ticker]
        else: pf["positions"][ticker]["shares"] -= shares

    return {"action": action, "ticker": ticker, "shares": shares,
            "price": price, "total_value": round(shares*price,2),
            "reasoning": str(trade.get("reasoning",""))[:300]}, None


# ── Gemini Decision ───────────────────────────────────────────────────────────
def get_decision(bot_id, profile, pf, prices, changes, market_data):
    """Returns (decision_dict, context_dict). decision has trades/market_outlook/analysis."""
    total = calc_value(pf, prices)
    ret   = (total - profile["initial_capital"]) / profile["initial_capital"] * 100

    pos_display = {t: {"shares": p["shares"], "avg_cost": p["avg_cost"],
        "current": prices.get(t, p.get("current_price", p["avg_cost"])),
        "pnl": round((prices.get(t, p.get("current_price", p["avg_cost"])) - p["avg_cost"]) * p["shares"], 2)}
        for t, p in pf["positions"].items()}

    stocks = market_data.get("stocks", {})
    fg     = market_data.get("crypto", {}).get("fear_greed", {})
    idx    = stocks.get("indices", {})
    sp500  = idx.get("sp500", {}).get("change_24h", "N/A") if isinstance(idx, dict) else "N/A"
    vix    = idx.get("vix",   {}).get("value",     "N/A") if isinstance(idx, dict) else "N/A"

    ctx = build_bot_context(bot_id, profile, prices, changes, market_data)

    # Watchlist with price + daily change
    avail = {t: {"price": prices[t], "chg_pct": changes.get(t, 0.0)}
             for t in profile["watchlist"] if t in prices}

    movers_str = "  ".join(
        f"{t} {'+' if c >= 0 else ''}{c:.1f}%"
        for t, c in ctx["top_movers"]
    ) or "minimal movement"

    news_lines = "\n".join(f"  • {h}" for h in ctx["selected_news"]) or "  (no relevant headlines available)"

    prompt = f"""You are {profile['display_name']}, a paper trader on PaperChase Trading Arena.

PERSONALITY: {profile['prompt_persona']}

PORTFOLIO: Cash ${pf['cash']:.2f} | Total ${total:.2f} | Return {ret:+.2f}%
POSITIONS: {json.dumps(pos_display) if pos_display else "None — fully in cash"}

YOUR WATCHLIST (price + today's move):
{json.dumps(avail)}

MARKET CONDITIONS:
  Fear & Greed: {fg.get('value','N/A')} — {fg.get('label', 'N/A')}
  S&P 500 today: {sp500}% | VIX: {vix}
  Your watchlist top movers today: {movers_str}

NEWS RELEVANT TO YOUR STRATEGY:
{news_lines}
{ctx['domain_extra']}

RULES: Only BUY from your watchlist. Max {int(profile['max_position_pct']*100)}% per stock. Keep >=${profile['min_cash_reserve']} cash reserve. Max {profile['max_trades_per_session']} trades this session.

Reply ONLY valid JSON:
{{"trades":[{{"action":"BUY","ticker":"AAPL","shares":5,"reasoning":"one sentence citing specific data"}}],"market_outlook":"one sentence","analysis":"2-3 sentences: what specific data points you noticed, why you acted or held back, what you're watching next"}}
No trades: {{"trades":[],"market_outlook":"...","analysis":"..."}}"""

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.75,
                    max_output_tokens=800
                )
            )
            result = json.loads(resp.text)
            if not isinstance(result, dict):
                raise ValueError(f"Gemini returned non-dict: {type(result)}")
            return result, ctx
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 20 * (attempt + 1)   # 20s then 40s (was 60/120s)
                print(f"    Rate limit hit, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


# ── Leaderboard ───────────────────────────────────────────────────────────────
def update_leaderboard(results):
    bots = []
    for pf, profile in results:
        val = pf["total_value"]; init = profile["initial_capital"]
        bots.append({
            "bot_id": profile["bot_id"], "display_name": profile["display_name"],
            "avatar": profile["avatar"], "bio": profile["bio"],
            "strategy": profile["strategy"], "risk_level": profile["risk_level"],
            "risk_bar": profile["risk_bar"], "color": profile["color"],
            "total_value": val, "initial_capital": init,
            "total_return_pct":  round((val-init)/init*100, 2),
            "total_return_usd":  round(val-init, 2),
            "today_pnl":         pf.get("today_pnl", 0),
            "today_pnl_pct":     pf.get("today_pnl_pct", 0),
            "total_trades":      pf.get("total_trades", 0),
            "last_action":       pf.get("last_action", ""),
            "last_updated":      pf.get("last_updated", ""),
            "cash":              pf["cash"],
            "positions":         pf["positions"]
        })
    bots.sort(key=lambda b: b["total_return_pct"], reverse=True)
    for i, b in enumerate(bots): b["rank"] = i + 1
    save_json(LEADERBOARD_FILE, {"updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "bots": bots})
    print(f"  Leaderboard updated ({len(bots)} bots)")


# ── Single Bot Run ────────────────────────────────────────────────────────────
def run_bot(bot_id, prices, changes, market_data):
    profile   = BOT_PROFILES[bot_id]
    pf        = load_json(pf_path(bot_id))
    trades_db = load_json(tr_path(bot_id))

    print(f"\n  {profile['avatar']} {profile['display_name']}")
    sync_prices(pf, prices)

    today = date.today().isoformat()
    if pf.get("today_date") != today:
        pf["today_date"] = today
        pf["today_start_value"] = calc_value(pf, prices)

    start_val  = pf["today_start_value"]
    new_trades = []
    outlook    = ""
    analysis   = ""
    ctx        = {}

    # Snapshot market context for transparency display
    stocks   = market_data.get("stocks", {})
    fg       = market_data.get("crypto", {}).get("fear_greed", {})
    idx      = stocks.get("indices", {})
    sp500_v  = idx.get("sp500", {}).get("change_24h", None) if isinstance(idx, dict) else None
    vix_v    = idx.get("vix",   {}).get("value",     None) if isinstance(idx, dict) else None

    try:
        print(f"    → Gemini query...")
        dec, ctx = get_decision(bot_id, profile, pf, prices, changes, market_data)
        outlook  = dec.get("market_outlook", "")
        analysis = dec.get("analysis", "")
        print(f"    → {outlook[:70]}")

        for trade in dec.get("trades", []):
            rec, err = execute(pf, trade, prices, profile)
            if err: print(f"    FAIL {err}"); continue
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            rec["timestamp"]      = ts
            rec["market_outlook"] = outlook
            rec["signal_context"] = {
                "fg_value":         fg.get("value"),
                "fg_label":         fg.get("label"),
                "sp500_chg":        sp500_v,
                "vix":              vix_v,
                "ticker_chg_pct":   changes.get(rec["ticker"], None),
                "trigger_news":     ctx.get("selected_news", [None])[0],
            }
            new_trades.append(rec)
            print(f"    OK {rec['action']} {rec['shares']}x {rec['ticker']} @${rec['price']:.2f}")

    except Exception as e:
        import traceback
        print(f"    FAIL {type(e).__name__}: {e}")
        traceback.print_exc()
        outlook  = "Analysis unavailable"
        analysis = ""

    val      = calc_value(pf, prices)
    now_str  = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    pf.update({
        "total_value":      val,
        "total_return_pct": round((val - profile["initial_capital"]) / profile["initial_capital"] * 100, 2),
        "today_pnl":        round(val - start_val, 2),
        "today_pnl_pct":    round((val - start_val) / start_val * 100, 2) if start_val else 0,
        "total_trades":     pf.get("total_trades", 0) + len(new_trades),
        "last_updated":     now_str,
        "last_action":      outlook[:200] or ("Traded" if new_trades else "Analysed — no trades"),
        "last_session": {
            "at":              now_str,
            "fear_greed":      fg.get("value"),
            "fear_greed_label":fg.get("label"),
            "sp500_change":    sp500_v,
            "vix":             vix_v,
            "top_movers":      [[t, c] for t, c in ctx.get("top_movers", [])],
            "news_read":       ctx.get("selected_news", []),
            "domain_extra":    ctx.get("domain_extra", ""),
            "ai_analysis":     analysis,
            "outlook":         outlook,
            "trades_made":     len(new_trades),
        },
    })
    pf.setdefault("portfolio_history", []).append({"timestamp": now_str, "value": val})
    pf["portfolio_history"] = pf["portfolio_history"][-500:]

    save_json(pf_path(bot_id), pf)
    if new_trades:
        trades_db["trades"].extend(new_trades)
        save_json(tr_path(bot_id), trades_db)

    print(f"    → ${val:.2f} ({pf['total_return_pct']:+.2f}%) | Today: {pf['today_pnl']:+.2f}")
    return pf


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now_et = datetime.now(ET)
    open_  = is_market_open()
    print(f"\n{'='*55}")
    print(f"  PaperChase Bots  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  ET: {now_et.strftime('%H:%M')}  Market: {'OPEN' if open_ else 'CLOSED'}")
    print(f"{'='*55}")

    if not open_:
        print("  Market is closed — skipping this run.")
        print(f"{'='*55}\n")
        return

    # ── Gemini API key check ──────────────────────────────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("  FATAL: GEMINI_API_KEY is not set. Aborting.")
        print(f"{'='*55}\n")
        raise SystemExit(1)
    print(f"  Gemini API key: set ({len(api_key)} chars)")

    print("\n[1] Market data...")
    md = get_market_data()
    print(f"    Market Sentinel: {'OK' if md else 'unavailable'}")

    all_tickers = set()
    for pid, p in BOT_PROFILES.items():
        all_tickers.update(p["watchlist"])
        try: all_tickers.update(load_json(pf_path(pid)).get("positions", {}).keys())
        except: pass

    print(f"\n[2] Prices for {len(all_tickers)} tickers...")
    tickers_list = list(all_tickers)
    prices  = get_prices(tickers_list)
    print(f"    Got {len(prices)}/{len(all_tickers)}")

    print(f"\n[2b] Daily changes...")
    changes = get_price_changes(tickers_list)
    print(f"    Got {len(changes)} changes")

    print(f"\n[3] Running {len(BOT_PROFILES)} bots...")
    results = []
    for bot_id, profile in BOT_PROFILES.items():
        try:
            results.append((run_bot(bot_id, prices, changes, md), profile))
            time.sleep(RATE_LIMIT_DELAY)   # Gemini 15 RPM rate limit
        except Exception as e:
            print(f"\n  FAIL {bot_id}: {e}")

    print(f"\n[4] Leaderboard...")
    if results: update_leaderboard(results)
    print(f"\n{'='*55}  Done.\n")


if __name__ == "__main__":
    main()
