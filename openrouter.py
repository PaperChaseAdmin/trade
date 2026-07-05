"""
OpenRouter decision function for PaperChase trading bots.
OpenAI-compatible API that routes to free models (Gemma, Llama, DeepSeek, Mistral).
Includes per-bot fallback model support for resilience.

If the primary model fails (provider error / rate limit / content=null),
falls back to the bot's designated fallback model (a different source).
"""

import os, json, time, requests, re
from datetime import date, datetime
from bot_profiles import BOT_PROFILES

# Global fallback chain — used as last resort if primary AND per-bot fallback both fail
GLOBAL_FALLBACK_CHAIN = ["nemotron", "gemma", "cohere", "liquid", "qwen3-coder", "llama70b", "nemotron-ultra"]


def get_decision(bot_id, profile, pf, prices, changes, market_data,
                 model_name="minimax", fallback_model=None):
    """Returns (decision_dict, context_dict) using OpenRouter API.
    
    Uses profile.get('model') to determine which OpenRouter model to use.
    Falls back to profile's fallback_model if primary fails.
    If both fail, tries global fallback chain.
    """
    total = pf.get("total_value", calc_value(pf, prices))
    ret = (total - profile["initial_capital"]) / profile["initial_capital"] * 100

    pos_display = {t: {"shares": p["shares"], "avg_cost": p["avg_cost"],
        "current": prices.get(t, p.get("current_price", p["avg_cost"])),
        "pnl": round((prices.get(t, p.get("current_price", p["avg_cost"])) - p["avg_cost"]) * p["shares"], 2)}
        for t, p in pf.get("positions", {}).items()}

    stocks = market_data.get("stocks", {})
    fg = market_data.get("crypto", {}).get("fear_greed", {})
    idx = stocks.get("indices", {})
    sp500 = idx.get("sp500", {}).get("change_24h", "N/A") if isinstance(idx, dict) else "N/A"
    vix = idx.get("vix", {}).get("value", "N/A") if isinstance(idx, dict) else "N/A"

    ctx = _build_bot_context(bot_id, profile, prices, changes, market_data)

    avail = {t: {"price": prices[t], "chg_pct": changes.get(t, 0.0)}
             for t in profile["watchlist"] if t in prices}

    prompt = _build_prompt(profile, pf, pos_display, avail, prices, changes, ctx, total, ret, sp500, vix, fg, market_data)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    # Build model list: primary → per-bot fallback → global chain
    base_primary = _resolve_base_name(model_name)
    base_fallback = _resolve_base_name(fallback_model) if fallback_model else None
    
    models_to_try = [base_primary]
    if base_fallback and base_fallback != base_primary:
        models_to_try.append(base_fallback)
    for m in GLOBAL_FALLBACK_CHAIN:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for attempt_model in models_to_try:
        or_model_id = _resolve_model_id(attempt_model)
        print(f"    → OpenRouter ({attempt_model})...")
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
                        {"role": "system", "content": "You are a stock market paper trader. Reply ONLY with valid JSON. Do NOT include any reasoning, explanation, or thinking. Your ENTIRE response must be parseable JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1200,
                    "response_format": {"type": "json_object"},
                },
                timeout=90,  # more patience → less fallback churn
            )
            data = resp.json()
            if "error" in data:
                err = data["error"]
                code = err.get("code", 0)
                msg = err.get("message", str(err))
                if code == 429:
                    wait = 45  # longer backoff
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    # Single retry after rate limit
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
                                {"role": "system", "content": "You are a stock market paper trader. Reply ONLY with valid JSON. Do NOT include any reasoning, explanation, or thinking. Your ENTIRE response must be parseable JSON."},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.1,
                            "max_tokens": 1200,
                            "response_format": {"type": "json_object"},
                        },
                        timeout=90,
                    )
                    data = resp.json()
                    if "error" in data:
                        err = data["error"]
                        msg = err.get("message", str(err))
                        print(f"    Error on {attempt_model} after retry, trying next model...")
                        last_error = ValueError(f"OpenRouter API error: {msg}")
                        continue  # try next model
                else:
                    # All errors (provider, etc.) → try next model instead of raising
                    print(f"    Error on {attempt_model}: {msg[:100]}, trying next model...")
                    last_error = ValueError(f"OpenRouter error: {msg[:200]}")
                    continue  # try next model

            content = data["choices"][0]["message"].get("content")
            if content is None:
                reasoning = data["choices"][0]["message"].get("reasoning", "")
                if reasoning:
                    json_match = re.search(r'\{.*\}', reasoning, re.DOTALL)
                    if json_match:
                        content = json_match.group()
                    else:
                        print(f"    No JSON in reasoning on {attempt_model}, trying next model...")
                        last_error = ValueError(f"OpenRouter returned no content. Reasoning: {reasoning[:200]}")
                        continue  # try next model
                else:
                    print(f"    No content from {attempt_model}, trying next model...")
                    last_error = ValueError(f"OpenRouter returned no content.")
                    continue  # try next model
            
            result = json.loads(content)
            if not isinstance(result, dict):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError(f"OpenRouter returned non-dict: {type(result)}")
            return result, ctx

        except requests.Timeout:
            print(f"    Timeout on {attempt_model}, trying next model...")
            last_error = TimeoutError(f"OpenRouter timeout on {attempt_model}")
            continue
        except json.JSONDecodeError as e:
            print(f"    JSON parse error on {attempt_model}, trying next model...")
            last_error = e
            continue
        except Exception as e:
            # All errors → try next model (never re-raise, exhaust the chain)
            print(f"    Exception on {attempt_model}: {e}, trying next model...")
            last_error = e
            continue  # try next model

    # All models exhausted
    if last_error:
        raise last_error
    raise RuntimeError("Failed to get decision from OpenRouter after all models exhausted")


