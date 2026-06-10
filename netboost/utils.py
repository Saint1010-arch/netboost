"""NetBoost - Network diagnosis and optimization tool.

Utility functions for cross-platform support.
"""
import platform
import subprocess
import sys
import locale
import os
import re
import time
import socket
import struct


PLATFORM = platform.system().lower()  # 'windows', 'darwin', 'linux'
IS_WIN = PLATFORM == "windows"
IS_MAC = PLATFORM == "darwin"
IS_LINUX = PLATFORM == "linux"

# ---------- i18n ----------

_LANG = "zh"

TEXTS = {
    "zh": {
        "title": "NetBoost - 网络加速助手",
        "scanning": "正在扫描网络环境...",
        "scan_done": "扫描完成",
        "speedtest_ask": "测速将消耗约 30-80 MB 流量，是否继续？",
        "speedtest_running": "正在测速...",
        "speedtest_download": "正在测试下载速度...",
        "speedtest_upload": "正在测试上传速度...",
        "speedtest_done": "测速完成",
        "diagnosing": "正在分析诊断结果...",
        "diagnosis_done": "诊断完成",
        "optimize_ask": "是否执行以下优化？",
        "optimizing": "正在执行优化...",
        "optimize_done": "优化完成",
        "after_ask": "优化完成！是否再测一次看看效果？",
        "comparing": "正在生成对比报告...",
        "compare_done": "对比完成",
        "score_excellent": "优秀",
        "score_good": "良好",
        "score_fair": "一般",
        "score_poor": "较差",
        "yes": "是",
        "no": "否",
        "approve": "批准",
        "skip": "跳过",
        "start_diagnose": "开始诊断",
        "export_report": "导出报告",
        "rollback": "还原改动",
        "before": "优化前",
        "after": "优化后",
        "change": "变化",
        "metric": "指标",
        "download_speed": "下载速度",
        "upload_speed": "上传速度",
        "latency": "延迟",
        "jitter": "抖动",
        "packet_loss": "丢包率",
        "dns_time": "DNS 响应",
        "wifi_signal": "Wi-Fi 信号",
        "network_score": "网络评分",
        "risk_low": "低",
        "risk_medium": "中",
        "risk_high": "高",
        "issue_severity_critical": "严重",
        "issue_severity_warning": "警告",
        "issue_severity_info": "提示",
        "no_issues": "未发现明显问题",
        "issues_found": "发现 {} 个问题",
        "recommend_optimize": "建议优化",
        "no_optimize_needed": "网络状态良好，无需优化",
        "rollback_saved": "还原命令已保存到: {}",
        "admin_required": "此操作需要管理员权限",
        "status_ok": "正常",
        "status_optimized": "已优化",
    },
    "en": {
        "title": "NetBoost - Network Booster",
        "scanning": "Scanning network environment...",
        "scan_done": "Scan complete",
        "speedtest_ask": "Speed test will consume ~30-80 MB. Continue?",
        "speedtest_running": "Running speed test...",
        "speedtest_download": "Testing download speed...",
        "speedtest_upload": "Testing upload speed...",
        "speedtest_done": "Speed test complete",
        "diagnosing": "Analyzing results...",
        "diagnosis_done": "Diagnosis complete",
        "optimize_ask": "Execute the following optimizations?",
        "optimizing": "Optimizing...",
        "optimize_done": "Optimization complete",
        "after_ask": "Optimization done! Run another speed test to compare?",
        "comparing": "Generating comparison report...",
        "compare_done": "Comparison complete",
        "score_excellent": "Excellent",
        "score_good": "Good",
        "score_fair": "Fair",
        "score_poor": "Poor",
        "yes": "Yes",
        "no": "No",
        "approve": "Approve",
        "skip": "Skip",
        "start_diagnose": "Start Diagnosis",
        "export_report": "Export Report",
        "rollback": "Rollback Changes",
        "before": "Before",
        "after": "After",
        "change": "Change",
        "metric": "Metric",
        "download_speed": "Download",
        "upload_speed": "Upload",
        "latency": "Latency",
        "jitter": "Jitter",
        "packet_loss": "Packet Loss",
        "dns_time": "DNS Response",
        "wifi_signal": "Wi-Fi Signal",
        "network_score": "Network Score",
        "risk_low": "Low",
        "risk_medium": "Medium",
        "risk_high": "High",
        "issue_severity_critical": "Critical",
        "issue_severity_warning": "Warning",
        "issue_severity_info": "Info",
        "no_issues": "No issues found",
        "issues_found": "{} issues found",
        "recommend_optimize": "Optimization recommended",
        "no_optimize_needed": "Network looks good, no optimization needed",
        "rollback_saved": "Rollback commands saved to: {}",
        "admin_required": "This operation requires admin privileges",
        "status_ok": "OK",
        "status_optimized": "Optimized",
    },
}


