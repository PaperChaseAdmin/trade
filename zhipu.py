"""
Zhipu (智谱) GLM-4-Flash decision function for PaperChase trading bots.
Ultimate fallback when OpenRouter's 3 free models all fail.
OpenAI-compatible API, free tier, no geo-block from HK/US.

Model: glm-4-flash (FREE, 128K context, fast)
Endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
"""

import os, json, time, requests, re
from openrouter import _build_prompt, _build_bot_context, calc_value

API_BASE = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4-flash"


def get_decision(bot_id, profile, pf, prices, changes, market_data,
                 model_name="glm-4-flash", fallback_model=None):
    """Returns (decision_dict, context_dict) using Zhipu GLM-4-Flash API.
    
    Same signature as openrouter.get_decision() for drop-in replacement.
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

    prompt = _build_prompt(profile, pf, pos_display, avail, prices, changes, ctx,
                           total, ret, sp500, vix, fg, market_data)

    api_key = os.environ.get("ZHIPU_API_KEY", "")
    if not api_key:
        raise ValueError("ZHIPU_API_KEY not set")

    for attempt in range(2):
        try:
            resp = requests.post(
                f"{API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a stock market paper trader. Reply ONLY with valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.75,
                    "max_tokens": 1200,
                },
                timeout=45,
            )
            data = resp.json()

            if "error" in data:
                err = data["error"]
                msg = err.get("message", str(err))
                if attempt == 0:
                    print(f"    Zhipu error: {msg[:100]}, retrying...")
                    time.sleep(5)
                    continue
                raise ValueError(f"Zhipu API error: {msg[:200]}")

            content = data["choices"][0]["message"].get("content")
            if not content:
                raise ValueError("Zhipu returned empty content")

            # Zhipu wraps JSON in ```json ... ``` markdown fences
            content = content.strip()
            if content.startswith("```"):
                # Remove opening fence: ```json or ```
                content = re.sub(r'^```(?:json)?\s*\n?', '', content)
                # Remove closing fence: ```
                content = re.sub(r'\n?```\s*$', '', content)

            result = json.loads(content)
            if not isinstance(result, dict):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError(f"Zhipu returned non-dict: {type(result)}")

            return result, ctx

        except requests.Timeout:
            if attempt == 0:
                print(f"    Zhipu timeout, retrying...")
                time.sleep(5)
                continue
            raise TimeoutError("Zhipu timeout after retry")
        except json.JSONDecodeError:
            if attempt == 0:
                print(f"    Zhipu JSON error, retrying...")
                time.sleep(3)
                continue
            raise

    raise RuntimeError("Zhipu failed after all attempts")
