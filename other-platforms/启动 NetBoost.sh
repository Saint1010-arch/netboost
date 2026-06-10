#!/bin/bash
# NetBoost Launcher for Linux
# chmod +x 后双击运行

cd "$(dirname "$0")"

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
    echo ""
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║  未检测到 Python 3                           ║"
    echo "  ║                                              ║"
    echo "  ║  请安装:                                     ║"
    echo "  ║  Ubuntu/Debian: sudo apt install python3     ║"
    echo "  ║  Fedora: sudo dnf install python3            ║"
    echo "  ║  Arch: sudo pacman -S python                 ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

# 检查 tkinter
$PYTHON_CMD -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  提示: 未检测到 tkinter，将使用命令行模式"
    echo "  如需 GUI 请安装: sudo apt install python3-tk"
    echo ""
    $PYTHON_CMD netboost.py --cli
else
    $PYTHON_CMD netboost.py
fi
