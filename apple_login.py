#!/usr/bin/env python3
"""Apple Account login via Playwright + capture HME session (robust, iframe-aware).
The Apple sign-in form lives inside an idmsa.apple.com iframe. This script:
  - opens account.apple.com, clicks Sign In
  - fills email + password inside the idmsa iframe
  - prompts for 2FA interactively
  - waits until an auth cookie is present, then captures session + HME list
Reads APPLE_EMAIL / APPLE_PASSWORD from environment.
"""
import os, json, sys, time, re
from pathlib import Path
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get('APPLE_EMAIL', '').strip()
PASSWORD = os.environ.get('APPLE_PASSWORD', '').strip()
OUT = os.environ.get('APPLE_SESSION_OUT', '/tmp/apple_session.json')

if not EMAIL: sys.exit('ERROR: APPLE_EMAIL env not set')
if not PASSWORD: sys.exit('ERROR: APPLE_PASSWORD env not set')

AUTH_COOKIES = ['X-APPLE-DS-WEB-SESSION-TOKEN','dssid','asid','X-APPLE-WEBAUTH-USER']

def has_auth(cookies):
    return any(c['name'] in AUTH_COOKIES for c in cookies)

def find_auth_frame(page):
    """Return the idmsa iframe (or main if none)."""
    for fr in page.frames:
        if 'idmsa.apple.com' in fr.url or 'appleauth' in fr.url:
            return fr
    return page.main_frame

