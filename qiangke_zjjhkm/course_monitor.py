#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
课程监控与抢课模块

功能：
1. 管理待监控的课程列表
2. 定时查询课程余量
3. 发现空位立即抢课
4. 记录抢课结果
"""

import time
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

from config import (
    BASE_URL, COURSE_QUERY_URL, COURSE_SELECT_URL,
    MONITOR_INTERVAL, RETRY_INTERVAL, MAX_RETRIES,
    REQUEST_TIMEOUT, STUDENT_ID, NOT_STARTED_RETRY_INTERVAL
)
from logger import logger
from email_sender import (
    send_success_notification,
    send_error_notification
)


class CourseMonitor:
    """课程监控和抢课"""

    def __init__(self, session):
        """
        初始化课程监控

        Args:
            session: 登录后的 requests.Session 对象
        """
        self.session = session
        self.monitored_courses = []    # 监控中的课程列表
        self.grabbed_courses = set()   # 已抢到的课程ID集合
        self.failed_courses = {}       # 失败次数记录 {course_id: fail_count}
        self.total_checks = 0          # 总检查次数
        self.running = False           # 运行状态
        self.selection_open = False    # 选课系统是否已开放
        self.not_started_count = 0     # 连续未开放的计数

    def add_course(self, course_name, course_id, **kwargs):
        """
        添加要监控的课程

        Args:
            course_name: 课程名称（仅用于显示）
            course_id: 课程编号（用于API请求）
            **kwargs: 其他可选参数
                - teacher: 教师名称
                - class_time: 上课时间
                - credit: 学分
                - extra_params: 额外的请求参数（dict）
        """
        course_info = {
            'name': course_name,
            'id': str(course_id),
            'status': 'monitoring',   # monitoring, grabbed, failed
            'added_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'teacher': kwargs.get('teacher', ''),
            'class_time': kwargs.get('class_time', ''),
            'credit': kwargs.get('credit', ''),
            'extra_params': kwargs.get('extra_params', {}),
        }
        self.monitored_courses.append(course_info)
        logger.info(f"✓ 已添加监控课程: [{course_id}] {course_name}")

    def add_courses_from_file(self, file_path):
        """
        从JSON文件批量添加课程

        Args:
            file_path: JSON文件路径
            JSON格式: [{"name": "课程名", "id": "课程ID", ...}, ...]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                courses = json.load(f)

            count = 0
            for course in courses:
                self.add_course(
                    course.get('name', '未知课程'),
                    course.get('id', ''),
                    teacher=course.get('teacher', ''),
                    class_time=course.get('class_time', ''),
                    credit=course.get('credit', ''),
                    extra_params=course.get('extra_params', {})
                )
                count += 1

            logger.info(f"从文件 {file_path} 导入 {count} 门课程")
            return count

        except FileNotFoundError:
            logger.error(f"课程文件不存在: {file_path}")
            return 0
        except json.JSONDecodeError as e:
            logger.error(f"课程文件格式错误: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"导入课程文件失败: {str(e)}")
            return 0

    def remove_course(self, course_id):
        """
        移除监控的课程

        Args:
            course_id: 课程ID
        """
        self.monitored_courses = [
            c for c in self.monitored_courses if c['id'] != str(course_id)
        ]
        logger.info(f"已移除课程监控: {course_id}")

    def check_course_availability(self, course_id, extra_params=None):
        """
        查询课程是否有空余名额

        Args:
            course_id: 课程编号
            extra_params: 额外的查询参数

        Returns:
            dict: {
                'available': bool,      # 是否有空位
                'remaining': int,       # 剩余名额
                'total': int,           # 总名额
                'selected': int,        # 已选人数
                'raw_data': dict}       # 原始响应数据
                或 None（查询失败）
        """
        params = {
            'xkxnm': '',        # 学年，留空由系统自动
            'xqxqm': '',        # 学期
            'kcmc': '',         # 课程名称
            'kcdm': course_id,  # 课程代码
        }

        # 合并额外参数
        if extra_params:
            params.update(extra_params)

        try:
            logger.debug(f"查询课程 [{course_id}] 状态...")

            response = self.session.get(
                COURSE_QUERY_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={
                    'Referer': f'{BASE_URL}/xsxk/zzxkyzb.html',
                    'X-Requested-With': 'XMLHttpRequest',
                }
            )

            if response.status_code != 200:
                logger.warning(f"查询课程 [{course_id}] 失败: HTTP {response.status_code}")
                return None

            # 尝试解析响应
            return self._parse_course_response(response.text, course_id)

        except requests.exceptions.Timeout:
            logger.warning(f"查询课程 [{course_id}] 超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"查询课程 [{course_id}] 请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"查询课程 [{course_id}] 异常: {str(e)}")
            return None

    def _parse_course_response(self, response_text, course_id):
        """
        解析课程查询响应

        注：正方系统不同版本返回格式不同，这里支持多种格式

        Args:
            response_text: 响应文本
            course_id: 课程ID

        Returns:
            dict: 解析后的课程信息
        """
        result = {
            'available': False,
            'remaining': 0,
            'total': 0,
            'selected': 0,
            'system_closed': False,    # 选课系统是否未开放
            'system_message': '',      # 系统返回的消息
            'raw_data': response_text[:500],  # 只保留前500字符
        }

        # 检测选课系统是否未开放
        closed_patterns = [
            r'目前还不能选课',
            r'未到选课时间',
            r'选课未开始',
            r'不在选课时间段',
            r'选课时间尚未开始',
            r'当前不在选课期间',
            r'选课尚未开始',
            r'不能选课',
            r'系统未开放',
            r'not in the course selection period',
            r'course selection not started',
        ]
        for pattern in closed_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                result['system_closed'] = True
                result['system_message'] = '选课系统尚未开放'
                logger.info(f"  ℹ 选课系统尚未开放，等待中...")
                return result

        # 方法1: JSON格式解析
        try:
            data = json.loads(response_text)

            # 处理不同的JSON结构
            if isinstance(data, dict):
                # 标准格式: {"total": 100, "selected": 80, "available": 20}
                if 'total' in data and 'selected' in data:
                    result['total'] = int(data.get('total', 0))
                    result['selected'] = int(data.get('selected', 0))
                    result['remaining'] = result['total'] - result['selected']
                    result['available'] = result['remaining'] > 0
                    return result

                # 嵌套格式: {"data": {"total": 100, "yxrs": 80}}
                if 'data' in data and isinstance(data['data'], dict):
                    d = data['data']
                    result['total'] = int(d.get('total', d.get('zrs', 0)))
                    result['selected'] = int(d.get('selected', d.get('yxrs', 0)))
                    result['remaining'] = result['total'] - result['selected']
                    result['available'] = result['remaining'] > 0
                    return result

                # 包含课程列表的格式
                if 'courseList' in data or 'items' in data:
                    items = data.get('courseList', data.get('items', []))
                    for item in items:
                        if str(item.get('kcdm', item.get('id', ''))) == str(course_id):
                            result['total'] = int(item.get('zrs', item.get('total', 0)))
                            result['selected'] = int(item.get('yxrs', item.get('selected', 0)))
                            result['remaining'] = result['total'] - result['selected']
                            result['available'] = result['remaining'] > 0
                            return result

            elif isinstance(data, list):
                # 列表格式
                for item in data:
                    if str(item.get('kcdm', item.get('id', ''))) == str(course_id):
                        result['total'] = int(item.get('zrs', item.get('total', 0)))
                        result['selected'] = int(item.get('yxrs', item.get('selected', 0)))
                        result['remaining'] = result['total'] - result['selected']
                        result['available'] = result['remaining'] > 0
                        return result

        except json.JSONDecodeError:
            pass

        # 方法2: HTML表格格式解析
        # 尝试从HTML中提取课程信息
        total_match = re.search(r'总人数[：:]\s*(\d+)', response_text)
        selected_match = re.search(r'已选[人数][：:]\s*(\d+)', response_text)

        if total_match and selected_match:
            result['total'] = int(total_match.group(1))
            result['selected'] = int(selected_match.group(1))
            result['remaining'] = result['total'] - result['selected']
            result['available'] = result['remaining'] > 0
            return result

        # 方法3: 从表格行中提取
        # <tr>...<td>课程ID</td>...<td>已选/总人数</td>...</tr>
        row_pattern = (
            r'<tr[^>]*>.*?' +
            re.escape(course_id) +
            r'.*?(\d+)\s*/\s*(\d+).*?</tr>'
        )
        row_match = re.search(row_pattern, response_text, re.DOTALL)
        if row_match:
            result['selected'] = int(row_match.group(1))
            result['total'] = int(row_match.group(2))
            result['remaining'] = result['total'] - result['selected']
            result['available'] = result['remaining'] > 0
            return result

        # 无法解析，标记为不可用（避免误抢）
        logger.warning(f"课程 [{course_id}] 响应格式无法解析")
        logger.debug(f"响应内容: {response_text[:300]}")
        return result

    def select_course(self, course_id, course_name, extra_params=None):
        """
        执行选课操作

        Args:
            course_id: 课程编号
            course_name: 课程名称
            extra_params: 额外的选课参数

        Returns:
            dict: {
                'success': bool,        # 是否成功
                'message': str,         # 结果消息
                'raw_data': dict/str    # 原始响应
            }
        """
        # 构建选课参数（根据正方系统实际接口调整）
        select_data = {
            'kcdm': course_id,
            # 可能需要其他参数，如：
            # 'xkxnm': '2024-2025',    # 学年
            # 'xqxqm': '3',            # 学期
        }

        if extra_params:
            select_data.update(extra_params)

        result = {
            'success': False,
            'message': '',
            'raw_data': None,
        }

        try:
            logger.info(f"正在抢课: [{course_id}] {course_name}")

            response = self.session.post(
                COURSE_SELECT_URL,
                data=select_data,
                timeout=REQUEST_TIMEOUT,
                headers={
                    'Referer': f'{BASE_URL}/xsxk/zzxkyzb.html',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': BASE_URL,
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                }
            )

            result['raw_data'] = response.text[:500]

            if response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    resp_json = response.json()
                    if isinstance(resp_json, dict):
                        if resp_json.get('success') or resp_json.get('flag') == '1':
                            result['success'] = True
                            result['message'] = resp_json.get(
                                'message', resp_json.get('msg', '选课成功')
                            )
                        else:
                            result['message'] = resp_json.get(
                                'message', resp_json.get('msg', '选课失败')
                            )
                    else:
                        # 非标准格式，但状态码200通常表示成功
                        result['success'] = True
                        result['message'] = '选课请求已提交'
                except json.JSONDecodeError:
                    # 非JSON响应，检查文本内容
                    if '成功' in response.text or 'success' in response.text.lower():
                        result['success'] = True
                        result['message'] = '选课成功'
                    else:
                        result['message'] = response.text[:200]
            else:
                result['message'] = f'HTTP {response.status_code}'

        except requests.exceptions.Timeout:
            result['message'] = '选课请求超时'
        except requests.exceptions.RequestException as e:
            result['message'] = f'选课请求异常: {str(e)}'
        except Exception as e:
            result['message'] = f'选课异常: {str(e)}'

        # 记录结果
        if result['success']:
            logger.info(f"✓ 抢课成功: [{course_id}] {course_name}")
            self.grabbed_courses.add(course_id)
            # 更新课程状态
            for course in self.monitored_courses:
                if course['id'] == str(course_id):
                    course['status'] = 'grabbed'
                    course['grabbed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    break
            # 发送邮件通知
            send_success_notification(course_name)
        else:
            logger.warning(f"✗ 抢课失败: [{course_id}] {course_name} - {result['message']}")
            # 记录失败次数
            self.failed_courses[str(course_id)] = self.failed_courses.get(str(course_id), 0) + 1

        return result

    def start_monitoring(self, check_interval=None):
        """
        开始监控所有课程

        Args:
            check_interval: 检查间隔（秒），默认使用配置文件中的值
        """
        if check_interval is None:
            check_interval = MONITOR_INTERVAL

        if len(self.monitored_courses) == 0:
            logger.warning("⚠ 没有要监控的课程！请先使用 add_course() 添加课程")
            return

        self.running = True

        logger.info("=" * 50)
        logger.info("开始监控课程")
        logger.info(f"监控课程数: {len(self.monitored_courses)}")
        logger.info(f"检查间隔: {check_interval} 秒")
        logger.info(f"重试间隔: {RETRY_INTERVAL} 秒")
        logger.info(f"最大重试次数: {'无限制' if MAX_RETRIES == -1 else MAX_RETRIES}")
        logger.info("按 Ctrl+C 停止监控")
        logger.info("=" * 50)

        # 打印课程列表
        for i, course in enumerate(self.monitored_courses, 1):
            logger.info(f"  {i}. [{course['id']}] {course['name']}")
        logger.info("=" * 50)

        try:
            while self.running:
                self.total_checks += 1
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                logger.info(f"[第{self.total_checks}轮检查] {current_time}")
                logger.info("-" * 40)

                all_grabbed = True
                system_not_open = False

                for course in self.monitored_courses:
                    course_id = course['id']
                    course_name = course['name']

                    # 已经抢到的课程，跳过
                    if course_id in self.grabbed_courses:
                        continue

                    all_grabbed = False

                    # 检查失败次数（排除选课未开放的失败）
                    fail_count = self.failed_courses.get(course_id, 0)
                    if MAX_RETRIES != -1 and fail_count >= MAX_RETRIES:
                        logger.warning(f"课程 [{course_id}] {course_name} 已失败 {fail_count} 次，暂停监控")
                        course['status'] = 'failed'
                        continue

                    # 查询课程余量
                    logger.info(f"检查课程: [{course_id}] {course_name}")
                    availability = self.check_course_availability(
                        course_id,
                        course.get('extra_params')
                    )

                    if availability is None:
                        logger.warning(f"  ↻ 查询失败，将在下一轮重试")
                        continue

                    # 检测选课系统是否未开放
                    if availability.get('system_closed', False):
                        system_not_open = True
                        continue

                    if availability['available']:
                        remaining = availability['remaining']
                        logger.info(f"  ★ 发现空位! 剩余名额: {remaining}")
                        logger.info(f"  ★ 正在抢课...")

                        # 立即抢课
                        select_result = self.select_course(
                            course_id,
                            course_name,
                            course.get('extra_params')
                        )

                        if select_result['success']:
                            logger.info(f"  ✓ {course_name} 抢课成功！")
                        else:
                            logger.info(f"  ✗ 抢课失败: {select_result['message']}")
                            # 检查是否因为系统未开放
                            if '未到时间' in select_result['message'] or '不能选课' in select_result['message']:
                                system_not_open = True
                            else:
                                # 等待重试间隔后继续
                                time.sleep(RETRY_INTERVAL)
                    else:
                        total = availability.get('total', 0)
                        selected = availability.get('selected', 0)
                        remaining = availability.get('remaining', 0)
                        logger.info(f"  - 暂无名额 [{selected}/{total}]")

                # 所有课程都已抢到
                if all_grabbed:
                    logger.info("=" * 40)
                    logger.info("🎉 所有课程已抢到，监控完成！")
                    logger.info("=" * 40)
                    self.print_status()
                    break

                # 如果选课系统未开放，使用较长的等待间隔
                if system_not_open:
                    self.not_started_count += 1
                    if self.not_started_count == 1:
                        logger.info(f"  ℹ 选课系统尚未开放，程序将持续等待...")
                    elif self.not_started_count % 10 == 0:
                        logger.info(f"  ℹ 仍在等待选课系统开放（已等待约 {self.not_started_count * check_interval} 秒）...")
                    wait_time = NOT_STARTED_RETRY_INTERVAL
                else:
                    self.not_started_count = 0
                    if not self.selection_open:
                        self.selection_open = True
                        logger.info("  ★ 选课系统已开放！开始高频监控！")
                    wait_time = check_interval

                # 等待下一次检查
                logger.info(f"等待 {wait_time} 秒后进行下一轮检查...")
                logger.info("=" * 40)
                time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("")
            logger.info("用户手动停止监控")
        except Exception as e:
            logger.error(f"监控过程出现错误: {str(e)}")
            send_error_notification(str(e))
        finally:
            self.running = False
            self.print_status()

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        logger.info("正在停止监控...")

    def print_status(self):
        """打印当前监控状态"""
        logger.info("=" * 50)
        logger.info("监控状态报告")
        logger.info("=" * 50)
        logger.info(f"总检查轮次: {self.total_checks}")
        logger.info(f"监控课程数: {len(self.monitored_courses)}")
        logger.info(f"已抢到课程: {len(self.grabbed_courses)}")
        logger.info(f"失败课程数: {len(self.failed_courses)}")
        logger.info("-" * 40)

        for course in self.monitored_courses:
            status_text = {
                'monitoring': '监控中',
                'grabbed': '✓ 已抢到',
                'failed': '✗ 已失败',
            }.get(course['status'], course['status'])

            fail_count = self.failed_courses.get(course['id'], 0)
            fail_text = f" (失败{fail_count}次)" if fail_count > 0 else ""

            logger.info(f"  [{course['id']}] {course['name']} - {status_text}{fail_text}")

        logger.info("=" * 50)

    def browse_available_courses(self, keyword='', page=1, page_size=50):
        """
        浏览可选课程列表（用于发现课程和课程ID）

        Args:
            keyword: 搜索关键词（课程名）
            page: 页码
            page_size: 每页数量

        Returns:
            list: 课程列表，每项包含 name, id, teacher, credit, capacity 等
        """
        try:
            params = {
                'xkxnm': '',           # 学年
                'xqxqm': '',           # 学期
                'kcmc': keyword,       # 课程名称关键词
                'page': page,
                'pageSize': page_size,
            }

            response = self.session.get(
                COURSE_QUERY_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={
                    'Referer': f'{BASE_URL}/xsxk/zzxkyzb.html',
                    'X-Requested-With': 'XMLHttpRequest',
                }
            )

            if response.status_code != 200:
                logger.error(f"查询课程列表失败: HTTP {response.status_code}")
                return []

            courses = []

            # 尝试JSON解析
            try:
                data = json.loads(response.text)
                # 多种可能的字段名
                items = (
                    data.get('courseList') or
                    data.get('items') or
                    data.get('data', {}).get('rows') or
                    data.get('rows') or
                    data.get('list') or
                    []
                )

                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            courses.append({
                                'name': item.get('kcmc', item.get('courseName', item.get('name', '未知'))),
                                'id': item.get('kcdm', item.get('courseId', item.get('id', ''))),
                                'teacher': item.get('jsxm', item.get('teacher', item.get('teacherName', ''))),
                                'credit': item.get('xf', item.get('credit', '')),
                                'total': item.get('zrs', item.get('total', 0)),
                                'selected': item.get('yxrs', item.get('selected', 0)),
                                'available': item.get('skrl', item.get('available', 0)),
                                'class_time': item.get('sksj', item.get('classTime', '')),
                                'department': item.get('kkbm', item.get('department', '')),
                            })
            except json.JSONDecodeError:
                # HTML解析兜底
                logger.warning("课程列表返回非JSON格式，尝试HTML解析...")

            if not courses:
                logger.info(f"未查询到课程，系统可能尚未开放或关键词无结果")
                logger.debug(f"原始响应: {response.text[:300]}")

            return courses

        except Exception as e:
            logger.error(f"浏览课程时出错: {str(e)}")
            return []

    def get_status(self):
        """获取监控状态数据"""
        return {
            'total_checks': self.total_checks,
            'total_courses': len(self.monitored_courses),
            'grabbed_courses': len(self.grabbed_courses),
            'failed_courses': len(self.failed_courses),
            'courses': [
                {
                    'id': c['id'],
                    'name': c['name'],
                    'status': c['status'],
                    'fail_count': self.failed_courses.get(c['id'], 0),
                }
                for c in self.monitored_courses
            ],
        }