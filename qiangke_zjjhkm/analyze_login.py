#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze login page structure"""
import urllib.request
import ssl
import re
import sys

ssl._create_default_https_context = ssl._create_unverified_context
req = urllib.request.Request(
    'https://jwxt.zjjhkm.edu.cn/jwglxt/xtgl/login_slogin.html',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
)
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='replace')

print("=== INPUT FIELDS ===")
for m in re.finditer(r'<input[^>]*>', html):
    print(m.group())

print("\n=== FORM TAGS ===")
for m in re.finditer(r'<form[^>]*>', html):
    print(m.group())

print("\n=== ALL SCRIPTS (src=) ===")
for m in re.finditer(r'<script[^>]*src="([^"]+)"', html):
    print(m.group(1))

print("\n=== ONCLICK / SUBMIT HANDLERS ===")
for m in re.finditer(r'(onclick|onsubmit)\s*=\s*"([^"]+)"', html, re.I):
    print(f"{m.group(1)} = {m.group(2)[:100]}")

print("\n=== HIDDEN INPUTS ===")
for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', html):
    print(m.group())

# Check for any login-related JS
print("\n=== LOGIN-RELATED CONTENT ===")
for m in re.finditer(r'(login|Login|LOGIN|yhm|mm\b|password|csrftoken)', html):
    start = max(0, m.start() - 50)
    end = min(len(html), m.end() + 100)
    snippet = html[start:end].replace('\n', ' ').replace('\r', '')
    print(f"...{snippet}...")
    print("---")

# Print full page title/scripts section
print("\n=== PAGE HEAD ===")
head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL)
if head_match:
    head = head_match.group(1)
    for m in re.finditer(r'<script[^>]*>', head):
        print(m.group())