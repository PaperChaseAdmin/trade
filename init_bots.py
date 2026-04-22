"""Run once to initialise data files for all bots."""
import os, json
from datetime import datetime
from bot_profiles import BOT_PROFILES

TS = "2026-04-22T00:00:00Z"

for bot_id, p in BOT_PROFILES.items():
    os.makedirs(f"data/bots/{bot_id}", exist_ok=True)
    pf_path = f"data/bots/{bot_id}/portfolio.json"
    tr_path = f"data/bots/{bot_id}/trades.json"

    if not os.path.exists(pf_path):
        json.dump({
            "bot_id": bot_id, "display_name": p["display_name"],
            "initial_capital": p["initial_capital"],
            "cash": float(p["initial_capital"]), "positions": {},
            "portfolio_history": [{"timestamp": TS, "value": float(p["initial_capital"])}],
            "total_value": float(p["initial_capital"]),
            "total_return_pct": 0.0, "today_pnl": 0.0, "today_pnl_pct": 0.0,
            "today_date": "2026-04-22", "today_start_value": float(p["initial_capital"]),
            "total_trades": 0, "last_updated": TS,
            "last_action": "Initialized — ready to trade"
        }, open(pf_path,"w"), indent=2)
        print(f"  Created portfolio: {bot_id}")

    if not os.path.exists(tr_path):
        json.dump({"bot_id": bot_id, "trades": []}, open(tr_path,"w"), indent=2)
        print(f"  Created trades:    {bot_id}")

# Rebuild leaderboard
bots = []
for bot_id, p in BOT_PROFILES.items():
    pf = json.load(open(f"data/bots/{bot_id}/portfolio.json", encoding="utf-8"))
    bots.append({
        "bot_id": bot_id, "display_name": p["display_name"],
        "avatar": p["avatar"], "bio": p["bio"], "strategy": p["strategy"],
        "risk_level": p["risk_level"], "risk_bar": p["risk_bar"], "color": p["color"],
        "total_value": pf["total_value"], "initial_capital": p["initial_capital"],
        "total_return_pct": 0.0, "total_return_usd": 0.0,
        "today_pnl": 0.0, "today_pnl_pct": 0.0, "total_trades": 0, "rank": 0,
        "last_action": "Initialized", "last_updated": TS,
        "cash": pf["cash"], "positions": {}
    })

for i, b in enumerate(bots): b["rank"] = i + 1
json.dump({"updated_at": TS, "bots": bots}, open("data/leaderboard.json","w"), indent=2)
print(f"\nDone — {len(bots)} bots initialised.")
