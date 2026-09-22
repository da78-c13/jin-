#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug login - check what the server returns"""
import sys, re, time, base64, json
sys.path.insert(0, r'C:\Users\Administrator\qiangke_zjjhkm')

import requests
from config import LOGIN_URL, PUBLIC_KEY_URL, MAIN_URL, BASE_URL, STUDENT_ID, STUDENT_PASSWORD, REQUEST_TIMEOUT

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
})

# Step 1: Get login page
r = session.get(LOGIN_URL, timeout=REQUEST_TIMEOUT)
print(f"Step1: status={r.status_code}, cookies={dict(session.cookies)}")

# Extract hidden fields
hidden = {}
for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', r.text, re.I):
    tag = m.group()
    name_m = re.search(r'name=["\']([^"\']*)["\']', tag)
    if not name_m: continue
    name = name_m.group(1)
    val_m = re.search(r'value=["\']([^"\']*)["\']', tag)
    val = val_m.group(1) if val_m else ''
    hidden[name] = val

print(f"Hidden fields: {json.dumps(hidden, indent=2)}")

# Step 2: Get public key
r2 = session.get(f"{PUBLIC_KEY_URL}?time={int(time.time()*1000)}",
    headers={'X-Requested-With': 'XMLHttpRequest'})
print(f"Step2: status={r2.status_code}, key={r2.text[:100]}")

# Step 3: Encrypt password
import rsa
key_data = r2.json()
mod_bytes = base64.b64decode(key_data['modulus'])
exp_bytes = base64.b64decode(key_data['exponent'])
pub_key = rsa.PublicKey(
    n=int.from_bytes(mod_bytes, byteorder='big'),
    e=int.from_bytes(exp_bytes, byteorder='big')
)
encrypted = base64.b64encode(rsa.encrypt(STUDENT_PASSWORD.encode('utf-8'), pub_key)).decode('ascii')
print(f"Step3: encrypted_pwd len={len(encrypted)}")

# Step 4: Pre-login checks
# 4a: login_cxDlxgxx.html
r3 = session.post(f'{BASE_URL}/xtgl/login_cxDlxgxx.html',
    data={'yhm': STUDENT_ID},
    headers={'X-Requested-With': 'XMLHttpRequest'})
print(f"Step4a (login_cxDlxgxx): status={r3.status_code}, body={r3.text[:200]}")

# 4b: login_logoutAccount.html
csrf_token_logout = hidden.get('csrfTokenLogout', '')
r4 = session.post(f'{BASE_URL}/xtgl/login_logoutAccount.html',
    data={'csrfTokenLogout': csrf_token_logout},
    headers={'X-Requested-With': 'XMLHttpRequest'})
print(f"Step4b (logout): status={r4.status_code}, body={r4.text[:200]}")

# Step 5: Submit login form with ALL hidden fields
login_data = dict(hidden)
login_data['yhm'] = STUDENT_ID
login_data['mm'] = encrypted

login_url = f"{LOGIN_URL}?time={int(time.time()*1000)}"
r5 = session.post(login_url, data=login_data,
    headers={
        'Referer': LOGIN_URL,
        'Origin': BASE_URL,
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    allow_redirects=True)
print(f"\nStep5: status={r5.status_code}, url={r5.url}")
print(f"Response text (first 500 chars): {r5.text[:500]}")
print(f"Response cookies: {dict(session.cookies)}")

# Check if success
if 'index' in r5.url or 'main' in r5.url:
    print("\n✓ LOGIN SUCCESS!")
elif '错误' in r5.text or '失败' in r5.text:
    # Try to find error message
    err_m = re.search(r'错误[：:]\s*([^<]+)', r5.text)
    if err_m: print(f"Error: {err_m.group(1)}")
    err_m = re.search(r'<div[^>]*class=["\']error["\'][^>]*>([^<]+)', r5.text)
    if err_m: print(f"Error div: {err_m.group(1)}")