#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮件发送模块（可选）
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import (
    EMAIL_ENABLED, EMAIL_SENDER, EMAIL_PASSWORD,
    EMAIL_RECEIVER, SMTP_SERVER, SMTP_PORT
)
from logger import logger


def send_email(subject, body, is_html=False):
    """
    发送邮件通知

    Args:
        subject: 邮件主题
        body: 邮件正文
        is_html: 是否是HTML格式

    Returns:
        bool: 发送是否成功
    """
    if not EMAIL_ENABLED:
        logger.debug("邮件通知未启用，跳过发送")
        return False

    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        logger.warning("邮件配置不完整，无法发送通知")
        return False

    try:
        # 设置邮件对象
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        # 添加邮件正文
        if is_html:
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 连接SMTP服务器并发送
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"邮件发送成功: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("邮件发送失败: SMTP认证失败，请检查邮箱地址和授权码")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"邮件发送失败: SMTP错误 - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"邮件发送失败: {str(e)}")
        return False


def send_success_notification(course_name, course_info=None):
    """发送抢课成功通知"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = f"【抢课成功】{course_name}"

    body = f"""
========================================
        🎉 抢课成功通知 🎉
========================================

课程名称: {course_name}
抢课时间: {now}
{'' if not course_info else f'课程信息: {course_info}'}

请尽快登录教务系统确认选课结果！

浙江金华科贸职业技术学院 教务管理系统
========================================
    """
    return send_email(subject, body)


def send_error_notification(error_msg):
    """发送错误通知"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = "【抢课异常】程序出现错误"

    body = f"""
========================================
        ⚠️ 抢课程序异常通知 ⚠️
========================================

错误信息: {error_msg}
发生时间: {now}

请查看程序日志了解详情（logs/qiangke.log）

========================================
    """
    return send_email(subject, body)


def send_monitor_status_notification(courses_status):
    """发送监控状态通知"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    subject = "【抢课程序】监控状态报告"

    body = f"""
========================================
        抢课程序运行状态报告
========================================

报告时间: {now}

监控课程:
{courses_status}

========================================
    """
    return send_email(subject, body)