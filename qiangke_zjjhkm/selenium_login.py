#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Selenium登录教务系统（浏览器自动处理JSEncrypt加密）
登录成功后保存cookies供后续使用
"""
import sys, time, json, re
sys.path.insert(0, r'C:\Users\Administrator\qiangke_zjjhkm')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from config import LOGIN_URL, STUDENT_ID, STUDENT_PASSWORD

print("=" * 60)
print("Selenium 浏览器登录")
print("=" * 60)

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1280,720')
chrome_options.add_argument('--disable-gpu')
chrome_options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

try:
    driver = webdriver.Chrome(options=chrome_options)
    print("✓ 浏览器已启动")
    
    # 访问登录页面
    print(f"正在访问: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    
    # 等待页面加载完成
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.ID, "yhm")))
    print("✓ 页面加载完成")
    
    # 输入用户名
    username_input = driver.find_element(By.ID, "yhm")
    username_input.clear()
    username_input.send_keys(STUDENT_ID)
    print(f"✓ 已输入学号: {STUDENT_ID}")
    
    # 输入密码
    password_input = driver.find_element(By.ID, "mm")
    password_input.clear()
    password_input.send_keys(STUDENT_PASSWORD)
    print("✓ 已输入密码")
    
    time.sleep(0.5)
    
    # 点击登录按钮
    login_btn = driver.find_element(By.ID, "dl")
    login_btn.click()
    print("✓ 已点击登录按钮，等待登录结果...")
    
    # 等待登录完成 - 最多等10秒
    time.sleep(3)
    
    # 检查登录结果
    current_url = driver.current_url
    print(f"\n当前URL: {current_url}")
    
    if 'index' in current_url or 'initMenu' in current_url:
        print("\n✓✓✓ 登录成功！")
        
        # 获取cookies
        cookies = driver.get_cookies()
        print(f"\n获取到 {len(cookies)} 个cookie:")
        
        # 保存cookies
        with open('cookies.json', 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print("✓ Cookies已保存到 cookies.json")
        
        # 也输出requests格式的cookie字符串
        cookie_dict = {}
        for c in cookies:
            cookie_dict[c['name']] = c['value']
        
        # 保存为Python dict格式
        with open('cookies_dict.json', 'w', encoding='utf-8') as f:
            json.dump(cookie_dict, f, ensure_ascii=False, indent=2)
        print("✓ Cookie字典已保存到 cookies_dict.json")
        
        print("\nCookie字符串:")
        print('; '.join([f"{k}={v}" for k, v in cookie_dict.items()]))
        
        # 截图确认
        driver.save_screenshot('login_success.png')
        print("✓ 已保存截图 login_success.png")
        
    else:
        print("\n✗ 登录失败")
        
        # 检查错误提示
        try:
            tips = driver.find_element(By.ID, "tips")
            if tips.is_displayed() and tips.text:
                print(f"错误提示: {tips.text}")
        except:
            pass
        
        # 检查页面中的错误信息
        page_source = driver.page_source
        for kw in ['锁定', '错误', '密码错误', '不存在']:
            if kw in page_source:
                print(f"发现关键词: {kw}")
                # 找到附近内容
                idx = page_source.find(kw)
                print(f"  上下文: ...{page_source[max(0,idx-30):idx+50]}...")
        
        driver.save_screenshot('login_failed.png')
        print("已保存截图 login_failed.png")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    try:
        driver.quit()
        print("\n浏览器已关闭")
    except:
        pass