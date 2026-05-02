"""
OpenRouter decision function for PaperChase trading bots.
OpenAI-compatible API that routes to free models (Nemotron, MiniMax, etc.)
"""
import os, json, time, requests
from datetime import date, datetime
from bot_profiles import BOT_PROFILES


def get_decision(bot_id, profile, pf, prices, changes, market_data, model_name="nemotron-3-super-120b-a12b"):
    """Returns (decision_dict, context_dict) using OpenRouter API.
    
    Uses profile.get('model') to determine which OpenRouter model to use.
    """
    total = pf.get("total_value", calc_value(pf, prices))
    ret = (total - profile["initial_capital"]) / profile["initial_capital"] * 100

    # Build context similar to Gemini version
    pos_display = {t: {"shares": p["shares"], "avg_cost": p["avg_cost"],
        "current": prices.get(t, p.get("current_price", p["avg_cost"])),
        "pnl": round((prices.get(t, p.get("current_price", p["avg_cost"])) - p["avg_cost"]) * p["shares"], 2)}
        for t, p in pf.get("positions", {}).items()}

    stocks = market_data.get("stocks", {})
    fg = market_data.get("crypto", {}).get("fear_greed", {})
    idx = stocks.get("indices", {})
    sp500 = idx.get("sp500", {}).get("change_24h", "N/A") if isinstance(idx, dict) else "N/A"
    vix = idx.get("vix", {}).get("value", "N/A") if isinstance(idx, dict) else "N/A"

    # Build bot context
    ctx = _build_bot_context(bot_id, profile, prices, changes, market_data)

    avail = {t: {"price": prices[t], "chg_pct": changes.get(t, 0.0)}
             for t in profile["watchlist"] if t in prices}

    movers_str = "  ".join(
        f"{t} {'+' if c >= 0 else ''}{c:.1f}%"
        for t, c in ctx["top_movers"]
    ) or "minimal movement"

    news_lines = "\n".join(f"  \u2022 {h}" for h in ctx["selected_news"]) or "  (no relevant headlines available)"

    prompt = f"""You are {profile['display_name']}, a paper trader on PaperChase Trading Arena.

PERSONALITY: {profile['prompt_persona']}

PORTFOLIO: Cash ${pf['cash']:.2f} | Total ${total:.2f} | Return {ret:+.2f}%
POSITIONS: {json.dumps(pos_display) if pos_display else "None \u2014 fully in cash"}

YOUR WATCHLIST (price + today's move):
{json.dumps(avail)}

MARKET CONDITIONS:
  Fear & Greed: {fg.get('value','N/A')} \u2014 {fg.get('label', 'N/A')}
  S&P 500 today: {sp500}% | VIX: {vix}
  Your watchlist top movers today: {movers_str}

NEWS RELEVANT TO YOUR STRATEGY:
{news_lines}
{ctx['domain_extra']}

RULES: Only BUY from your watchlist. Max {int(profile['max_position_pct']*100)}% per stock. Keep >=${profile['min_cash_reserve']} cash reserve. Max {profile['max_trades_per_session']} trades this session.

Reply ONLY valid JSON:
{{"trades":[{{"action":"BUY","ticker":"AAPL","shares":5,"reasoning":"one sentence citing specific data"}}],"market_outlook":"one sentence","analysis":"2-3 sentences: what specific data points you noticed, why you acted or held back, what you're watching next"}}
No trades: {{"trades":[],"market_outlook":"...","analysis":"..."}}"""

    # Map model_name to OpenRouter model ID
    or_model_id = _resolve_model_id(model_name)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://paperchase.online",
                },
                json={
                    "model": or_model_id,
                    "messages": [
                        {"role": "system", "content": "You are a stock market paper trader. Reply ONLY with valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.75,
                    "max_tokens": 800,
                    "response_format": {"type": "json_object"},
                },
                timeout=60,
            )
            data = resp.json()
            if "error" in data:
                err = data["error"]
                code = err.get("code", 0)
                msg = err.get("message", str(err))
                if code == 429 and attempt < 2:
                    wait = 20 * (attempt + 1)
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise ValueError(f"OpenRouter API error: {msg}")

            content = data["choices"][0]["message"].get("content")
            if content is None:
                # Some models return reasoning without content
                # Try reasoning field or raise
                reasoning = data["choices"][0]["message"].get("reasoning", "")
                if reasoning:
                    # Attempt to extract JSON from reasoning
                    import re
                    json_match = re.search(r'\{.*\}', reasoning, re.DOTALL)
                    if json_match:
                        content = json_match.group()
                    else:
                        raise ValueError(f"OpenRouter returned no content. Reasoning: {reasoning[:200]}")
                else:
                    raise ValueError(f"OpenRouter returned no content. Full: {json.dumps(data['choices'][0]['message'])[:300]}")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError(f"OpenRouter returned non-dict: {type(result)}")
            return result, ctx

        except Exception as e:
            if attempt < 2:
                wait = 5 * (attempt + 1)
                print(f"    Retry {attempt+1} after error: {e}")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("Failed to get decision from OpenRouter after 3 attempts")


def _resolve_model_id(model_name):
    """Map short model name to full OpenRouter model ID."""
    mapping = {
        "nemotron": "nvidia/nemotron-3-super-120b-a12b:free",
        "nemotron-3-super-120b-a12b": "nvidia/nemotron-3-super-120b-a12b:free",
        "minimax": "minimax/minimax-m2.5:free",
        "minimax-m2.5": "minimax/minimax-m2.5:free",
    }
    result = mapping.get(model_name)
    if result:
        return result
    # If not in mapping, assume it's already a full model ID
    if ":" in model_name or "/" in model_name:
        return model_name
    return f"{model_name}:free"


def _build_bot_context(bot_id, profile, prices, changes, market_data):
    """Build per-bot enriched research context. Mirrors the Gemini version's logic."""
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

    wl_changes = [(t, changes.get(t, 0.0)) for t in profile["watchlist"] if t in prices]
    top_movers = sorted(wl_changes, key=lambda x: abs(x[1]), reverse=True)[:6]

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
            vix_state = "ELEVATED \u2014 risk-off" if vix_v > 25 else "LOW \u2014 risk-on" if vix_v < 15 else "NORMAL"
            extra_lines.append(f"MACRO: NASDAQ {n_chg:+.2f}%  DOW {d_chg:+.2f}%  VIX {vix_v:.1f} ({vix_state})")
        mkt_reddit = stocks.get("reddit_summary") or ""
        if mkt_reddit:
            extra_lines.append(f"MARKET REDDIT: {mkt_reddit[:200]}")

    if bot_id in ("warren", "michael", "kevin", "scrooge"):
        fg = crypto.get("fear_greed", {})
        fg_v = fg.get("value", 50)
        fg_l = fg.get("label", "Neutral")
        meaning = (
            "Oversold \u2014 potential value opportunity" if fg_v < 30 else
            "Extreme greed \u2014 valuations stretched, be selective" if fg_v > 75 else
            "Moderate sentiment \u2014 stick to fundamentals"
        )
        extra_lines.append(f"VALUE CONTEXT: Fear&Greed={fg_v} ({fg_l}) \u2014 {meaning}")

    return {
        "selected_news": selected_news,
        "top_movers": top_movers,
        "domain_extra": "\n".join(extra_lines),
    }


def calc_value(pf, prices):
    """Calculate total portfolio value."""
    return round(pf.get("cash", 0) + sum(
        pos["shares"] * prices.get(t, pos.get("current_price", pos.get("avg_cost", 0)))
        for t, pos in pf.get("positions", {}).items()
    ), 2)


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
