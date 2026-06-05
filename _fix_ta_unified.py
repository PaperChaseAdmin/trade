#!/usr/bin/env python3
"""Add .wrap div to Trading Arena and unify page-header"""
path = "/mnt/c/Hermes/paper_trading/index.html"
with open(path) as f:
    c = f.read()

# 1. Add .wrap div after bg-overlay (if not already present)
if '<div class="wrap">' not in c:
    c = c.replace(
        '<div class="bg-overlay"></div>\n\n<nav class="topbar">',
        '<div class="bg-overlay"></div>\n<div class="wrap">\n<nav class="topbar">')
    # Add closing </div> before </body>
    c = c.replace('</body>', '</div>\n</body>')
    print("✅ .wrap div added")
else:
    print("✅ .wrap div already present")

# 2. Fix page-header padding (add padding:28px 0 0 for consistency)
if 'padding:28px 0 0' not in c:
    c = c.replace(
        '<div class="page-header">',
        '<div class="page-header" style="padding:28px 0 0">')
    print("✅ page-header padding added")
else:
    print("✅ page-header padding already set")

# 3. Fix page-sub structure - use data-i18n on the outer div, add live class
old_sub = '''    <div class="page-sub"><span class="live-dot"></span> <span data-i18n="page_sub_trade">20 AI bots · $10,000 each · Real market data · Transparent decisions</span></div>'''
new_sub = '''    <div class="page-sub" data-i18n="page_sub_trade"><span class="live"></span> 20 AI bots · $10,000 each · Real market data · Transparent decisions</div>'''
c = c.replace(old_sub, new_sub)
print("✅ page-sub unified")

# 4. Add .wrap CSS if not present
wrap_css = '.wrap{position:relative;z-index:1}'
if wrap_css not in c:
    # Add after bg-overlay CSS or at end of style block
    c = c.replace('body{background:var(--tv-bg);color:var(--tv-text);',
                  'body{background:var(--tv-bg);color:var(--tv-text);' + wrap_css)
    print("✅ .wrap CSS added")
else:
    print("✅ .wrap CSS already present")

with open(path, "w") as f:
    f.write(c)

# Verify
with open(path) as f:
    final = f.read()
print(f"\n.wrap div: {'<div class=\"wrap\">' in final}")
print(f".wrap /wrap: {'</div>' in final[final.rfind('<div class=\"wrap\">'):final.rfind('</div>')+30]}")
print(f"page-header padding: {'padding:28px 0 0' in final}")
print(f"page-sub unified: {'live\"></span>' in final}")
