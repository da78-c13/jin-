#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===================================================
  浙江金华科贸职业技术学院 - 抢课配置工具 (Web版)
===================================================

启动后打开浏览器访问 http://localhost:8080
填写信息后自动保存到 .env 和 courses.json

使用方法：
    python config_web.py
"""

import os
import sys
import json
import re
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# ==================== 配置 ====================
HOST = '0.0.0.0'
PORT = 8080
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_DIR, '.env')
COURSES_FILE = os.path.join(PROJECT_DIR, 'courses.json')


# ==================== 工具函数 ====================

def load_env():
    """读取当前 .env 文件内容"""
    data = {
        'STUDENT_ID': '',
        'STUDENT_PASSWORD': '',
        'SCHEDULED_START': '12:30',
        'MONITOR_INTERVAL': '5',
        'BASE_URL': 'https://jwxt.zjjhkm.edu.cn/jwglxt',
    }
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    if key in data:
                        data[key] = val
    return data


def save_env(data):
    """保存配置到 .env 文件"""
    content = f"""# ==================== 教务系统配置 ====================
BASE_URL={data.get('BASE_URL', 'https://jwxt.zjjhkm.edu.cn/jwglxt')}

# 你的学号
STUDENT_ID={data['STUDENT_ID']}

# 你的密码
STUDENT_PASSWORD={data['STUDENT_PASSWORD']}

# ==================== 选课接口配置 ====================
COURSE_QUERY_URL={data.get('BASE_URL', 'https://jwxt.zjjhkm.edu.cn/jwglxt')}/xsxk/zzxkyzb_cxZzxkyzbIndex.html
COURSE_SELECT_URL={data.get('BASE_URL', 'https://jwxt.zjjhkm.edu.cn/jwglxt')}/xsxk/zzxkyzb_xkBc.html
COURSE_CANCEL_URL={data.get('BASE_URL', 'https://jwxt.zjjhkm.edu.cn/jwglxt')}/xsxk/zzxkyzb_tkbc.html

# ==================== 定时启动配置 ====================
SCHEDULED_START={data.get('SCHEDULED_START', '12:30')}
PRE_LOGIN_SECONDS=30

# ==================== 抢课配置 ====================
MONITOR_INTERVAL={data.get('MONITOR_INTERVAL', '5')}
RETRY_INTERVAL=2
MAX_RETRIES=-1
REQUEST_TIMEOUT=15
NOT_STARTED_RETRY_INTERVAL=30

# ==================== 邮件通知（可选）====================
EMAIL_ENABLED=False
# EMAIL_SENDER=your_email@qq.com
# EMAIL_PASSWORD=你的QQ邮箱授权码
# EMAIL_RECEIVER=接收通知的邮箱
# SMTP_SERVER=smtp.qq.com
# SMTP_PORT=587

