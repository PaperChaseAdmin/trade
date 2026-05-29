"""Update DETAIL_TMPL and RECORDS_TMPL in generate_pages.py:
1. Remove lang-switcher from DETAIL_TMPL nav
2. Remove lang-switcher from RECORDS_TMPL nav
3. Remove the switchLang script block
"""

with open('/mnt/c/Hermes/paper_trading/generate_pages.py', 'r', encoding='utf-8') as f:
    content = f.read()

# --- DETAIL_TMPL: Remove lang-switcher (emoji version) ---
old_detail_lang = '''  <div style="flex:1"></div>
  <div class="lang-switcher" style="position:relative">
    <button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="background:var(--tv-surface-2);border:1px solid var(--tv-border-2);border-radius:var(--tv-radius-sm);padding:4px 10px;cursor:pointer;font-size:12px;color:var(--tv-text-2);font-family:var(--tv-font)">🌐 <span data-i18n="nav_lang">Language</span> ▾</button>
    <div style="display:none;position:absolute;top:100%;right:0;background:var(--tv-surface);border:1px solid var(--tv-border);border-radius:var(--tv-radius-sm);min-width:150px;z-index:200;margin-top:4px;overflow:hidden">
      <div onclick="localStorage.setItem('pap_tfav_lang','en');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇬🇧 <span data-i18n="lang_en">English</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','tc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇭🇰 <span data-i18n="lang_tc">繁體中文</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','sc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇨🇳 <span data-i18n="lang_sc">简体中文</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','ja');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇯🇵 <span data-i18n="lang_ja">日本語</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','fr');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇫🇷 <span data-i18n="lang_fr">Français</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','es');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">🇪🇸 <span data-i18n="lang_es">Español</span></div>
    </div>
  </div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login" id="nav-login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register" id="nav-register">Register</a>
  <a class="nav-link" href="/trade/account/" data-i18n="nav_account" id="nav-account" style="display:none">Account</a>
  <a class="nav-link" href="#" onclick="if(window.PaperChaseAuth)PaperChaseAuth.signOut()" data-i18n="nav_logout" id="nav-logout" style="display:none">Log Out</a>
</div></nav>
<script>
function switchLang(lang) {
  if (window.__setLang) window.__setLang(lang);
}
</script>'''

new_detail_nav = '''  <div style="flex:1"></div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login" id="nav-login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register" id="nav-register">Register</a>
  <a class="nav-link" href="/trade/account/" data-i18n="nav_account" id="nav-account" style="display:none">Account</a>
  <a class="nav-link" href="#" onclick="if(window.PaperChaseAuth)PaperChaseAuth.signOut()" data-i18n="nav_logout" id="nav-logout" style="display:none">Log Out</a>
</div></nav>'''

if old_detail_lang in content:
    content = content.replace(old_detail_lang, new_detail_nav)
    print("DETAIL_TMPL: lang-switcher removed")
else:
    print("DETAIL_TMPL: lang-switcher NOT FOUND!")
    # Debug: find the anchor
    idx = content.find('id="nav-login"')
    if idx > 0:
        print("  Found id=nav-login at position", idx)
        print("  Context around it:")
        print(repr(content[idx-50:idx+50]))

# --- RECORDS_TMPL: Remove lang-switcher (HTML entities version) ---
old_records_lang = '''  <div style="flex:1"></div>
  <div class="lang-switcher" style="position:relative">
    <button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="background:var(--tv-surface-2);border:1px solid var(--tv-border-2);border-radius:var(--tv-radius-sm);padding:4px 10px;cursor:pointer;font-size:12px;color:var(--tv-text-2);font-family:var(--tv-font)">&#127760; <span data-i18n="nav_lang">Language</span> &#9662;</button>
    <div style="display:none;position:absolute;top:100%;right:0;background:var(--tv-surface);border:1px solid var(--tv-border);border-radius:var(--tv-radius-sm);min-width:150px;z-index:200;margin-top:4px;overflow:hidden">
      <div onclick="localStorage.setItem('pap_tfav_lang','en');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127468;&#127463; <span data-i18n="lang_en">English</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','tc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127472;&#127475; <span data-i18n="lang_tc">Traditional Chinese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','sc');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127464;&#127475; <span data-i18n="lang_sc">Simplified Chinese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','ja');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127471;&#127477; <span data-i18n="lang_ja">Japanese</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','fr');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127467;&#127479; <span data-i18n="lang_fr">French</span></div>
      <div onclick="localStorage.setItem('pap_tfav_lang','es');location.reload()" style="padding:8px 12px;cursor:pointer;font-size:13px;color:var(--tv-text);transition:background.1s" onmouseover="this.style.background='var(--tv-surface-2)'" onmouseout="this.style.background='transparent'">&#127466;&#127480; <span data-i18n="lang_es">Spanish</span></div>
    </div>
  </div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register">Register</a>
</div></nav>'''

new_records_nav = '''  <div style="flex:1"></div>
  <a class="nav-link" href="/trade/login/" data-i18n="nav_login">Log In</a>
  <a class="nav-link" href="/trade/register/" data-i18n="nav_register">Register</a>
</div></nav>'''

if old_records_lang in content:
    content = content.replace(old_records_lang, new_records_nav)
    print("RECORDS_TMPL: lang-switcher removed")
else:
    print("RECORDS_TMPL: lang-switcher NOT FOUND!")
    idx = content.find('&#127760;')
    if idx > 0:
        print("  Found &#127760; at position", idx)
        print("  Context:")
        print(repr(content[idx-30:idx+50]))

with open('/mnt/c/Hermes/paper_trading/generate_pages.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone writing generate_pages.py")
