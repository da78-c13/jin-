#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal login test - just the essentials"""
import sys, time, base64, re
import requests as r

s = r.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})

BASE = 'https://jwxt.zjjhkm.edu.cn/jwglxt'

# Step 1: Get login page
resp = s.get(f'{BASE}/xtgl/login_slogin.html', timeout=15)
print(f'Page loaded: {resp.status_code}, length={len(resp.text)}')

# Extract csrf token
csrftoken = ''
m = re.search(r'name="csrftoken"\s+value="([^"]+)"', resp.text)
if m:
    csrftoken = m.group(1)
    print(f'CSRF token: {csrftoken[:30]}...')

# Step 2: Get public key
resp2 = s.get(f'{BASE}/xtgl/login_getPublicKey.html?time={int(time.time()*1000)}',
    headers={'X-Requested-With': 'XMLHttpRequest'})
key_data = resp2.json()
print(f'Got public key: modulus={len(key_data["modulus"])} chars')

# Step 3: Encrypt password
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

mod = int.from_bytes(base64.b64decode(key_data['modulus']), 'big')
exp = int.from_bytes(base64.b64decode(key_data['exponent']), 'big')
rsa_key = RSA.construct((mod, exp))
cipher = PKCS1_v1_5.new(rsa_key)
enc_pwd = base64.b64encode(cipher.encrypt(b'Jiusi258')).decode()
print(f'Encrypted pwd: {enc_pwd[:40]}...{enc_pwd[-20:]}')

# Step 4: Try login with minimal params
login_data = {
    'yhm': '202610122040205',
    'mm': enc_pwd,
    'csrftoken': csrftoken,
}

login_resp = s.post(
    f'{BASE}/xtgl/login_slogin.html?time={int(time.time()*1000)}',
    data=login_data,
    headers={
        'Referer': f'{BASE}/xtgl/login_slogin.html',
        'Origin': BASE,
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    allow_redirects=False
)
print(f'\nLogin: status={login_resp.status_code}')
print(f'Location: {login_resp.headers.get("Location", "none")}')
print(f'Cookies: {dict(s.cookies)}')

# Check response text for error messages
text = login_resp.text
# Check if it redirects (success)
if login_resp.status_code == 302:
    print('REDIRECT - login may have succeeded!')
    loc = login_resp.headers.get('Location', '')
    print(f'Redirect to: {loc}')
elif login_resp.status_code == 200:
    # Look for error messages
    for kw in ['错误', '失败', '锁定', '密码', '成功']:
        count = text.count(kw)
        if count > 0:
            # Find the context
            for m in re.finditer(f'.{{0,30}}{kw}.{{0,60}}', text):
                print(f'  [{kw}] ...{m.group().strip()}...')
                break
    
    # Show a piece of the page title
    title_m = re.search(r'<title>([^<]+)</title>', text)
    if title_m:
        print(f'Title: {title_m.group(1)}')