def _resolve_base_name(model_name):
    """Convert model name strings to base name for model ID resolution.
    ponytail: pass through unrecognized names — _resolve_model_id handles the mapping."""
    if not model_name:
        return None
    m = str(model_name).lower()
    if "gemma" in m and "26b" in m:
        return "gemma"
    if "nemotron" in m and "ultra" in m:
        return "nemotron-ultra"
    if "nemotron" in m:
        return "nemotron"
    if "llama" in m and "70b" in m:
        return "llama70b"
    if "qwen" in m and "coder" in m:
        return "qwen3-coder"
    if "cohere" in m:
        return "cohere"
    if "liquid" in m:
        return "liquid"
    # Pass through — _resolve_model_id has the definitive mapping
    return m


def _resolve_model_id(model_name):
    """Map short model name to full OpenRouter model ID."""
    mapping = {
        # === CONFIRMED WORKING FREE MODELS (tested 2026-07-01 from HK) ===
        "nemotron": "nvidia/nemotron-3-super-120b-a12b",
        "nemotron-3-super-120b-a12b": "nvidia/nemotron-3-super-120b-a12b",
        "gemma": "google/gemma-4-26b-a4b-it",
        "google/gemma-4-26b-a4b-it": "google/gemma-4-26b-a4b-it",
        "cohere": "cohere/north-mini-code",
        "cohere/north-mini-code": "cohere/north-mini-code",
        "liquid": "liquid/lfm-2.5-1.2b-thinking",
        "liquid/lfm-2.5-1.2b-thinking": "liquid/lfm-2.5-1.2b-thinking",
        # Global chain diversifiers (different providers = better rate limit survival)
        "qwen3-coder": "qwen/qwen3-coder",
        "qwen/qwen3-coder": "qwen/qwen3-coder",
        "llama70b": "meta-llama/llama-3.3-70b-instruct",
        "meta-llama/llama-3.3-70b-instruct": "meta-llama/llama-3.3-70b-instruct",
        "nemotron-ultra": "nvidia/nemotron-3-ultra-550b-a55b",
        "nvidia/nemotron-3-ultra-550b-a55b": "nvidia/nemotron-3-ultra-550b-a55b",
        # Legacy names — backwards compat with bot_profiles.py
        "qwen": "nvidia/nemotron-3-super-120b-a12b",
        "qwen3-coder": "nvidia/nemotron-3-super-120b-a12b",
        "kimi": "nvidia/nemotron-3-super-120b-a12b",
        "kimi-k2.6": "nvidia/nemotron-3-super-120b-a12b",
        "minimax": "google/gemma-4-26b-a4b-it",
        "minimax-m2.5": "google/gemma-4-26b-a4b-it",
        "ling": "cohere/north-mini-code",
        "ling-2.6-1t": "cohere/north-mini-code",
        # Fallback-only (not tested from HK but kept for diversity)
        "llama": "nvidia/nemotron-3-super-120b-a12b",
        "deepseek": "nvidia/nemotron-3-super-120b-a12b",
        "mistral": "cohere/north-mini-code",
        "dolphin": "cohere/north-mini-code",
    }
    result = mapping.get(model_name)
    if result:
        return result
    if ":" in model_name or "/" in model_name:
        return model_name
    return f"{model_name}:free"


def _build_prompt(profile, pf, pos_display, avail, prices, changes, ctx, total, ret, sp500, vix, fg, market_data):
    """Build the trading prompt for the AI model."""
    movers_str = "  ".join(
        f"{t} {'+' if c >= 0 else ''}{c:.1f}%"
        for t, c in ctx["top_movers"]
    ) or "minimal movement"

    news_lines = "\n".join(f"  • {h}" for h in ctx["selected_news"]) or "  (no relevant headlines available)"

    return f"""Reply ONLY valid JSON. No other text.
Format: {{"trades":[{{"action":"BUY","ticker":"AAPL","shares":5,"reasoning":"..."}}],"market_outlook":"...","analysis":"..."}}
No trades: {{"trades":[],"market_outlook":"...","analysis":"..."}}

You are {profile['display_name']}, a paper trader on PaperChase Trading Arena.

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
"""


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
        if isinstance(cs, str) and cs:
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
            try:
                extra_lines.append(f"MACRO: NASDAQ {float(n_chg):+.2f}%  DOW {float(d_chg):+.2f}%  VIX {vix_v:.1f} ({vix_state})")
            except (ValueError, TypeError):
                pass
        mkt_reddit = stocks.get("reddit_summary") or ""
        if isinstance(mkt_reddit, str) and mkt_reddit:
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
