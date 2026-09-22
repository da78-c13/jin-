#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug login v2 - full response analysis"""
import sys, re, time, base64, json
sys.path.insert(0, r'C:\Users\Administrator\qiangke_zjjhkm')

import requests
from config import LOGIN_URL, PUBLIC_KEY_URL, MAIN_URL, BASE_URL, STUDENT_ID, STUDENT_PASSWORD, REQUEST_TIMEOUT

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
})

# Get login page
r = session.get(LOGIN_URL, timeout=REQUEST_TIMEOUT)

# Extract hidden fields
hidden = {}
for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', r.text, re.I):
    tag = m.group()
    for attr_re in [r'name=["\']([^"\']*)["\']', r'name=\s*([^\s>/]+)']:
        name_m = re.search(attr_re, tag)
        if name_m: break
    if not name_m: continue
    name = name_m.group(1).strip()
    for val_re in [r'value=["\']([^"\']*)["\']', r'value=\s*([^\s>/]+)']:
        val_m = re.search(val_re, tag)
        if val_m: break
    val = val_m.group(1).strip() if val_m else ''
    hidden[name] = val

print(f"Hidden fields count: {len(hidden)}")
for k, v in sorted(hidden.items()):
    print(f"  {k} = [{v}]")

# Get public key
r2 = session.get(f"{PUBLIC_KEY_URL}?time={int(time.time()*1000)}",
    headers={'X-Requested-With': 'XMLHttpRequest'})
key_data = r2.json()

# Encrypt password using rsa library
import rsa
mod_bytes = base64.b64decode(key_data['modulus'])
exp_bytes = base64.b64decode(key_data['exponent'])
pub_key = rsa.PublicKey(
    n=int.from_bytes(mod_bytes, byteorder='big'),
    e=int.from_bytes(exp_bytes, byteorder='big')
)
encrypted = base64.b64encode(rsa.encrypt(STUDENT_PASSWORD.encode('utf-8'), pub_key)).decode('ascii')
print(f"\nEncrypted pwd: {encrypted[:50]}...{encrypted[-20:]}")

# Pre-login checks
session.post(f'{BASE_URL}/xtgl/login_cxDlxgxx.html',
    data={'yhm': STUDENT_ID},
    headers={'X-Requested-With': 'XMLHttpRequest'})
csrf_token_logout = hidden.get('csrfTokenLogout', '')
session.post(f'{BASE_URL}/xtgl/login_logoutAccount.html',
    data={'csrfTokenLogout': csrf_token_logout},
    headers={'X-Requested-With': 'XMLHttpRequest'})

# Submit login with ALL fields
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
    allow_redirects=False)  # DON'T follow redirects!

print(f"\nLogin response: status={r5.status_code}")
print(f"Location header: {r5.headers.get('Location', 'N/A')}")
print(f"Set-Cookie: {r5.headers.get('Set-Cookie', 'N/A')}")

# Check response content for error messages
text = r5.text
print(f"\nResponse length: {len(text)}")

# Search for common error patterns
patterns = [
    (r'错误[：:]\s*([^<.]+)', '错误'),
    (r'失败[：:]\s*([^<.]+)', '失败'),
    (r'alert[^>]*>([^<]*)', 'alert'),
    (r'<div[^>]*id=["\']tips["\'][^>]*>([^<]*)', 'tips div'),
    (r'<span[^>]*id=["\']tips["\'][^>]*>([^<]*)', 'tips span'),
    (r'密码错误', '密码错误'),
    (r'用户名或密码', '用户名或密码'),
]
for pat, desc in patterns:
    m = re.search(pat, text)
    if m:
        val = m.group(1).strip() if m.lastindex else m.group(0)
        print(f"  Found [{desc}]: {val[:200]}")

# If not redirected, show first 1000 chars
if r5.status_code == 200:
    print(f"\nResponse content (first 1000 chars):")
    print(text[:1000])