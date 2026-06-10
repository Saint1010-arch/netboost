#!/bin/bash
# NetBoost Launcher for macOS
# 双击此文件即可运行 NetBoost

cd "$(dirname "$0")"

# 检测 Python
PYTHON_CMD=""

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    ver=$(python --version 2>&1 | grep -oP '3\.\d+')
    if [ -n "$ver" ]; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    osascript -e 'display dialog "未检测到 Python 3\n\n请先安装 Python:\n1. 打开 Terminal\n2. 输入: brew install python3\n\n或访问 python.org 下载安装" with title "NetBoost" buttons {"打开下载页", "取消"} default button "打开下载页"'
    if [ $? -eq 0 ]; then
        open "https://www.python.org/downloads/"
    fi
    exit 1
fi

# 检查版本
$PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    osascript -e 'display dialog "Python 版本过低，需要 3.7+" with title "NetBoost" buttons {"确定"}'
    exit 1
fi

# 启动
$PYTHON_CMD netboost.py
