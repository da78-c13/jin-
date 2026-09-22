#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志模块
"""

import logging
import os
from config import LOG_DIR, LOG_FILE, LOG_LEVEL

# 创建日志目录
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logger = logging.getLogger('qiangke_zjjhkm')
logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.DEBUG))

# 防止重复添加处理器
if not logger.handlers:
    # 文件处理器 - 记录所有日志
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 控制台处理器 - 只记录INFO及以上级别
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)