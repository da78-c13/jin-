# 浙江金华科贸职业技术学院 - 自动抢课工具

基于 [wolverine396/qiangke](https://github.com/wolverine396/qiangke) 改造，适配本校正方教务系统 v9.0。

## 功能

- ✅ 自动登录教务系统（支持 RSA 加密密码）
- ✅ 监控指定课程的剩余名额
- ✅ 发现空位立即自动抢课
- ✅ 邮件通知（可选，支持 QQ 邮箱）
- ✅ 详细日志记录
- ✅ 失败自动重试

## 环境要求

- Python 3.8+
- 网络连接

## 快速开始

### 1. 安装依赖

```bash
cd qiangke_zjjhkm
pip install -r requirements.txt
```

### 2. 配置学号和密码

`.env` 文件中已经配置了你的学号和密码，无需修改。

### 3. 配置要监控的课程

编辑 `main.py` 文件，在 `步骤2` 区域添加你要监控的课程：

```python
# 添加要监控的课程
monitor.add_course("课程名称1", "课程ID1")
monitor.add_course("课程名称2", "课程ID2")
```

### 4. 运行程序

```bash
python main.py
```

## 如何获取课程ID

1. 浏览器打开教务系统并登录：https://jwxt.zjjhkm.edu.cn/jwglxt/
2. 进入选课界面
3. 按 **F12** 打开开发者工具
4. 切换到 **Network（网络）** 标签
5. 在选课页面中选择一门课程
6. 在网络请求中找到包含课程信息的请求
7. 从请求参数或响应中获取课程ID

## 程序说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序入口 |
| `config.py` | 配置文件 |
| `logger.py` | 日志模块 |
| `zhengfang_login.py` | 正方系统登录模块（RSA加密） |
| `course_monitor.py` | 课程监控和抢课模块 |
| `email_sender.py` | 邮件通知模块 |
| `.env` | 环境变量配置（含敏感信息） |
| `requirements.txt` | Python 依赖 |
| `logs/qiangke.log` | 运行日志文件 |

## 注意事项

⚠️ **重要提醒**：
- `.env` 文件包含你的学号密码，**不要**分享给他人
- 不要将本项目上传到公开的 GitHub 仓库
- 监控间隔建议 30 秒以上，避免对教务系统造成压力
- 本工具仅用于学习目的，请遵守学校相关规定
- 使用本工具产生的后果由用户自行承担

## 故障排除

### 登录失败
1. 检查 `.env` 文件中的学号和密码是否正确
2. 检查是否能正常访问 https://jwxt.zjjhkm.edu.cn/jwglxt/
3. 查看 `logs/qiangke.log` 了解详细错误信息

### 课程查询失败
1. 确认课程ID是否正确
2. 选课系统可能尚未开放
3. 检查 `COURSE_QUERY_URL` 配置是否需要修改

### 需要调整API地址
不同学校的正方系统 API 地址可能略有不同，如果默认的接口无法使用，请通过浏览器开发者工具获取正确的接口地址：
1. 登录教务系统，进入选课界面
2. F12 -> Network
3. 执行选课操作，查看请求的 URL
4. 将正确的 URL 更新到 `.env` 文件中

## 许可证

MIT License