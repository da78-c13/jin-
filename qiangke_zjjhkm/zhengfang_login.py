#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
正方教务系统 v9.0 登录模块

登录流程：
1. 访问登录页面，获取初始Cookie（JSESSIONID）
2. 获取RSA公钥（modulus + exponent）
3. 使用RSA公钥加密密码
4. 提交登录表单（用户名 + 加密后的密码）
5. 处理登录后的重定向，获取最终Session
"""

import re
import time
import base64
import requests
from urllib.parse import urljoin

from config import (
    LOGIN_URL, PUBLIC_KEY_URL, MAIN_URL, BASE_URL,
    STUDENT_ID, STUDENT_PASSWORD,
    REQUEST_TIMEOUT
)
from logger import logger


class ZhengfangLogin:
    """正方教务系统登录处理"""

    def __init__(self):
        """初始化会话"""
        self.session = requests.Session()

        # 设置请求头，模拟浏览器
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,image/avif,image/webp,image/apng,*/*;'
                'q=0.8,application/signed-exchange;v=b3;q=0.7'
            ),
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

        self.logged_in = False
        self.csrf_token = None
        self.hidden_fields = {}

    def _get_public_key(self):
        """
        从服务器获取RSA公钥

        Returns:
            tuple: (modulus, exponent) 或 (None, None)
        """
        try:
            # 添加时间戳避免缓存
            timestamp = int(time.time() * 1000)
            url = f"{PUBLIC_KEY_URL}?time={timestamp}"

            response = self.session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    'Referer': LOGIN_URL,
                    'X-Requested-With': 'XMLHttpRequest',
                }
            )

            if response.status_code == 200:
                data = response.json()
                modulus = data.get('modulus', '')
                exponent = data.get('exponent', '')
                logger.debug(f"获取RSA公钥成功")
                return modulus, exponent
            else:
                logger.error(f"获取RSA公钥失败: HTTP {response.status_code}")
                return None, None

        except requests.exceptions.Timeout:
            logger.error("获取RSA公钥超时")
            return None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"获取RSA公钥请求失败: {str(e)}")
            return None, None
        except ValueError as e:
            logger.error(f"解析RSA公钥响应失败: {str(e)}")
            return None, None

    def _rsa_encrypt(self, password, modulus_b64, exponent_b64):
        """
        使用RSA公钥加密密码（PKCS#1 v1.5）

        正方系统使用JavaScript的JSEncrypt库进行RSA加密，
        使用pycryptodome的PKCS1_v1_5实现相同逻辑

        Args:
            password: 明文密码
            modulus_b64: Base64编码的模数
            exponent_b64: Base64编码的指数

        Returns:
            str: Base64编码的加密后的密码
        """
        try:
            from Crypto.PublicKey import RSA
            from Crypto.Cipher import PKCS1_v1_5

            # Base64解码modulus和exponent
            modulus_bytes = base64.b64decode(modulus_b64)
            exponent_bytes = base64.b64decode(exponent_b64)

            # 构建RSA公钥（DER编码）
            n = int.from_bytes(modulus_bytes, byteorder='big')
            e = int.from_bytes(exponent_bytes, byteorder='big')

            # 通过数字构造RSA key
            rsa_key = RSA.construct((n, e))

            # 创建PKCS1_v1_5加密器
            cipher = PKCS1_v1_5.new(rsa_key)

            # 加密密码（PKCS#1 v1.5）
            password_bytes = password.encode('utf-8')
            crypto = cipher.encrypt(password_bytes)

            # Base64编码加密结果
            encrypted = base64.b64encode(crypto).decode('ascii')
            logger.debug("RSA密码加密成功")
            return encrypted

        except ImportError:
            # 回退到rsa库
            logger.warning("pycryptodome未安装，尝试使用rsa库...")
            try:
                import rsa
                modulus_bytes = base64.b64decode(modulus_b64)
                exponent_bytes = base64.b64decode(exponent_b64)
                pub_key = rsa.PublicKey(
                    n=int.from_bytes(modulus_bytes, byteorder='big'),
                    e=int.from_bytes(exponent_bytes, byteorder='big')
                )
                crypto = rsa.encrypt(password.encode('utf-8'), pub_key)
                encrypted = base64.b64encode(crypto).decode('ascii')
                return encrypted
            except ImportError:
                logger.error("缺少加密库，请安装: pip install pycryptodome 或 pip install rsa")
                raise
        except Exception as e:
            logger.error(f"RSA密码加密失败: {str(e)}")
            raise

    def login(self):
        """
        执行登录流程

        根据逆向登录页面JS实现：
          1. 访问登录页面获取Cookie和隐藏字段
          2. 获取RSA公钥
          3. RSA加密密码
          4. 检查用户状态（login_cxDlxgxx.html）
          5. 退出旧会话（login_logoutAccount.html）
          6. 提交全部表单字段

        Returns:
            bool: 登录是否成功
        """
        logger.info("=" * 50)
        logger.info("开始登录教务系统")
        logger.info(f"登录地址: {LOGIN_URL}")
        logger.info("=" * 50)

        try:
            # ===== 步骤1: 访问登录页面获取Cookie和隐藏字段 =====
            logger.info("步骤1: 访问登录页面获取初始Cookie...")
            init_response = self.session.get(
                LOGIN_URL,
                timeout=REQUEST_TIMEOUT
            )

            if init_response.status_code != 200:
                logger.error(f"访问登录页面失败: HTTP {init_response.status_code}")
                return False

            cookies = dict(self.session.cookies)
            logger.info(f"获取到Cookie: {list(cookies.keys())}")

            # 提取所有隐藏字段（含csrftoken）
            self._extract_hidden_fields(init_response.text)

            # ===== 步骤2: 获取RSA公钥 =====
            logger.info("步骤2: 获取RSA公钥...")
            modulus, exponent = self._get_public_key()

            if not modulus or not exponent:
                logger.error("获取RSA公钥失败，无法继续登录")
                return False

            logger.info(f"RSA公钥获取成功 (模数长度: {len(base64.b64decode(modulus))}字节)")

            # ===== 步骤3: RSA加密密码 =====
            logger.info("步骤3: 加密密码...")
            encrypted_password = self._rsa_encrypt(
                STUDENT_PASSWORD,
                modulus,
                exponent
            )
            logger.info("密码加密完成")

            # ===== 步骤4: 模拟浏览器预检流程 =====
            # 4a. 检查用户信息确认 (yhgl_cxXxqrCheck.html)
            try:
                xqr_response = self.session.post(
                    f'{BASE_URL}/xtgl/yhgl_cxXxqrCheck.html',
                    data={'yhm': STUDENT_ID},
                    timeout=REQUEST_TIMEOUT,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                logger.debug(f"用户信息确认检查: {xqr_response.text[:100]}")
            except Exception:
                pass

            # 4b. 检查用户登录状态 (login_cxDlxgxx.html)
            dlxgxx_ok = False
            try:
                dlxg_response = self.session.post(
                    f'{BASE_URL}/xtgl/login_cxDlxgxx.html',
                    data={'yhm': STUDENT_ID},
                    timeout=REQUEST_TIMEOUT,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                dlxg_data = dlxg_response.text.strip().strip('"')
                logger.debug(f"登录状态检查: {dlxg_data[:100]}")
                if dlxg_data and dlxg_data != '0':
                    dlxgxx_ok = True
            except Exception:
                pass

            # 4c. 退出旧会话 (login_logoutAccount.html)
            try:
                csrf_token_logout = self.hidden_fields.get('csrfTokenLogout', '')
                self.session.post(
                    f'{BASE_URL}/xtgl/login_logoutAccount.html',
                    data={'csrfTokenLogout': csrf_token_logout},
                    timeout=REQUEST_TIMEOUT,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                logger.debug("已退出旧会话")
            except Exception:
                pass

            # ===== 步骤5: 提交登录表单（所有字段） =====
            logger.info("步骤5: 提交登录表单...")

            # 从隐藏字段构建完整的POST数据，覆盖yhm和mm
            login_data = dict(self.hidden_fields)  # 复制所有隐藏字段
            login_data['yhm'] = STUDENT_ID
            login_data['mm'] = encrypted_password

            # 添加时间戳到URL
            timestamp = int(time.time() * 1000)
            login_url = f"{LOGIN_URL}?time={timestamp}"

            login_response = self.session.post(
                login_url,
                data=login_data,
                timeout=REQUEST_TIMEOUT,
                headers={
                    'Referer': LOGIN_URL,
                    'Origin': BASE_URL,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                allow_redirects=True
            )

            logger.info(f"登录响应状态码: {login_response.status_code}")
            logger.info(f"登录响应URL: {login_response.url}")

            # ===== 步骤6: 检查登录结果 =====
            if self._check_login_success(login_response):
                self.logged_in = True
                logger.info("✓ 登录成功！")
                return True
            else:
                logger.error("✗ 登录失败，请检查学号和密码是否正确")
                return False

        except requests.exceptions.Timeout:
            logger.error("登录请求超时，请检查网络连接")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("网络连接失败，请检查网络连接")
            return False
        except ImportError:
            logger.error("缺少必要的库，请执行: pip install -r requirements.txt")
            return False
        except Exception as e:
            logger.error(f"登录过程中出现意外错误: {str(e)}")
            return False

    def _extract_hidden_fields(self, html_text):
        """
        从登录页面HTML中提取所有hidden输入字段

        Args:
            html_text: 登录页面的HTML文本
        """
        self.hidden_fields = {}

        # 提取所有 <input type="hidden" ...> 字段
        pattern = r'<input[^>]*type=["\']hidden["\'][^>]*>'
        for match in re.finditer(pattern, html_text, re.IGNORECASE):
            input_tag = match.group()

            # 提取 name
            name_match = re.search(r'name=["\']([^"\']*)["\']', input_tag)
            if not name_match:
                # 尝试无引号的 name 属性
                name_match = re.search(r'name=\s*([^\s>]+)', input_tag)
            if not name_match:
                continue
            name = name_match.group(1).strip()

            # 提取 value（支持引号和无引号两种格式）
            value_match = re.search(r'value=["\']([^"\']*)["\']', input_tag)
            if not value_match:
                # 尝试无引号的 value 属性
                value_match = re.search(r'value=\s*([^\s>]+)', input_tag)
            value = value_match.group(1).strip() if value_match else ''

            self.hidden_fields[name] = value

        logger.debug(f"提取到 {len(self.hidden_fields)} 个隐藏字段: {list(self.hidden_fields.keys())}")

        # 特别记录csrftoken
        if 'csrftoken' in self.hidden_fields:
            self.csrf_token = self.hidden_fields['csrftoken']
            logger.debug(f"CSRF Token: {self.csrf_token[:30]}...")

    def _extract_csrf_token(self, html_text):
        """
        从登录页面中提取CSRF token（兼容旧版本）

        Args:
            html_text: 登录页面的HTML文本
        """
        # 尝试多种可能的CSRF token名称
        patterns = [
            r'name=["\']csrftoken["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\']csrfToken["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'id=["\']csrftoken["\'][^>]*value=["\']([^"\']+)["\']',
            r'csrf_token["\']\s*[:=]\s*["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                self.csrf_token = match.group(1)
                logger.debug(f"获取到CSRF Token: {self.csrf_token[:20]}...")
                return

        logger.debug("未在页面中找到CSRF Token（这是正常的）")

    def _check_login_success(self, response):
        """
        检查登录是否成功

        Args:
            response: 登录后的响应对象

        Returns:
            bool: 登录是否成功
        """
        # 方法1: 检查URL是否跳转到主页
        current_url = response.url
        logger.debug(f"当前URL: {current_url}")

        # 登录成功后会跳转到主页
        if 'index_initMenu' in current_url or 'index' in current_url:
            return True

        # 方法2: 检查响应内容中是否包含错误信息
        if '错误' in response.text or '失败' in response.text:
            # 提取具体错误信息
            error_patterns = [
                r'<div[^>]*class=["\']error["\'][^>]*>([^<]+)',
                r'<span[^>]*class=["\']error["\'][^>]*>([^<]+)',
                r'错误提示[：:]\s*([^<]+)',
                r'登录失败[：:]\s*([^<]+)',
            ]
            for pattern in error_patterns:
                match = re.search(pattern, response.text)
                if match:
                    logger.error(f"登录错误信息: {match.group(1).strip()}")
                    return False

        # 方法3: 检查是否包含学号（表示已登录）
        if STUDENT_ID in response.text:
            return True

        # 方法4: 访问主页验证
        try:
            verify_response = self.session.get(
                MAIN_URL,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False
            )
            # 如果首页返回200而不是302重定向，说明已登录
            if verify_response.status_code == 200 and not verify_response.is_redirect:
                return True
        except Exception:
            pass

        return False

    def get_session(self):
        """
        获取登录后的Session对象

        Returns:
            requests.Session: 已登录的Session对象
        """
        return self.session

    def is_logged_in(self):
        """
        检查当前是否已登录

        Returns:
            bool: 是否已登录
        """
        if not self.logged_in:
            return False

        try:
            # 访问主页验证session是否有效
            response = self.session.get(
                MAIN_URL,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False
            )
            # 如果返回200，说明session有效
            return response.status_code == 200
        except Exception:
            return False

    def logout(self):
        """退出登录"""
        try:
            logout_url = f"{MAIN_URL.split('xtgl')[0]}xtgl/login_slogin.html"
            self.session.get(
                logout_url,
                timeout=REQUEST_TIMEOUT,
                params={'logout': '1'}
            )
            self.logged_in = False
            logger.info("已退出登录")
        except Exception as e:
            logger.debug(f"退出登录时出现异常: {str(e)}")