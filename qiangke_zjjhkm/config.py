#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浙江金华科贸职业技术学院 抢课工具 - 配置文件
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ==================== 教务系统配置 ====================
# 教务系统基础URL
BASE_URL = os.getenv('BASE_URL', 'https://jwxt.zjjhkm.edu.cn/jwglxt')

# 登录页面
LOGIN_URL = f'{BASE_URL}/xtgl/login_slogin.html'

# 获取RSA公钥的接口
PUBLIC_KEY_URL = f'{BASE_URL}/xtgl/login_getPublicKey.html'

# 登录后的主页（用于验证登录状态）
MAIN_URL = f'{BASE_URL}/xtgl/index_initMenu.html'

# 学号和密码
STUDENT_ID = os.getenv('STUDENT_ID')
STUDENT_PASSWORD = os.getenv('STUDENT_PASSWORD')

# ==================== 选课接口配置 ====================
# 注意：这些URL需要根据学校实际选课系统进行调整
# 查询可选课程的接口
COURSE_QUERY_URL = os.getenv('COURSE_QUERY_URL', f'{BASE_URL}/xsxk/zzxkyzb_cxZzxkyzbIndex.html')

# 选课提交接口
COURSE_SELECT_URL = os.getenv('COURSE_SELECT_URL', f'{BASE_URL}/xsxk/zzxkyzb_xkBc.html')

# 退课接口
COURSE_CANCEL_URL = os.getenv('COURSE_CANCEL_URL', f'{BASE_URL}/xsxk/zzxkyzb_tkbc.html')

# ==================== 抢课配置 ====================
# 监控间隔（秒），建议30秒以上，避免对服务器造成压力
MONITOR_INTERVAL = int(os.getenv('MONITOR_INTERVAL', '5'))

# 抢课失败后的重试间隔（秒）
RETRY_INTERVAL = int(os.getenv('RETRY_INTERVAL', '5'))

# 最大重试次数（-1表示无限重试）
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '-1'))

# 请求超时（秒）
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))

# ==================== 定时启动配置 ====================
# 定时启动时间（选课开放时间）
# 格式：YYYY-MM-DD HH:MM 例如：2025-03-15 12:30
# 留空则立即开始监控
SCHEDULED_START = os.getenv('SCHEDULED_START', '')

# 定时启动时，提前登录的秒数（在开放时间前先登录好，到点直接抢）
PRE_LOGIN_SECONDS = int(os.getenv('PRE_LOGIN_SECONDS', '30'))

# 选课未开始时，等待重试间隔（秒）
NOT_STARTED_RETRY_INTERVAL = int(os.getenv('NOT_STARTED_RETRY_INTERVAL', '30'))

# ==================== 邮件通知配置（可选）====================
# 是否启用邮件通知（True/False）
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'False').lower() in ('true', '1', 'yes')

# 发件邮箱配置
EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')  # 授权码
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER', '')

# SMTP服务器配置（QQ邮箱）
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# ==================== 日志配置 ====================
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'qiangke.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')