def set_lang(lang: str):
    global _LANG
    _LANG = lang if lang in TEXTS else "zh"


def t(key: str, *args) -> str:
    text = TEXTS.get(_LANG, TEXTS["zh"]).get(key, key)
    if args:
        return text.format(*args)
    return text


# ---------- Shell helpers ----------

def run_cmd(cmd: str, timeout: int = 15, encoding: str = None) -> str:
    """Run a shell command and return stdout. Returns empty string on failure."""
    try:
        if IS_WIN:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=timeout,
            )
        # Try decoding with multiple encodings
        raw = result.stdout
        if not raw.strip():
            raw = result.stderr
        if encoding:
            return raw.decode(encoding, errors="replace")
        if IS_WIN:
            # Try utf-8 first, then gbk
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("gbk", errors="replace")
        else:
            return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def is_admin() -> bool:
    """Check if running with admin/root privileges."""
    if IS_WIN:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


# ---------- Color helpers for CLI ----------

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @staticmethod
    def enable():
        """Enable ANSI colors on Windows."""
        if IS_WIN:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass


def colored(text: str, color: str) -> str:
    return f"{color}{text}{Color.RESET}"


def bold(text: str) -> str:
    return f"{Color.BOLD}{text}{Color.RESET}"


# ---------- DNS resolution timer ----------

def dns_resolve_time(host: str, dns_server: str = None, timeout: float = 5.0) -> float:
    """Resolve a hostname and return time in ms. Returns -1 on failure."""
    if dns_server:
        # Use nslookup to query specific DNS server
        cmd = f"nslookup {host} {dns_server}" if IS_WIN else f"nslookup {host} {dns_server}"
        start = time.time()
        result = run_cmd(cmd, timeout=int(timeout) + 2)
        elapsed = (time.time() - start) * 1000
        if "can't find" in result.lower() or "timed out" in result.lower() or not result.strip():
            return -1
        return round(elapsed, 1)
    else:
        start = time.time()
        try:
            socket.setdefaulttimeout(timeout)
            socket.getaddrinfo(host, 80)
            elapsed = (time.time() - start) * 1000
            return round(elapsed, 1)
        except Exception:
            return -1


# ---------- Ping helper ----------

def ping(host: str, count: int = 10, timeout: int = 3) -> dict:
    """Ping a host and return stats dict: avg_ms, min_ms, max_ms, loss_pct, jitter_ms."""
    if IS_WIN:
        cmd = f"ping -n {count} -w {timeout * 1000} {host}"
    else:
        cmd = f"ping -c {count} -W {timeout} {host}"

    output = run_cmd(cmd, timeout=count * timeout + 10)

    result = {"avg_ms": -1, "min_ms": -1, "max_ms": -1, "loss_pct": -1, "jitter_ms": -1, "raw": output}

    # Parse packet loss
    loss_match = re.search(r"(\d+)%", output)
    if loss_match:
        result["loss_pct"] = float(loss_match.group(1))

    # Parse times
    times = []
    if IS_WIN:
        # Windows: "时间=Xms" or "time=Xms" or "time<1ms"
        for m in re.finditer(r"[=<](\d+)ms", output):
            times.append(float(m.group(1)))
    else:
        # Unix: "time=X.X ms"
        for m in re.finditer(r"time[=](\d+\.?\d*)\s*ms", output):
            times.append(float(m.group(1)))

    if times:
        result["avg_ms"] = round(sum(times) / len(times), 1)
        result["min_ms"] = round(min(times), 1)
        result["max_ms"] = round(max(times), 1)
        if len(times) > 1:
            mean = sum(times) / len(times)
            variance = sum((x - mean) ** 2 for x in times) / len(times)
            result["jitter_ms"] = round(variance ** 0.5, 1)

    return result

