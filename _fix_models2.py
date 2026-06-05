import os, json

path = "/mnt/c/Hermes/paper_trading/bot_profiles.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Replace all "fallback_model": "openrouter/minimax" -> "fallback_model": "openrouter/qwen"
content = content.replace('"fallback_model": "openrouter/minimax"', '"fallback_model": "openrouter/qwen"')

# Step 2: For each bot, change model and optionally fallback
# Format: for each bot, find the model line, change it
# All bots currently have model = openrouter/nemotron

# Define per-bot changes: bot_id -> (new_primary, new_fallback or None to keep)
# Use None for fallback to keep current (qwen which we just set)
CHANGES = {
    # Qwen primary -> Kimi fallback
    "elon":    ("qwen", "kimi"),
    "nancy":   ("qwen", "kimi"),
    "tony":    ("qwen", "kimi"),
    "satoshi": ("qwen", "kimi"),
    "thanos":  ("qwen", "kimi"),
    "jerome":  ("qwen", "kimi"),
    "jamie":   ("qwen", "kimi"),
    # Kimi primary -> Qwen fallback (keep qwen)
    "warren":  ("kimi", None),
    "donald":  ("kimi", None),
    "cathie":  ("kimi", None),
    "ray":     ("kimi", None),
    "george":  ("kimi", None),
    "michael": ("kimi", None),
    # Nemotron primary -> Qwen fallback (keep nemotron model, already qwen fallback)
    "kevin":   (None, None),
    "gordon":  (None, None),
    "jordan":  (None, None),
    "patrick": (None, None),
    "scrooge": (None, None),
    "yoda":    (None, None),
    "xi":      (None, None),
}

for bot_id, (new_model, new_fallback) in CHANGES.items():
    # Find this bot's model line
    marker = f'"bot_id": "{bot_id}"'
    pos = content.find(marker)
    if pos < 0:
        print(f"ERROR: {bot_id} not found")
        continue
    
    # Search from pos for the model line
    model_search_start = content.find('"model": "openrouter/', pos)
    if model_search_start < 0 or model_search_start > pos + 800:
        print(f"ERROR: model not found for {bot_id}")
        continue
    
    model_line_end = content.index('\n', model_search_start)
    old_model_line = content[model_search_start:model_line_end]
    
    if new_model:
        new_model_line = f'"model": "openrouter/{new_model}"'
        content = content[:model_search_start] + new_model_line + content[model_line_end:]
        print(f"  {bot_id:10s} model: nemotron -> {new_model}")
    
# Step 3: For qwen-primary bots, also change fallback to kimi
for bot_id in ["elon", "nancy", "tony", "satoshi", "thanos", "jerome", "jamie"]:
    marker = f'"bot_id": "{bot_id}"'
    pos = content.find(marker)
    if pos < 0: continue
    
    fb_start = content.find('"fallback_model": "openrouter/', pos)
    if fb_start < 0 or fb_start > pos + 800:
        continue
    fb_end = content.index('\n', fb_start)
    old_fb = content[fb_start:fb_end]
    new_fb = f'"fallback_model": "openrouter/kimi"'
    content = content[:fb_start] + new_fb + content[fb_end:]
    print(f"  {bot_id:10s} fallback: qwen -> kimi")

# Step 4: Update docstring header
old_header = '  "openrouter/minimax"  -> MiniMax M2.5 (free via OpenRouter) - primary\n  "openrouter/ling"     -> InclusionAI Ling 2.6 1T (free via OpenRouter) - primary\n  "openrouter/nemotron" -> NVIDIA Nemotron 3 Super 120B (free via OpenRouter) - primary'
new_header = '  "openrouter/qwen"      -> Qwen3-Coder (free via OpenRouter, 1M ctx) - primary\n  "openrouter/kimi"      -> MoonshotAI Kimi K2.6 (free via OpenRouter, 262K ctx) - primary\n  "openrouter/nemotron" -> NVIDIA Nemotron 3 Super 120B (free via OpenRouter, 1M ctx) - primary'
content = content.replace(old_header, new_header)

content = content.replace(
    '  Each bot has a DIFFERENT fallback model from its primary (3 sources rotate).',
    '  Each bot has a DIFFERENT provider as fallback for maximum resilience.')

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
print("\n=== VERIFICATION ===")
for m in ["qwen", "kimi", "nemotron"]:
    cnt = content.count(f'"model": "openrouter/{m}"')
    print(f"  model={m}: {cnt}")

for m in ["qwen", "kimi", "nemotron"]:
    cnt = content.count(f'"fallback_model": "openrouter/{m}"')
    print(f"  fallback={m}: {cnt}")

remaining = []
for m in ["minimax", "ling"]:
    if m in content:
        remaining.append(m)
if remaining:
    print(f"  WARNING: still present: {remaining}")
else:
    print("  Clean: no minimax/ling references")
