#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===================================================
  📦 抢课工具 - 一键安装依赖脚本
===================================================
  用法：双击运行 或 在终端执行：
    python install_deps.py
===================================================
"""

import subprocess
import sys
import os

# Windows下让输出显示UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PACKAGES = [
    'requests>=2.25.0',
    'beautifulsoup4>=4.9.0',
    'selenium>=3.141.0',
    'Pillow>=8.0.0',
    'pycryptodome>=3.10.0',
    'rsa>=4.7',
    'python-dotenv>=0.15.0',
    'lxml>=4.6.0',
]


def print_banner():
    print()
    print('=' * 55)
    print('   📦  浙江金华科贸职业技术学院')
    print('   🚀  抢课工具 - 一键安装依赖')
    print('=' * 55)
    print()


def check_python():
    """检查Python版本"""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print(f'   ❌ Python版本过低: {v.major}.{v.minor}.{v.micro}')
        print('      需要 Python 3.8 或更高版本')
        print('      请前往 https://www.python.org/downloads/ 下载安装')
        return False
    print(f'   ✅ Python {v.major}.{v.minor}.{v.micro}')
    return True


def get_pip():
    """获取 pip 命令"""
    # 优先使用当前 Python 的 pip
    python_exe = sys.executable
    pip_cmds = [
        [python_exe, '-m', 'pip'],
        [python_exe, '-m', 'pip3'],
    ]
    for cmd in pip_cmds:
        try:
            result = subprocess.run(
                [*cmd, '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return cmd
        except:
            continue

    # 最后尝试直接 pip
    for pip_name in ['pip', 'pip3']:
        try:
            result = subprocess.run(
                [pip_name, '--version'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return [pip_name]
        except:
            continue

    return None


def install_packages(pip_cmd):
    """安装依赖包"""
    print()
    print('   ⏳ 正在安装依赖包...')
    print()

    success = 0
    fail = 0

    for pkg in PACKAGES:
        pkg_name = pkg.split('>=')[0].split('=')[0]
        print(f'   📥 正在安装: {pkg_name}...', end=' ', flush=True)

        try:
            # 先升级 pip 本身
            if pkg == PACKAGES[0]:
                subprocess.run(
                    [*pip_cmd, 'install', '--upgrade', 'pip'],
                    capture_output=True, text=True, timeout=60
                )

            result = subprocess.run(
                [*pip_cmd, 'install', pkg],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                # 检查是否真的安装了（避免 already satisfied 但无版本号）
                check = subprocess.run(
                    [*pip_cmd, 'show', pkg_name],
                    capture_output=True, text=True, timeout=10
                )
                if check.returncode == 0:
                    # 提取版本号
                    for line in check.stdout.splitlines():
                        if line.lower().startswith('version'):
                            ver = line.split(':')[1].strip()
                            print(f'✅ {ver}')
                            break
                    else:
                        print('✅')
                else:
                    print('⚠️  可能未安装成功')
                    fail += 1
                success += 1
            else:
                print('❌')
                error_msg = result.stderr.strip()[:100] if result.stderr else '未知错误'
                print(f'      原因: {error_msg}')
                fail += 1

        except subprocess.TimeoutExpired:
            print('⏰ 超时')
            fail += 1
        except Exception as e:
            print(f'❌')
            print(f'      异常: {str(e)[:80]}')
            fail += 1

    return success, fail


def print_summary(success, fail):
    """打印安装结果"""
    total = len(PACKAGES)
    print()
    print('=' * 55)

    if fail == 0:
        print('   ✅  全部安装成功！')
    else:
        print(f'   ⚠️  安装完成: {success}/{total} 成功, {fail} 失败')

    print()
    print('   🚀 接下来你可以：')
    print()
    print('      方法1（推荐）：打开网页配置工具')
    print('        python config_web.py')
    print()
    print('      方法2：直接运行抢课程序')
    print('        python main.py')
    print()
    print('      方法3：测试登录是否正常')
    print('        python main.py test')
    print()
    print('=' * 55)
    print()

    if fail > 0:
        print('   💡 失败的包可以手动安装：')
        for pkg in PACKAGES:
            print(f'      pip install {pkg}')
        print()


def main():
    print_banner()

    # 检查Python
    if not check_python():
        input('\n   按回车键退出...')
        sys.exit(1)

    print(f'   路径: {sys.executable}')
    print()

    # 检查pip
    pip_cmd = get_pip()
    if not pip_cmd:
        print('   ❌ 未找到 pip，请确保 Python 已正确安装')
        input('\n   按回车键退出...')
        sys.exit(1)

    pip_version = subprocess.run(
        [*pip_cmd, '--version'],
        capture_output=True, text=True, timeout=10
    ).stdout.strip()
    print(f'   ✅ {pip_version}')
    print()

    # 询问是否继续
    print(f'   将要安装 {len(PACKAGES)} 个依赖包:')
    for pkg in PACKAGES:
        print(f'      - {pkg}')
    print()

    try:
        if sys.platform == 'win32':
            choice = input('   是否继续安装？(Y/n): ').strip().lower()
        else:
            choice = input('   是否继续安装？(Y/n): ').strip().lower()
    except:
        choice = 'y'

    if choice == 'n' or choice == 'no':
        print('\n   已取消安装')
        return

    # 开始安装
    success, fail = install_packages(pip_cmd)

    # 打印结果
    print_summary(success, fail)

    # 安装后自动运行 config_web.py
    if fail == 0 and success > 0:
        try:
            choice2 = input('   是否立即启动网页配置工具？(Y/n): ').strip().lower()
            if choice2 != 'n':
                print('\n   🌐 正在启动配置工具...')
                print()
                subprocess.run([sys.executable, 'config_web.py'])
        except:
            pass

    # 暂停（双击运行时可以看到结果）
    if sys.platform == 'win32':
        input('\n   按回车键退出...')


if __name__ == '__main__':
    main()