# ==================== 日志 ====================
LOG_DIR=logs
LOG_LEVEL=DEBUG
"""
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def load_courses():
    """读取当前课程列表"""
    if os.path.exists(COURSES_FILE):
        try:
            with open(COURSES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_courses(courses):
    """保存课程列表"""
    with open(COURSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(courses, f, ensure_ascii=False, indent=2)


# ==================== HTML页面 ====================

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>抢课配置工具</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, "Microsoft YaHei", sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
    color: #333;
}
.container {
    max-width: 720px;
    margin: 0 auto;
}
.card {
    background: white;
    border-radius: 16px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    padding: 32px;
    margin-bottom: 20px;
}
h1 {
    text-align: center;
    color: white;
    font-size: 26px;
    margin-bottom: 8px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.subtitle {
    text-align: center;
    color: rgba(255,255,255,0.85);
    font-size: 14px;
    margin-bottom: 24px;
}
h2 {
    font-size: 18px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #f0f0f0;
    display: flex;
    align-items: center;
    gap: 8px;
}
h2 .icon { font-size: 20px; }
.form-group { margin-bottom: 16px; }
label {
    display: block;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 6px;
    color: #555;
}
input[type="text"], input[type="password"] {
    width: 100%;
    padding: 10px 14px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 15px;
    transition: border-color 0.2s;
    outline: none;
}
input:focus { border-color: #667eea; }
.hint {
    font-size: 12px;
    color: #999;
    margin-top: 4px;
}
.btn {
    padding: 10px 24px;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}
.btn-primary {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    width: 100%;
    padding: 14px;
    font-size: 17px;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
.btn-danger { background: #ff4757; color: white; padding: 6px 14px; font-size: 13px; }
.btn-danger:hover { background: #ee3b4b; }
.btn-success { background: #2ed573; color: white; }
.btn-outline {
    background: white;
    color: #667eea;
    border: 2px solid #667eea;
    padding: 8px 18px;
    font-size: 14px;
}
.btn-outline:hover { background: #f8f9ff; }

.course-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: #f8f9ff;
    border-radius: 10px;
    margin-bottom: 8px;
    border: 1px solid #e8e8ff;
}
.course-item .info { flex: 1; }
.course-item .name { font-weight: 600; font-size: 14px; }
.course-item .id { font-size: 12px; color: #888; margin-top: 2px; }
.course-item .del-btn {
    background: none;
    border: none;
    color: #ff4757;
    font-size: 20px;
    cursor: pointer;
    padding: 0 4px;
    line-height: 1;
}
.course-item .del-btn:hover { color: #d63031; }

.add-course-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}
.add-course-row input { flex: 1; }
.add-course-row .btn { white-space: nowrap; }

.config-row {
    display: flex;
    gap: 16px;
}
.config-row .form-group { flex: 1; }

.toast {
    display: none;
    padding: 14px 20px;
    border-radius: 10px;
    margin-bottom: 16px;
    font-weight: 500;
    text-align: center;
}
.toast.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.toast.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

.next-steps {
    background: #f0f8ff;
    border: 1px solid #b8daff;
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 16px;
    display: none;
}
.next-steps h3 { font-size: 15px; margin-bottom: 8px; color: #004085; }
.next-steps code {
    display: block;
    background: #e9ecef;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
    margin: 4px 0;
}
.badge {
    display: inline-block;
    background: #667eea;
    color: white;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-left: 6px;
}
.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.course-count { font-size: 13px; color: #888; }
</style>
</head>
<body>
<div class="container">
    <h1>📚 抢课配置工具</h1>
    <p class="subtitle">浙江金华科贸职业技术学院 · 正方教务系统 v9.0</p>

    <div id="toast" class="toast"></div>

    <!-- 个人信息 -->
    <div class="card">
        <h2><span class="icon">🔐</span> 个人信息</h2>
        <div class="form-group">
            <label>学号</label>
            <input type="text" id="studentId" placeholder="请输入学号">
        </div>
        <div class="form-group">
            <label>密码</label>
            <input type="password" id="password" placeholder="请输入教务系统密码">
            <div class="hint">密码仅保存在本地 .env 文件中，不会上传</div>
        </div>
    </div>

    <!-- 课程管理 -->
    <div class="card">
        <h2><span class="icon">📋</span> 抢课列表 <span class="badge" id="courseBadge">0 门</span></h2>

        <div id="courseList"></div>

        <div class="add-course-row">
            <input type="text" id="courseName" placeholder="课程名称（如：高等数学A）">
            <input type="text" id="courseId" placeholder="课程ID">
            <button class="btn btn-success" onclick="addCourse()">＋添加</button>
        </div>
        <div class="hint" style="margin-top:8px">
            💡 课程ID获取：登录教务系统 → 选课页面 → F12 → Network → 查看请求参数
        </div>
    </div>

    <!-- 定时设置 -->
    <div class="card">
        <h2><span class="icon">⏰</span> 定时设置</h2>
        <div class="config-row">
            <div class="form-group">
                <label>定时启动时间</label>
                <input type="text" id="scheduledStart" placeholder="12:30 或 2025-09-23 12:30">
                <div class="hint">留空则立即启动 | 仅填时间(HH:MM)则自动匹配今/明天</div>
            </div>
            <div class="form-group">
                <label>监控间隔（秒）</label>
                <input type="text" id="monitorInterval" placeholder="5">
                <div class="hint">选课开放后的检查频率，建议 3-10 秒</div>
            </div>
        </div>
    </div>

    <!-- 保存 -->
    <div class="card">
        <button class="btn btn-primary" onclick="saveConfig()">💾 保存配置</button>

        <div id="nextSteps" class="next-steps">
            <h3>✅ 配置已保存！下一步：</h3>
            <p>打开终端（CMD），执行以下命令：</p>
            <code>cd 桌面\qiangke_zjjhkm</code>
            <code>pip install -r requirements.txt</code>
            <code>python main.py</code>
            <p style="margin-top:8px;font-size:13px;color:#666;">
                或在当前目录下直接运行：<code style="display:inline;padding:2px 8px;">python main.py</code>
            </p>
        </div>
    </div>

    <p style="text-align:center;color:rgba(255,255,255,0.6);font-size:13px;margin-top:12px;">
        配置信息仅保存在本地文件，关闭此页面不影响运行
    </p>
</div>

<script>
// ========== 加载已有配置 ==========
async function loadConfig() {
    try {
        const resp = await fetch('/api/load');
        const data = await resp.json();
        if (data.env) {
            document.getElementById('studentId').value = data.env.STUDENT_ID || '';
            document.getElementById('password').value = data.env.STUDENT_PASSWORD || '';
            document.getElementById('scheduledStart').value = data.env.SCHEDULED_START || '12:30';
            document.getElementById('monitorInterval').value = data.env.MONITOR_INTERVAL || '5';
        }
        if (data.courses) {
            renderCourses(data.courses);
        }
    } catch(e) { console.log('加载配置失败', e); }
}

// ========== 课程管理 ==========
let courses = [];

function renderCourses(list) {
    courses = list || [];
    const container = document.getElementById('courseList');
    const badge = document.getElementById('courseBadge');
    badge.textContent = courses.length + ' 门';

    if (courses.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:#aaa;">还没有添加课程，请在下方添加</div>';
        return;
    }

    container.innerHTML = courses.map((c, i) => `
        <div class="course-item">
            <div class="info">
                <div class="name">${escapeHtml(c.name)}</div>
                <div class="id">ID: ${escapeHtml(c.id)}</div>
            </div>
            <button class="del-btn" onclick="removeCourse(${i})" title="删除">×</button>
        </div>
    `).join('');
}

function addCourse() {
    const nameInput = document.getElementById('courseName');
    const idInput = document.getElementById('courseId');
    const name = nameInput.value.trim();
    const id = idInput.value.trim();

    if (!name) { showToast('请输入课程名称', 'error'); nameInput.focus(); return; }
    if (!id) { showToast('请输入课程ID', 'error'); idInput.focus(); return; }

    // 检查重复
    if (courses.some(c => c.id === id)) {
        showToast('课程ID已存在', 'error');
        return;
    }

    courses.push({ name, id });
    renderCourses(courses);
    nameInput.value = '';
    idInput.value = '';
    nameInput.focus();
    showToast(`已添加: ${name}`, 'success');
}

function removeCourse(index) {
    const removed = courses[index];
    courses.splice(index, 1);
    renderCourses(courses);
    showToast(`已移除: ${removed.name}`, 'success');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 保存配置 ==========
async function saveConfig() {
    const studentId = document.getElementById('studentId').value.trim();
    const password = document.getElementById('password').value.trim();
    const scheduledStart = document.getElementById('scheduledStart').value.trim();
    const monitorInterval = document.getElementById('monitorInterval').value.trim();

    // 验证
    if (!studentId) { showToast('请输入学号', 'error'); return; }
    if (!password) { showToast('请输入密码', 'error'); return; }
    if (courses.length === 0) { showToast('请至少添加一门课程', 'error'); return; }

    const data = {
        env: {
            STUDENT_ID: studentId,
            STUDENT_PASSWORD: password,
            SCHEDULED_START: scheduledStart || '',
            MONITOR_INTERVAL: monitorInterval || '5',
        },
        courses: courses
    };

    try {
        const resp = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await resp.json();
        if (result.success) {
            showToast('✅ 配置保存成功！共 ' + courses.length + ' 门课程', 'success');
            document.getElementById('nextSteps').style.display = 'block';
        } else {
            showToast('❌ 保存失败: ' + (result.error || '未知错误'), 'error');
        }
    } catch(e) {
        showToast('❌ 保存失败: ' + e.message, 'error');
    }
}

// ========== Toast 通知 ==========
function showToast(msg, type) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

// ========== 键盘事件 ==========
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();

    document.getElementById('courseName').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('courseId').focus();
        }
    });
    document.getElementById('courseId').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addCourse();
        }
    });
});
</script>
</body>
</html>
'''


# ==================== HTTP服务器 ====================

class ConfigHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))

        elif path == '/api/load':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            env_data = load_env()
            courses_data = load_courses()
            result = {'env': env_data, 'courses': courses_data}
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        if self.path == '/api/save':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            try:
                # 保存 .env
                save_env(data['env'])
                # 保存 courses.json
                save_courses(data['courses'])
                # 保存成功后写一个 courses_loaded.flag 告诉 main.py 已配置
                flag_file = os.path.join(PROJECT_DIR, '.courses_loaded')
                with open(flag_file, 'w') as f:
                    f.write('1')

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        """静默日志"""
        pass


def open_browser():
    """延迟打开浏览器"""
    import time
    time.sleep(1.5)
    url = f'http://localhost:{PORT}'
    try:
        webbrowser.open(url)
        print(f'   🌐 已自动打开浏览器: {url}')
    except:
        print(f'   🌐 请手动打开浏览器访问: {url}')


def main():
    print('')
    print('=' * 55)
    print('    📚 浙江金华科贸职业技术学院')
    print('    🚀 抢课配置工具 (Web版)')
    print('=' * 55)
    print('')
    print(f'   服务器已启动: http://localhost:{PORT}')
    print('')
    print('   请在其他浏览器中打开此地址')
    print('   填写信息后点击"保存配置"即可')
    print('')
    print('   保存后运行: python main.py')
    print('')
    print('   [按 Ctrl+C 停止服务器]')
    print('')

    # 启动浏览器
    threading.Thread(target=open_browser, daemon=True).start()

    # 启动HTTP服务器
    server = HTTPServer((HOST, PORT), ConfigHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n   服务器已停止')
        server.server_close()


if __name__ == '__main__':
    main()