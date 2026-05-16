#!/usr/bin/env python3
"""
Polymarket Scanner Module
Fetches markets from Gamma API, analyzes with heuristics + OpenRouter AI.
"""
import os, json, requests, ast
from datetime import datetime

GAMMA_API = "https://gamma-api.polymarket.com"
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "polymarket")

TAGS = ["politics", "crypto", "finance", "news", "science"]


def fetch_markets():
    """Fetch active markets from all categories."""
    seen = set()
    results = []
    for tag in TAGS:
        try:
            url = f"{GAMMA_API}/events?limit=25&closed=false&tag={tag}&withMinimalMarkets=true"
            resp = requests.get(url, timeout=10)
            if not resp.ok:
                continue
            for event in resp.json():
                for m in event.get("markets", []):
                    mid = m.get("conditionId", m.get("id", ""))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    
                    prices = m.get("outcomePrices", '["0","1"]')
                    if isinstance(prices, str):
                        prices = ast.literal_eval(prices)
                    if len(prices) < 2:
                        continue
                    yes = float(prices[0])
                    no = float(prices[1])
                    if (yes == 0 and no == 1) or (yes == 1 and no == 0):
                        continue
                    
                    results.append({
                        "id": mid,
                        "question": m.get("question", ""),
                        "outcome": m.get("outcome", ""),
                        "yes_price": round(yes, 4),
                        "no_price": round(no, 4),
                        "end_date": event.get("endDate", ""),
                        "event_title": event.get("title", ""),
                        "tag": tag,
                        "volume": float(m.get("volume", 0)),
                        "liquidity": float(m.get("liquidity", 0)),
                        "volume_24h": float(m.get("volume24hr", 0)),
                    })
        except:
            pass
    return results


def analyze_heuristic(m):
    """Local heuristic analysis."""
    q = m.get("question", "").lower()
    tag = m.get("tag", "").lower()
    yes_price = m.get("yes_price", 0)
    end_str = m.get("end_date", "")
    
    score = 0
    reasons = []
    
    if end_str:
        try:
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            days = (end - datetime.now().astimezone()).days
            if days < 0:
                score -= 30
                reasons.append(f"Past end ({abs(days)}d)")
            elif days < 7:
                score += 15
                reasons.append(f"Resolves in {days}d")
            elif days < 30:
                score += 10
                reasons.append(f"Resolves in {days}d")
        except:
            pass
    
    if any(k in q for k in ["will", "vote", "meet", "confirmed", "scheduled", "announced"]):
        score += 10
        reasons.append("Scheduled event")
    if "by " in q and any(c.isdigit() for c in q):
        score += 5
        reasons.append("Fixed deadline")
    if yes_price >= 0.95:
        score += 10
    elif yes_price >= 0.90:
        score += 5
    if m.get("volume", 0) > 10000:
        score += 5
        reasons.append("High volume")
    
    recommand = score >= 15
    return {
        "score": score,
        "reasons": "; ".join(reasons),
        "recommend": recommand,
        "verdict": "✅ Yes" if recommand else "⚠️ Review"
    }


def analyze_with_ai(m, openrouter_key=None):
    """Use OpenRouter AI to analyze whether this market is a good bet."""
    key = openrouter_key or OPENROUTER_KEY
    if not key:
        return {"error": "No OpenRouter key", "ai_analysis": "", "ai_outlook": "neutral", "ai_confidence": 0}
    
    question = m["question"]
    yes_pct = m["yes_price"] * 100
    end_date = m["end_date"] or "No end date"
    volume = f"${m['volume']:,.0f}" if m['volume'] else "Low"
    
    prompt = f"""Analyze this prediction market bet. Is it near-certain (>90% chance)?

Question: {question}
Current Yes%: {yes_pct:.1f}%
End Date: {end_date}
Volume: {volume}

Reply with exactly this JSON (no other text):
{{"outlook":"yes","confidence":95,"rationale":"one short reason"}}
Replace yes with no/neutral and adjust numbers. Only say yes+confidence>90 if truly near-certain."""
    
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://paperchase.online",
            },
            json={
                "model": "nvidia/nemotron-3-nano-30b-a3b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=15,
        )
        if resp.ok:
            text = resp.json()["choices"][0]["message"]["content"]
            # Extract JSON
            import re
            js = re.search(r'\{.*\}', text, re.DOTALL)
            if js:
                data = json.loads(js.group())
                return {
                    "ai_outlook": data.get("outlook", "neutral"),
                    "ai_confidence": data.get("confidence", 0),
                    "ai_analysis": data.get("rationale", ""),
                    "ai_should_bet": data.get("should_bet", False),
                    "ai_max_bet": data.get("max_bet", 1),
                }
    except:
        pass
    return {"ai_outlook": "neutral", "ai_confidence": 0, "ai_analysis": "", "ai_should_bet": False, "ai_max_bet": 1}


def scan(use_ai=True):
    """Full scan: fetch + analyze + AI."""
    markets = fetch_markets()
    results = []
    
    for m in markets:
        h = analyze_heuristic(m)
        m.update({"heuristic": h, "ai": {}})
        
        if use_ai and h["score"] >= 15:  # Only AI-analyze the most promising ones
            ai = analyze_with_ai(m)
            m["ai"] = ai
        
        results.append(m)
    
    # Sort: recommended first, then by yes_price desc
    results.sort(key=lambda x: (x["heuristic"]["score"] >= 15, x["yes_price"]), reverse=True)
    
    # Save to file
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "scan_results.json"), "w") as f:
        json.dump({
            "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_markets": len(results),
            "markets": results,
        }, f, indent=2)
    
    return results


if __name__ == "__main__":
    r = scan(use_ai=True)
    print(f"Scanned {len(r)} markets")
    for m in r[:5]:
        h = m["heuristic"]
        ai = m.get("ai", {})
        ai_str = f" | AI: {ai.get('ai_outlook','N/A')} ({ai.get('ai_confidence',0)}%)" if ai.get("ai_analysis") else ""
        print(f"  {h['verdict']} | {m['yes_price']*100:.1f}%{ai_str} | {m['question'][:55]}")