def fill_in_frame(fr, email_sel, val):
    for sel in email_sel:
        try:
            loc = fr.locator(sel).first
            if loc.is_visible(timeout=2500):
                loc.click(); loc.fill(val)
                return sel
        except Exception:
            continue
    return None

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
            args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        ctx = browser.new_context(viewport={'width':1280,'height':900},
            locale='en-US', timezone_id='Asia/Jakarta')
        page = ctx.new_page()

        scnt = {'v': None}
        def on_resp(resp):
            if resp.headers.get('scnt'):
                scnt['v'] = resp.headers['scnt']
        page.on('response', on_resp)

        print("[*] Opening account.apple.com ...")
        page.goto('https://account.apple.com/', wait_until='domcontentloaded', timeout=45000)
        time.sleep(4)

        # click Sign In to mount the idmsa iframe
        try:
            page.evaluate("Array.from(document.querySelectorAll('a')).find(a=>/sign\\s?in/i.test(a.textContent))?.click()")
            print("[*] clicked Sign In")
        except Exception as e:
            print("[-] click sign in failed:", e)
        time.sleep(7)

        # if already authed, skip
        ck = ctx.cookies()
        if has_auth(ck):
            print("[+] Already authenticated.")
        else:
            fr = find_auth_frame(page)
            print("[*] auth frame:", fr.url[:120])

            # --- EMAIL ---
            print("[*] filling email ...")
            em = fill_in_frame(fr, ['input[type="email"]','input[placeholder*="mail" i]',
                                    '#account_name_text_field','input[name="accountName"]','input[type="text"]'], EMAIL)
            print("   email field:", em or "NOT FOUND")
            if em:
                for btn in ['button:has-text("Continue")','input[type="submit"]','button[type="submit"]']:
                    try:
                        fr.locator(btn).first.click(timeout=2500); break
                    except Exception:
                        continue
                time.sleep(4)

            # --- PASSWORD ---
            print("[*] filling password ...")
            pw = fill_in_frame(fr, ['input[type="password"]','#password_text_field','input[name="password"]',
                                    'input[autocomplete="current-password"]'], PASSWORD)
            print("   password field:", pw or "NOT FOUND")
            if pw:
                for btn in ['button:has-text("Continue")','button:has-text("Sign In")',
                            'input[type="submit"]','button[type="submit"]']:
                    try:
                        fr.locator(btn).first.click(timeout=2500); break
                    except Exception:
                        continue
            time.sleep(4)

        # --- wait for auth + 2FA loop ---
        print("[*] Waiting for authentication (2FA if needed) ...")
        gave_2fa = False
        for i in range(45):
            time.sleep(3)
            ck = ctx.cookies()
            if has_auth(ck):
                print("[+] Authenticated!")
                break
            fr = find_auth_frame(page)
            lower = fr.content().lower()[:3000] if fr else ""
            if not gave_2fa and any(k in lower for k in ['verification code','enter the code','two-factor',
                                                         '6-digit','six-digit','trusted device','security code']):
                # DEBUG: dump actual input structure in the 2FA frame
                try:
                    dbg = fr.evaluate("""() => Array.from(document.querySelectorAll('input')).map(i => ({
                        type:i.type, name:i.name, id:i.id, cls:i.className, maxlen:i.maxLength,
                        ph:i.placeholder, autocomp:i.autocomplete, aria:i.getAttribute('aria-label')
                    }))""")
                    print("  [2FA inputs]:", json.dumps(dbg))
                except Exception as e:
                    print("  [2FA dump fail]:", e)
                code = input(">>> Enter 2FA code: ").strip()
                gave_2fa = True
                filled = False
                # Apple 2FA auto-advances: focus first box, type full code via keyboard
                for sel in ['input.form-security-code-input','input[type="tel"]','input[inputmode="numeric"]',
                            'input[name*="code" i]','input[autocomplete="one-time-code"]']:
                    try:
                        locs = fr.locator(sel)
                        if locs.count() >= 6:
                            locs.nth(0).click()
                            page.keyboard.type(code, delay=120)
                            filled = True
                            break
                        else:
                            loc = locs.first
                            if loc.is_visible(timeout=1500):
                                loc.click(); loc.fill(code); filled = True
                                break
                    except Exception:
                        continue
                if not filled:
                    try:
                        page.keyboard.type(code, delay=120)
                        filled = True
                    except Exception:
                        pass
                for btn in ['button:has-text("Continue")','button:has-text("Verify")',
                            'button:has-text("Trust")','button:has-text("Sign In")','button[type="submit"]']:
                    try:
                        fr.locator(btn).first.click(timeout=2500)
                        break
                    except Exception:
                        continue
                time.sleep(3)
                # handle "Trust this browser" prompt after successful 2FA
                try:
                    tframe = find_auth_frame(page)
                    tlow = tframe.content().lower()[:1500]
                    if 'trust this browser' in tlow or 'trust' in tlow:
                        for btn in ['button:has-text("Trust")','button:has-text("Continue")']:
                            try:
                                tframe.locator(btn).first.click(timeout=2000)
                                break
                            except Exception:
                                continue
                except Exception:
                    pass
                continue
            if i % 8 == 0:
                print(f"  ...waiting ({i*3}s) url={page.url} cookies={[c.get('name') for c in ck]}")

        # --- capture session ---
        time.sleep(3)
        ck = ctx.cookies()
        authed = has_auth(ck)
        data = {
            'email': EMAIL,
            'captured_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'authed': authed,
            'scnt': scnt['v'],
            'cookies': ck,
            'url': page.url,
        }
        Path(OUT).parent.mkdir(parents=True, exist_ok=True)
        with open(OUT,'w') as f: json.dump(data,f,indent=2)
        print(f"[+] Session -> {OUT} | authed={authed} | scnt={'Y' if data['scnt'] else 'N'} | cookies={len(ck)}")
        page.screenshot(path='/tmp/apple_postlogin.png', full_page=False)
        print("[+] screenshot: /tmp/apple_postlogin.png")

        if authed:
            try:
                r = page.evaluate("""async () => {
                    const lst = await fetch('https://appleid.apple.com/account/manage/email/private',{headers:{'Accept':'application/json'}});
                    const js = await lst.json();
                    return {list: js.privateEmailList||[], forward: js.forwardToEmailAddress||null};
                }""")
                print("[+] HME list:", json.dumps(r)[:400])
            except Exception as e:
                print("[-] HME fetch failed:", e)
        browser.close()

if __name__=='__main__':
    main()
