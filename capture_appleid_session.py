#!/usr/bin/env python3
"""
Interactive Apple ID login capture for HME bot (terminal-driven).

Flow (matches user preference: login email+password auto, user types 2FA in terminal):
  * Prompt email + password + 2FA code via terminal (not stored on disk).
  * Drive account.apple.com in Xvfb browser: autofill email, password, submit 2FA.
  * Solve/click through, land on Hide My Email page.
  * Capture appleid.apple.com session cookies + apiKey (from /account/manage) + scnt.
  * Save to /root/icloud-hme/appleid_session.json
"""
import json, sys, time, getpass, os, re
from playwright.sync_api import sync_playwright

OUT = '/root/icloud-hme/appleid_session.json'
UA  = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36')

def prompt(label, secret=False):
    sys.stdout.write(label); sys.stdout.flush()
    return getpass.getpass('') if secret else input('').strip()

# ---- gather credentials from terminal ----
email = prompt('Apple ID email: ')
if not email:
    print('no email, abort'); sys.exit(1)
password = prompt('Password: ', secret=True)
if not password:
    print('no password, abort'); sys.exit(1)

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width':1366,'height':850}, user_agent=UA, locale='en-US')
    page = ctx.new_page()
    captured = {'api_key': None, 'scnt': None}

    def on_resp(r):
        try:
            url = r.url
            if '/account/manage' in url or url.startswith('https://appleid.apple.com/api'):
                ct = r.headers.get('content-type','')
                if 'json' in ct and r.status == 200:
                    try:
                        body = r.json()
                        if isinstance(body, dict) and body.get('apiKey'):
                            captured['api_key'] = body['apiKey']
                            print('  [capture] apiKey set')
                        rh = r.headers.get('scnt')
                        if rh:
                            captured['scnt'] = rh
                    except Exception:
                        pass
        except Exception:
            pass
    page.on('response', on_resp)

    # ---- go to signin ----
    page.goto('https://account.apple.com/account/manage/section/privacy',
              wait_until='domcontentloaded', timeout=60000)

    # click "Sign In" if on landing
    for _ in range(3):
        try:
            page.get_by_role('link', name=re.compile(r'sign\s?in', re.I)).first.click(timeout=5000)
            break
        except Exception:
            try:
                page.get_by_role('button', name=re.compile(r'sign\s?in', re.I)).first.click(timeout=5000)
                break
            except Exception:
                break

    time.sleep(3)

    # ---- email ----
    filled = False
    for sel in ['input[type=email]', '#account_name_text_field', 'input[name=accountName]',
                'input[autocomplete=username]', 'input[type=text]', 'input[name=login]']:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(email); filled = True; break
        except Exception:
            continue
    if not filled:
        print('[-] could not find email field; do manual from here. Press Enter when at HME.')
        try: input('>>> Press Enter after manual login...')
        except EOFError: time.sleep(180)

    # click continue / submit
    for btn in ['//button[contains(.,"Continue")]', '//input[@type="submit"]',
                '//button[@type="submit"]', '//a[contains(.,"Continue")]']:
        try:
            page.locator(btn).first.click(timeout=3000); break
        except Exception:
            continue

    time.sleep(4)

    # ---- password ----
    pv = re.sub(r'[^A-Za-z0-9_.@+-]', '', email)  # not used for pwd
    pwd_filled = False
    for sel in ['input[type=password]', '#password_text_field', 'input[name=password]',
                'input[autocomplete=current-password]']:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(password); pwd_filled = True; break
        except Exception:
            continue
    if not pwd_filled:
        print('[-] password not auto-filled; fill manually, then continue.')
    for btn in ['//button[contains(.,"Continue")]', '//button[contains(.,"Sign In")]',
                '//button[@type="submit"]', '//input[@type="submit"]']:
        try:
            page.locator(btn).first.click(timeout=3000); break
        except Exception:
            continue

    # ---- 2FA ----
    print('[*] Waiting for 2FA prompt... check your device')
    code = ''
    for _ in range(6):
        code = prompt('2FA code (6 digits): ')
        code = code.strip()
        if re.fullmatch(r'\d{6}', code):
            break
        print('  need 6 digits')
    if not re.fullmatch(r'\d{6}', code):
        print('[-] no valid 2FA entered; continuing (may fail)')
    for sel in ['input[type=code]', 'input[type=tel]', 'input[name=securityCode]',
                'input[autocomplete=one-time-code]', '.otp-input input', 'input[inputmode=numeric]']:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(code); break
        except Exception:
            continue
    for btn in ['//button[contains(.,"Continue")]', '//button[contains(.,"Verify")]',
                '//button[contains(.,"Sign In")]', '//button[@type="submit"]']:
        try:
            page.locator(btn).first.click(timeout=3000); break
        except Exception:
            continue

    print('[*] logging in... waiting for HME page')

    # wait until we reach privacy/hme OR manage page
    reached = False
    for _ in range(30):
        time.sleep(3)
        url = page.url
        if 'privacy' in url or 'manage' in url and 'signin' not in url:
            reached = True; break
        if '2fa' in url.lower() or 'verify' in url.lower():
            pass
        if 'hme' in url:
            reached = True; break
        # if still on login, maybe need more
    time.sleep(5)

    # ensure HME endpoint fetch for apiKey
    if not captured['api_key']:
        try:
            captured['api_key'] = page.evaluate("""async () => {
                const r = await fetch('https://appleid.apple.com/account/manage', {headers:{'Accept':'application/json'}});
                const j = await r.json();
                return j.apiKey || null;
            }""")
            print('[*] apiKey via fetch:', (captured['api_key'][:8]+'...') if captured['api_key'] else None)
        except Exception as e:
            print('[*] fetch apiKey failed:', e)

    # capture cookies
    cookies = ctx.cookies()
    apple_cookies = [c for c in cookies if 'apple.com' in c.get('domain','')]
    print(f'[*] captured {len(apple_cookies)} apple cookies; reached={reached}')

    out = {
        'captured_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'apple_id': email,
        'api_key': captured['api_key'],
        'scnt': captured['scnt'],
        'final_url': page.url,
        'cookies': apple_cookies,
        'user_agent': UA,
    }
    json.dump(out, open(OUT,'w'), indent=2)
    print(f'[*] saved -> {OUT}')
    try:
        page.screenshot(path='/tmp/aa_login_done.png')
    except Exception:
        pass
    b.close()
