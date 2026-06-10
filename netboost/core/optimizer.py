"""NetBoost - Optimizer Module.

Applies network optimizations with user confirmation. Records rollback commands.
"""
import os
import time
import json
from datetime import datetime

from netboost import utils


class OptimizationAction:
    """Represents a single optimization action."""
    def __init__(self, action_id, title, description, expected_benefit, risk, category,
                 execute_cmd, rollback_cmd, needs_admin=True):
        self.action_id = action_id
        self.title = title
        self.description = description
        self.expected_benefit = expected_benefit
        self.risk = risk
        self.category = category
        self.execute_cmd = execute_cmd  # dict: {windows: str, darwin: str, linux: str}
        self.rollback_cmd = rollback_cmd  # dict: {windows: str, darwin: str, linux: str}
        self.needs_admin = needs_admin
        self.executed = False
        self.success = False
        self.result_msg = ""

    def to_dict(self):
        return {
            "id": self.action_id,
            "title": self.title,
            "description": self.description,
            "expected_benefit": self.expected_benefit,
            "risk": self.risk,
            "category": self.category,
            "needs_admin": self.needs_admin,
            "executed": self.executed,
            "success": self.success,
            "result_msg": self.result_msg,
        }


def generate_actions(scan_results: dict, diagnosis_report) -> list:
    """Generate optimization actions based on diagnosis."""
    actions = []
    metrics = diagnosis_report.metrics

    # 1. DNS optimization - lower threshold to be more proactive
    dns_timing = scan_results.get("dns_timing", {})
    system_avg = dns_timing.get("system_avg", -1)
    best_dns = dns_timing.get("best_public", {})

    if system_avg > 30 and best_dns.get("avg_ms", -1) > 0 and best_dns["avg_ms"] < system_avg * 0.8:
        # Extract IP from name like "阿里DNS (223.5.5.5)"
        dns_name = best_dns["name"]
        import re
        dns_ip_match = re.search(r"\(([\d.]+)\)", dns_name)
        dns_ip = dns_ip_match.group(1) if dns_ip_match else "223.5.5.5"

        # Secondary DNS
        dns_secondary = {
            "223.5.5.5": "223.6.6.6",
            "119.29.29.29": "182.254.116.116",
            "114.114.114.114": "114.114.115.115",
            "1.1.1.1": "1.0.0.1",
            "8.8.8.8": "8.8.4.4",
        }.get(dns_ip, "223.6.6.6")

        # Detect current interface name (Windows)
        iface_name = _detect_active_interface(scan_results)

        # Get current DNS for rollback
        current_dns = scan_results.get("dns", {}).get("servers", [])
        current_dns_str = current_dns[0] if current_dns else ""

        actions.append(OptimizationAction(
            action_id="dns_switch",
            title=f"切换 DNS 为 {dns_name}",
            description=f"当前系统 DNS 响应 {system_avg}ms，{dns_name} 仅需 {best_dns['avg_ms']}ms",
            expected_benefit=f"网页打开速度提升约 {int(system_avg - best_dns['avg_ms'])}ms",
            risk="low",
            category="dns",
            execute_cmd={
                "windows": f'netsh interface ip set dns name="{iface_name}" static {dns_ip} & netsh interface ip add dns name="{iface_name}" {dns_secondary} index=2',
                "darwin": f'networksetup -setdnsservers Wi-Fi {dns_ip} {dns_secondary}',
                "linux": f'echo "nameserver {dns_ip}\nnameserver {dns_secondary}" | sudo tee /etc/resolv.conf',
            },
            rollback_cmd={
                "windows": f'netsh interface ip set dns name="{iface_name}" dhcp' if not current_dns_str else f'netsh interface ip set dns name="{iface_name}" static {current_dns_str}',
                "darwin": "networksetup -setdnsservers Wi-Fi empty",
                "linux": f'echo "nameserver {current_dns_str}" | sudo tee /etc/resolv.conf' if current_dns_str else "",
            },
            needs_admin=True,
        ))

    # 2. Flush DNS cache
    if system_avg > 50:
        actions.append(OptimizationAction(
            action_id="dns_flush",
            title="刷新 DNS 缓存",
            description="清除可能过期或错误的 DNS 缓存记录",
            expected_benefit="清除错误缓存，可改善部分网站访问",
            risk="low",
            category="dns",
            execute_cmd={
                "windows": "ipconfig /flushdns",
                "darwin": "sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder",
                "linux": "sudo resolvectl flush-caches 2>/dev/null || sudo systemd-resolve --flush-caches 2>/dev/null",
            },
            rollback_cmd={
                "windows": "",  # DNS cache rebuilds automatically
                "darwin": "",
                "linux": "",
            },
            needs_admin=True,
        ))

    # 3. MTU optimization
    mtu_info = scan_results.get("mtu", {})
    if mtu_info.get("needs_change", False):
        optimal = mtu_info["optimal"]
        current = mtu_info["current"]
        iface_name = _detect_active_interface(scan_results)

        actions.append(OptimizationAction(
            action_id="mtu_adjust",
            title=f"调整 MTU 为 {optimal}",
            description=f"当前 MTU={current}，最佳值为 {optimal}，减少数据包分片",
            expected_benefit="减少丢包重传，改善稳定性",
            risk="low",
            category="mtu",
            execute_cmd={
                "windows": f'netsh interface ipv4 set subinterface "{iface_name}" mtu={optimal} store=persistent',
                "darwin": f"sudo ifconfig en0 mtu {optimal}",
                "linux": f"sudo ip link set dev $(ip route show default | awk '{{print $5}}') mtu {optimal}",
            },
            rollback_cmd={
                "windows": f'netsh interface ipv4 set subinterface "{iface_name}" mtu={current} store=persistent',
                "darwin": f"sudo ifconfig en0 mtu {current}",
                "linux": f"sudo ip link set dev $(ip route show default | awk '{{print $5}}') mtu {current}",
            },
            needs_admin=True,
        ))

    # 4. Flush DNS cache (always suggest if there are DNS or latency issues)
    has_dns_issue = any(i.category == "dns" for i in diagnosis_report.issues)
    has_latency_issue = any(i.category == "latency" for i in diagnosis_report.issues)
    flush_already = any(a.action_id == "dns_flush" for a in actions)
    if (has_dns_issue or has_latency_issue or system_avg > 50) and not flush_already:
        actions.append(OptimizationAction(
            action_id="dns_flush",
            title="刷新 DNS 缓存",
            description="清除可能过期或错误的 DNS 缓存记录",
            expected_benefit="清除错误缓存，可改善部分网站访问速度",
            risk="low",
            category="dns",
            execute_cmd={
                "windows": "ipconfig /flushdns",
                "darwin": "sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder",
                "linux": "sudo resolvectl flush-caches 2>/dev/null || sudo systemd-resolve --flush-caches 2>/dev/null",
            },
            rollback_cmd={"windows": "", "darwin": "", "linux": ""},
            needs_admin=True,
        ))

    # 5. Reset TCP/IP stack (Windows) - for latency / jitter issues
    if utils.IS_WIN and (metrics.get("latency_ms", 0) > 40 or metrics.get("jitter_ms", 0) > 15):
        actions.append(OptimizationAction(
            action_id="tcp_reset",
            title="重置 TCP/IP 网络栈优化参数",
            description="重置 Windows 网络连接参数，清理可能的网络配置积累问题",
            expected_benefit="可改善延迟和连接稳定性",
            risk="low",
            category="latency",
            execute_cmd={
                "windows": "netsh int tcp set global autotuninglevel=normal & netsh int tcp set global chimney=disabled & netsh int tcp set global rss=enabled",
                "darwin": "",
                "linux": "",
            },
            rollback_cmd={
                "windows": "netsh int tcp set global autotuninglevel=normal",
                "darwin": "",
                "linux": "",
            },
            needs_admin=True,
        ))

    # 6. Disable Nagle algorithm (reduces latency for interactive use)
    if metrics.get("latency_ms", 0) > 30 or metrics.get("jitter_ms", 0) > 10:
        if utils.IS_WIN:
            actions.append(OptimizationAction(
                action_id="nagle_disable",
                title="优化 TCP 延迟设置 (Nagle)",
                description="禁用 Nagle 算法，减少小包传输延迟，改善网页和实时应用响应",
                expected_benefit="降低交互延迟 5-20ms，网页响应更快",
                risk="low",
                category="latency",
                execute_cmd={
                    "windows": 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpNoDelay /t REG_DWORD /d 1 /f & reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpAckFrequency /t REG_DWORD /d 1 /f',
                    "darwin": "",
                    "linux": "",
                },
                rollback_cmd={
                    "windows": 'reg delete "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpNoDelay /f & reg delete "HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters" /v TcpAckFrequency /f',
                    "darwin": "",
                    "linux": "",
                },
                needs_admin=True,
            ))

    # 7. Wi-Fi reconnect suggestion (for weak signal or high jitter)
    wifi = scan_results.get("wifi", {})
    if wifi.get("connected") and (wifi.get("signal_pct", 100) < 50 or metrics.get("jitter_ms", 0) > 20):
        iface_name = _detect_active_interface(scan_results)
        actions.append(OptimizationAction(
            action_id="wifi_reconnect",
            title="重新连接 Wi-Fi（刷新连接）",
            description="断开并重新连接 Wi-Fi，让设备重新选择最佳接入点和信道",
            expected_benefit="可改善信号和减少抖动",
            risk="low",
            category="wifi",
            execute_cmd={
                "windows": f'netsh wlan disconnect & timeout /t 3 /nobreak >nul & netsh wlan connect name="{wifi.get("ssid", "")}"',
                "darwin": f'networksetup -setairportpower en0 off && sleep 3 && networksetup -setairportpower en0 on',
                "linux": "nmcli radio wifi off && sleep 3 && nmcli radio wifi on",
            },
            rollback_cmd={"windows": "", "darwin": "", "linux": ""},
            needs_admin=False,
        ))

    # 8. Disable auto proxy detection (Windows) - can cause latency
    proxy = scan_results.get("proxy", {})
    if utils.IS_WIN:
        # Check if auto proxy detection is enabled (common cause of slowness)
        reg_output = utils.run_cmd('reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\Connections" /v DefaultConnectionSettings 2>nul')
        if reg_output:
            actions.append(OptimizationAction(
                action_id="disable_auto_proxy",
                title="关闭自动检测代理设置",
                description="Windows 的'自动检测代理'功能会在每次网络请求前尝试探测代理，导致额外延迟",
                expected_benefit="减少每次连接 0.5-2 秒的代理探测延迟",
                risk="low",
                category="proxy",
                execute_cmd={
                    "windows": 'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v AutoDetect /t REG_DWORD /d 0 /f',
                    "darwin": "",
                    "linux": "",
                },
                rollback_cmd={
                    "windows": 'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v AutoDetect /t REG_DWORD /d 1 /f',
                    "darwin": "",
                    "linux": "",
                },
                needs_admin=False,
            ))

    return actions


