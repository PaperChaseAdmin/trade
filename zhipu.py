"""
Zhipu (智谱) Zhipu-fallback via OpenRouter for PaperChase trading bots.
Ultimate fallback when OpenRouter's main 3 models all fail.
Uses OpenRouter API (z-ai/glm-4.5-air:free) — no separate Zhipu key needed.
"""
import os, json, time, requests, re
from openrouter import _build_prompt, _build_bot_context, calc_value

MODEL_ID = "qwen/qwen3-coder"


def get_decision(bot_id, profile, pf, prices, changes, market_data,
                 model_name="glm-4.5-air", fallback_model=None):
    """Returns (decision_dict, context_dict) using Zhipu-fallback via OpenRouter."""
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

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    for attempt in range(2):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://paperchase.online",
                },
                json={
                    "model": MODEL_ID,
                    "messages": [
                        {"role": "system", "content": "You are a stock market paper trader. Reply ONLY with valid JSON. Do NOT include any reasoning, explanation, or thinking."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1200,
                    "response_format": {"type": "json_object"},
                },
                timeout=45,
            )
            data = resp.json()

            if "error" in data:
                err = data["error"]
                msg = err.get("message", str(err))
                if attempt == 0:
                    print(f"    Zhipu-fallback error: {msg[:100]}, retrying...")
                    time.sleep(5)
                    continue
                raise ValueError(f"Zhipu-fallback error: {msg[:200]}")

            content = data["choices"][0]["message"].get("content")
            if not content:
                reasoning = data["choices"][0]["message"].get("reasoning", "")
                json_match = re.search(r'\{.*\}', reasoning, re.DOTALL)
                if json_match:
                    content = json_match.group()
                else:
                    raise ValueError("Zhipu-fallback returned empty content")

            result = json.loads(content)
            if not isinstance(result, dict):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError(f"Gemma returned non-dict: {type(result)}")

            return result, ctx

        except (requests.Timeout, json.JSONDecodeError) as e:
            if attempt == 0:
                print(f"    Zhipu-fallback {type(e).__name__}, retrying...")
                time.sleep(5)
                continue
            raise

    raise RuntimeError("Zhipu-fallback failed after all attempts")
