#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
环境检查脚本 - 检查依赖是否安装完整
"""

import sys
import importlib

required_packages = {
    'requests': 'requests',
    'rsa': 'rsa',
    'dotenv': 'python-dotenv',
}

optional_packages = {}

print("=" * 50)
print("浙江金华科贸职业技术学院 - 抢课工具")
print("环境检查")
print("=" * 50)

print(f"\nPython 版本: {sys.version}")
print(f"Python 路径: {sys.executable}")

print("\n--- 必需依赖检查 ---")
all_ok = True
for module_name, package_name in required_packages.items():
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', '（已安装）')
        print(f"  ✓ {package_name}: {version}")
    except ImportError:
        print(f"  ✗ {package_name}: 未安装")
        print(f"       请执行: pip install {package_name}")
        all_ok = False

print("\n--- 可选依赖检查 ---")
for module_name, package_name in optional_packages.items():
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', '（已安装）')
        print(f"  ✓ {package_name}: {version}")
    except ImportError:
        print(f"  - {package_name}: 未安装（可选）")

print("\n--- 配置文件检查 ---")
import os
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print("  ✓ .env 文件存在")
    # 检查是否配置了学号和密码
    from dotenv import load_dotenv
    load_dotenv(env_path)
    student_id = os.getenv('STUDENT_ID')
    student_pwd = os.getenv('STUDENT_PASSWORD')
    if student_id:
        print(f"  ✓ 学号已配置: {student_id}")
    else:
        print("  ✗ 学号未配置")
        all_ok = False
    if student_pwd:
        print(f"  ✓ 密码已配置: {'*' * len(student_pwd)}")
    else:
        print("  ✗ 密码未配置")
        all_ok = False
else:
    print("  ✗ .env 文件不存在")
    print("       请复制 .env.example 为 .env 并配置学号和密码")
    all_ok = False

print("\n--- 网络连接检查 ---")
try:
    import urllib.request
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    req = urllib.request.Request(
        'https://jwxt.zjjhkm.edu.cn/jwglxt/xtgl/login_slogin.html',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"  ✓ 教务系统可访问 (HTTP {resp.status})")
except Exception as e:
    print(f"  ✗ 教务系统不可访问: {str(e)}")
    all_ok = False

print(f"\n{'=' * 50}")
if all_ok:
    print("✅ 环境检查通过！可以运行 python main.py")
else:
    print("⚠️  环境检查未通过，请修复上述问题后重试")
print(f"{'=' * 50}")

if not all_ok:
    sys.exit(1)