def _detect_active_interface(scan_results: dict) -> str:
    """Detect the active network interface name for commands."""
    if utils.IS_WIN:
        interfaces = scan_results.get("interfaces", [])
        for iface in interfaces:
            if iface.get("gateway") or iface.get("ipv4"):
                name = iface.get("name", "")
                # Clean up Windows interface name
                if "WLAN" in name or "Wi-Fi" in name or "无线" in name or "Wireless" in name:
                    return "WLAN"
                elif "以太网" in name or "Ethernet" in name:
                    return "以太网"
                elif "本地连接" in name or "Local Area" in name:
                    return name
        return "WLAN"  # default
    elif utils.IS_MAC:
        return "en0"
    else:
        output = utils.run_cmd("ip route show default")
        import re
        m = re.search(r"dev (\S+)", output)
        return m.group(1) if m else "eth0"


def execute_action(action: OptimizationAction, log_callback=None) -> bool:
    """Execute a single optimization action. Returns True on success."""
    def log(msg):
        if log_callback:
            log_callback(msg)

    platform_key = "windows" if utils.IS_WIN else ("darwin" if utils.IS_MAC else "linux")
    cmd = action.execute_cmd.get(platform_key, "")

    if not cmd:
        action.result_msg = "此平台暂不支持此优化"
        action.executed = True
        action.success = False
        return False

    log(f"正在执行: {action.title}")
    output = utils.run_cmd(cmd, timeout=15)

    # Simple success check
    if utils.IS_WIN:
        # Windows commands usually don't output error messages on success
        success = "错误" not in output and "failed" not in output.lower() and "error" not in output.lower()
    else:
        success = True  # TODO: better checking

    action.executed = True
    action.success = success
    action.result_msg = "执行成功" if success else f"执行可能失败: {output[:200]}"

    if success:
        log(f"✅ {action.title} - 完成")
    else:
        log(f"❌ {action.title} - {action.result_msg}")

    return success


