#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浙江金华科贸职业技术学院 - 教务系统自动抢课工具

基于 https://github.com/wolverine396/qiangke 改造

功能：
1. 自动登录正方教务系统 v9.0（RSA加密登录）
2. 监控指定课程的剩余名额
3. 发现空位立即自动抢课
4. 邮件通知（可选）

使用方法：
    python main.py

首次使用前请配置 .env 文件中的学号和密码，
并在下方添加要监控的课程。

获取课程ID的方法：
1. 登录教务系统 https://jwxt.zjjhkm.edu.cn/jwglxt/
2. 进入选课界面
3. 按 F12 打开开发者工具
4. 在网络请求中找到课程对应的ID
"""

import sys
import os
import time
from datetime import datetime, timedelta
from logger import logger
from config import (
    MONITOR_INTERVAL, STUDENT_ID, STUDENT_PASSWORD,
    EMAIL_ENABLED, SCHEDULED_START, PRE_LOGIN_SECONDS
)
from zhengfang_login import ZhengfangLogin
from course_monitor import CourseMonitor
from email_sender import send_monitor_status_notification


def wait_for_scheduled_start():
    """
    等待到定时启动时间

    如果配置了 SCHEDULED_START，则等待到指定时间再启动。
    支持格式：
      - "2025-03-15 12:30"（完整日期时间）
      - "12:30"（今天/明天的某个时间）
      - ""（空字符串 = 立即启动）
    """
    if not SCHEDULED_START:
        return  # 没有配置定时启动，立即开始

    # 解析定时启动时间
    scheduled_time = None
    now = datetime.now()

    # 尝试完整格式 "YYYY-MM-DD HH:MM"
    try:
        scheduled_time = datetime.strptime(SCHEDULED_START, '%Y-%m-%d %H:%M')
    except ValueError:
        pass

    # 尝试 "HH:MM" 格式（今天的时间）
    if scheduled_time is None:
        try:
            parsed_time = datetime.strptime(SCHEDULED_START, '%H:%M')
            scheduled_time = now.replace(
                hour=parsed_time.hour,
                minute=parsed_time.minute,
                second=0,
                microsecond=0
            )
            # 如果时间已过，设为明天
            if scheduled_time <= now:
                scheduled_time += timedelta(days=1)
        except ValueError:
            pass

    if scheduled_time is None:
        logger.warning(f"⚠ 无法解析定时启动时间: {SCHEDULED_START}，将立即启动")
        return

    # 计算等待时间
    wait_seconds = (scheduled_time - now).total_seconds()
    if wait_seconds <= 0:
        logger.info(f"定时启动时间 {SCHEDULED_START} 已过，立即启动")
        return

    logger.info("=" * 60)
    logger.info(f"📅 定时启动已设置")
    logger.info(f"目标时间: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"还需等待: {format_time(wait_seconds)}")
    logger.info("=" * 60)

    # 计算提前登录的时间点（在开放时间前 PRE_LOGIN_SECONDS 秒登录）
    login_time = scheduled_time - timedelta(seconds=PRE_LOGIN_SECONDS)
    login_wait = (login_time - now).total_seconds()

    # 先等待到提前登录时间
    if login_wait > 0:
        logger.info(f"将在 {format_time(login_wait)} 后登录系统（提前 {PRE_LOGIN_SECONDS} 秒）")

        # 倒计时显示
        remaining = int(login_wait)
        while remaining > 0:
            if remaining % 60 == 0 or remaining <= 10:  # 每分钟和最后10秒显示
                logger.info(f"  ⏳ 距离登录还有 {format_time(remaining)}...")
            time.sleep(min(5, remaining))
            remaining -= 5
            # 重新计算以防时间偏差
            actual_wait = (login_time - datetime.now()).total_seconds()
            if actual_wait <= 0:
                break
            remaining = min(remaining, int(actual_wait))

    logger.info("⏰ 开始登录系统...")
    return True


def format_time(seconds):
    """将秒数格式化为可读的时间字符串"""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} 秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} 分 {secs} 秒"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} 小时 {minutes} 分"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} 天 {hours} 小时"


def main():
    """主程序入口"""
    logger.info("=" * 60)
    logger.info("浙江金华科贸职业技术学院 - 自动抢课工具 v2.0")
    logger.info("=" * 60)

    # 检查配置
    if not STUDENT_ID or not STUDENT_PASSWORD:
        logger.error("✗ 错误：未设置学号或密码！")
        logger.error("  请在项目目录下的 .env 文件中配置：")
        logger.error("    STUDENT_ID=你的学号")
        logger.error("    STUDENT_PASSWORD=你的密码")
        sys.exit(1)

    logger.info(f"学号: {STUDENT_ID}")
    if EMAIL_ENABLED:
        logger.info("邮件通知: 已启用")
    else:
        logger.info("邮件通知: 未启用")

    # ==================== 步骤0: 等待定时启动（可选）====================
    if SCHEDULED_START:
        wait_for_scheduled_start()

    # ==================== 步骤1: 登录教务系统 ====================
    logger.info("")
    logger.info("步骤1: 登录教务系统")

    login = ZhengfangLogin()
    login_success = login.login()

    if not login_success:
        logger.error("✗ 登录失败，程序退出")
        logger.error("  可能的原因：")
        logger.error("    1. 学号或密码错误")
        logger.error("    2. 网络连接问题")
        logger.error("    3. 教务系统暂时不可用")
        logger.error("  请检查后重试")
        sys.exit(1)

    session = login.get_session()

    # ==================== 步骤2: 初始化课程监控 ====================
    logger.info("")
    logger.info("步骤2: 初始化课程监控")

    monitor = CourseMonitor(session)

    # 自动从 courses.json 加载课程（Web配置工具生成的）
    courses_file = os.path.join(os.path.dirname(__file__), 'courses.json')
    if os.path.exists(courses_file):
        loaded = monitor.add_courses_from_file(courses_file)
        if loaded > 0:
            logger.info(f"从 courses.json 自动加载了 {loaded} 门课程")

    # ！！！ 你也可以在这里手动添加课程 ！！！
    # 使用 monitor.add_course("课程名称", "课程ID")
    #
    # 示例：
    #   monitor.add_course("高等数学A", "12345")
    #   monitor.add_course("大学英语B", "67890")
    #
    # 如何获取课程ID：
    #   1. 浏览器登录教务系统
    #   2. 进入选课页面
    #   3. 按F12 -> Network标签
    #   4. 选择课程时查看请求参数中的课程ID

    # ========== 手动添加课程（可选）==========
    # example:
    # monitor.add_course("课程名称", "课程ID")
    # ====================================

    # 检查是否添加了课程
    if len(monitor.monitored_courses) == 0:
        logger.warning("⚠ 未添加任何监控课程！")
        logger.info("")
        logger.info("请编辑 main.py 文件，在 '步骤2' 部分添加你要监控的课程：")
        logger.info('')
        logger.info('    monitor.add_course("课程名称", "课程ID")')
        logger.info('')
        logger.info("例如：")
        logger.info('    monitor.add_course("高等数学", "12345")')
        logger.info('    monitor.add_course("大学英语", "67890")')
        logger.info('')
        logger.info("课程ID获取方法：")
        logger.info("1. 访问教务系统并登录")
        logger.info("2. 进入选课界面 https://jwxt.zjjhkm.edu.cn/jwglxt/xsxk/zzxkyzb.html")
        logger.info("3. 按 F12 打开开发者工具")
        logger.info("4. 在 Network 标签页中查看选课请求的参数")
        logger.info("")
        sys.exit(0)

    # ==================== 步骤3: 开始监控 ====================
    logger.info("")
    logger.info("步骤3: 开始监控课程")
    logger.info(f"监控间隔: {MONITOR_INTERVAL} 秒")
    logger.info("按 Ctrl+C 停止监控")
    logger.info("")

    try:
        monitor.start_monitoring(check_interval=MONITOR_INTERVAL)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("程序已停止")
    except Exception as e:
        logger.error(f"程序运行异常: {str(e)}")
        sys.exit(1)

    logger.info("程序运行结束")


def quick_test():
    """
    快速测试模式 - 仅测试登录和课程查询，不启动监控
    用于验证配置是否正确
    """
    logger.info("=" * 60)
    logger.info("快速测试模式")
    logger.info("=" * 60)

    if not STUDENT_ID or not STUDENT_PASSWORD:
        logger.error("请先配置 .env 文件中的学号和密码")
        return

    # 测试登录
    login = ZhengfangLogin()
    if not login.login():
        logger.error("登录测试失败")
        return

    logger.info("✓ 登录测试通过")

    # 测试课程查询
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_course_id = input("请输入要测试查询的课程ID: ")
        if test_course_id:
            from course_monitor import CourseMonitor
            monitor = CourseMonitor(login.get_session())
            result = monitor.check_course_availability(test_course_id)
            if result:
                logger.info(f"课程查询结果: {result}")
            else:
                logger.info("课程查询失败")

    logger.info("测试完成")


def browse_courses():
    """
    浏览可选课程模式 - 登录后查询当前可选课程列表
    用于帮助发现课程ID
    """
    logger.info("=" * 60)
    logger.info("📚 浏览可选课程模式")
    logger.info("=" * 60)

    if not STUDENT_ID or not STUDENT_PASSWORD:
        logger.error("请先配置 .env 文件中的学号和密码")
        return

    # 登录
    login = ZhengfangLogin()
    if not login.login():
        logger.error("登录失败")
        return

    session = login.get_session()
    monitor = CourseMonitor(session)

    keyword = input("\n请输入搜索关键词（直接回车显示所有课程）: ").strip()

    logger.info("正在查询可选课程...")
    courses = monitor.browse_available_courses(keyword=keyword)

    if not courses:
        logger.info("")
        logger.info("未找到课程，可能原因：")
        logger.info("  1. 选课系统尚未开放")
        logger.info("  2. 搜索关键词不匹配")
        logger.info("  3. 接口URL需要调整")
        logger.info("")
        logger.info("建议：选课开放后再运行 python main.py browse")
        return

    logger.info(f"\n找到 {len(courses)} 门课程：")
    logger.info("=" * 80)
    logger.info(f"{'序号':>4} | {'课程名称':<25} | {'课程ID':<15} | {'教师':<10} | {'名额':<10}")
    logger.info("-" * 80)

    for i, course in enumerate(courses, 1):
        name = course['name'][:25] if len(course['name']) > 25 else course['name']
        cid = str(course['id'])[:15]
        teacher = course['teacher'][:10] if course['teacher'] else '-'
        capacity = f"{course['selected']}/{course['total']}" if course['total'] else '-'
        logger.info(f"{i:>4} | {name:<25} | {cid:<15} | {teacher:<10} | {capacity:<10}")

    logger.info("=" * 80)
    logger.info("")
    logger.info("使用方式：将课程ID填入 main.py 的 monitor.add_course() 中")
    logger.info("例如：monitor.add_course(\"课程名\", \"课程ID\")")


if __name__ == '__main__':
    # 命令行参数处理
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'test':
            quick_test()
        elif cmd == 'browse':
            browse_courses()
        else:
            logger.error(f"未知命令: {cmd}")
            logger.info("可用命令: python main.py       - 正常抢课模式")
            logger.info("          python main.py test   - 测试登录")
            logger.info("          python main.py browse - 浏览可选课程")
    else:
        main()