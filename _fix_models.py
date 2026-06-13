#!/usr/bin/env python3
"""Fix all 20 bot models in bot_profiles.py"""
import re

PATH = "/mnt/c/Hermes/paper_trading/bot_profiles.py"
with open(PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Model assignments: bot_id -> (primary, fallback)
MODELS = {
    # Qwen-Coder primary -> Kimi fallback (7 bots — best at JSON/structured output)
    "elon":    ("qwen", "kimi"),
    "nancy":   ("qwen", "kimi"),
    "tony":    ("qwen", "kimi"),
    "satoshi": ("qwen", "kimi"),
    "thanos":  ("qwen", "kimi"),
    "jerome":  ("qwen", "kimi"),
    "jamie":   ("qwen", "kimi"),
    # Kimi primary -> Qwen fallback (6 bots — good general purpose)
    "warren":  ("kimi", "qwen"),
    "donald":  ("kimi", "qwen"),
    "cathie":  ("kimi", "qwen"),
    "ray":     ("kimi", "qwen"),
    "george":  ("kimi", "qwen"),
    "michael": ("kimi", "qwen"),
    # Nemotron primary -> Qwen fallback (7 bots — keep nemotron for reasoning-heavy)
    "kevin":   ("nemotron", "qwen"),
    "gordon":  ("nemotron", "qwen"),
    "jordan":  ("nemotron", "qwen"),
    "patrick": ("nemotron", "qwen"),
    "scrooge": ("nemotron", "qwen"),
    "yoda":    ("nemotron", "qwen"),
    "xi":      ("nemotron", "qwen"),
}

# Pattern: find bot_id "...", then find the model line shortly after
for bot_id, (primary, fallback) in MODELS.items():
    pattern = f'"{bot_id}"' + r'\s*:\s*\{'
    match = re.search(pattern, content)
    if not match:
        print(f"ERROR: {bot_id} not found!")
        continue
    
    # Find model + fallback lines after the bot_id
    model_match = re.search(
        r'"model":\s*"openrouter/([^"]+)"',
        content[match.start():match.start()+500]
    )
    if not model_match:
        print(f"ERROR: model not found near {bot_id}")
        continue
    
    old_model = model_match.group(0)
    new_model = f'"model": "openrouter/{primary}"'
    
    fb_match = re.search(
        r'"fallback_model":\s*"openrouter/([^"]+)"',
        content[match.start():match.start()+600]
    )
    if not fb_match:
        print(f"ERROR: fallback not found near {bot_id}")
        continue
    
    old_fallback = fb_match.group(0)
    new_fallback = f'"fallback_model": "openrouter/{fallback}"'
    
    content = content.replace(old_model, new_model, 1)
    content = content.replace(old_fallback, new_fallback, 1)
    print(f"  {'✅' if primary else '❌'} {bot_id:10s} → {primary:10s} (fb: {fallback})")

# Update docstring header
content = content.replace(
    '  "openrouter/minimax"  -> MiniMax M2.5 (free via OpenRouter) - primary\n  "openrouter/ling"     -> InclusionAI Ling 2.6 1T (free via OpenRouter) - primary\n  "openrouter/nemotron" -> NVIDIA Nemotron 3 Super 120B (free via OpenRouter) - primary',
    '  "openrouter/qwen"      -> Qwen3-Coder (free via OpenRouter, 1M ctx, best JSON)\n  "openrouter/kimi"      -> MoonshotAI Kimi K2.6 (free via OpenRouter, 262K ctx)\n  "openrouter/nemotron" -> NVIDIA Nemotron 3 Super 120B (free via OpenRouter, 1M ctx)'
)

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
v = {'qwen': 0, 'kimi': 0, 'nemotron': 0, 'minimax': 0}
for line in content.split('\n'):
    for m in v:
        if f'"model": "openrouter/{m}"' in line:
            v[m] += 1

print(f"\nFinal distribution: qwen={v['qwen']}, kimi={v['kimi']}, nemotron={v['nemotron']}")
if v['minimax']:
    print(f"WARNING: {v['minimax']} minimax references remain!")
else:
    print("Clean: no minimax")