def save_rollback(actions: list, filepath: str = None) -> str:
    """Save rollback commands to file."""
    if filepath is None:
        filepath = os.path.join(os.path.expanduser("~"), "netboost_rollback")
        if utils.IS_WIN:
            filepath += ".bat"
        else:
            filepath += ".sh"

    platform_key = "windows" if utils.IS_WIN else ("darwin" if utils.IS_MAC else "linux")
    executed = [a for a in actions if a.executed and a.success]

    if not executed:
        return ""

    lines = []
    if utils.IS_WIN:
        lines.append("@echo off")
        lines.append(f"REM NetBoost Rollback Script - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("REM Run this script as Administrator to undo all NetBoost optimizations")
        lines.append("")
    else:
        lines.append("#!/bin/bash")
        lines.append(f"# NetBoost Rollback Script - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("# Run this script with sudo to undo all NetBoost optimizations")
        lines.append("")

    for action in reversed(executed):
        cmd = action.rollback_cmd.get(platform_key, "")
        if cmd:
            lines.append(f"echo Reverting: {action.title}")
            lines.append(cmd)
            lines.append("")

    if utils.IS_WIN:
        lines.append("echo All changes reverted.")
        lines.append("pause")
    else:
        lines.append('echo "All changes reverted."')

    content = "\n".join(lines)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        if not utils.IS_WIN:
            os.chmod(filepath, 0o755)
    except Exception:
        # Fall back to temp dir
        import tempfile
        filepath = os.path.join(tempfile.gettempdir(), os.path.basename(filepath))
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return filepath


