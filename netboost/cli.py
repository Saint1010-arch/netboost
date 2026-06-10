"""NetBoost - CLI Interface."""
import sys
import time
import io

# Fix UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from . import utils
from .core import scanner, speedtest, diagnosis, optimizer, compare


def cli_main(args=None):
    """Main CLI entry point."""
    utils.Color.enable()

    import argparse
    parser = argparse.ArgumentParser(
        description="NetBoost - 网络诊断优化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli", action="store_true", help="强制 CLI 模式")
    parser.add_argument("--diagnose-only", action="store_true", help="只做诊断，不测速不优化")
    parser.add_argument("--speedtest-only", action="store_true", help="只测速")
    parser.add_argument("--no-speedtest", action="store_true", help="跳过测速")
    parser.add_argument("--rollback", action="store_true", help="还原所有改动")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="语言")
    parser.add_argument("--export", type=str, help="导出报告到文件 (md/html)")

    parsed = parser.parse_args(args)
    utils.set_lang(parsed.lang)

    if parsed.rollback:
        _do_rollback()
        return

    if parsed.speedtest_only:
        _do_speedtest_only()
        return

    _print_banner()
    _run_full_flow(
        diagnose_only=parsed.diagnose_only,
        no_speedtest=parsed.no_speedtest,
        export_path=parsed.export,
    )


def _print_banner():
    banner = f"""
{utils.colored('⚡ NetBoost', utils.Color.CYAN + utils.Color.BOLD)} - {utils.t('title')}
{utils.colored('━' * 50, utils.Color.GRAY)}
"""
    print(banner)


def _log(msg):
    timestamp = time.strftime("%H:%M:%S")
    print(f"  {utils.colored(f'[{timestamp}]', utils.Color.GRAY)} {msg}")


def _run_full_flow(diagnose_only=False, no_speedtest=False, export_path=None):
    """Run the full diagnosis -> speedtest -> optimize -> verify flow."""

    # ========== Phase 1: Scan ==========
    print(f"\n{utils.bold('📡 第一阶段：网络环境扫描')}")
    print(f"  {utils.colored('（只读检查，不修改任何设置）', utils.Color.GRAY)}\n")

    scan_results = scanner.scan_all(log_callback=_log)

    _print_scan_summary(scan_results)

    # ========== Phase 2: Before Speed Test ==========
    speed_results = None
    if not no_speedtest and not diagnose_only:
        print(f"\n{utils.bold('📊 第二阶段：Before 测速')}")
        if _ask_yes_no(f"  {utils.t('speedtest_ask')}"):
            speed_results = speedtest.run_speedtest(log_callback=_log)
            _print_speed_results(speed_results)
        else:
            print(f"  {utils.colored('已跳过测速', utils.Color.GRAY)}")

    # ========== Phase 3: Diagnosis ==========
    print(f"\n{utils.bold('🔍 第三阶段：诊断报告')}\n")

    report = diagnosis.diagnose(scan_results, speed_results)
    _print_diagnosis(report)

    if diagnose_only:
        if export_path:
            _export_report(report, scan_results, speed_results, None, None, export_path)
        print(f"\n{utils.colored('（仅诊断模式，流程结束）', utils.Color.GRAY)}")
        return

    # ========== Phase 4: Optimization ==========
    optimizable_issues = [i for i in report.issues if i.optimizable]
    if not optimizable_issues:
        print(f"\n{utils.colored(utils.t('no_optimize_needed'), utils.Color.GREEN)}")
        if export_path:
            _export_report(report, scan_results, speed_results, None, None, export_path)
        return

    print(f"\n{utils.bold('🛠️  第四阶段：优化建议')}\n")

    actions = optimizer.generate_actions(scan_results, report)
    if not actions:
        print(f"  {utils.colored('未生成可执行的优化方案', utils.Color.YELLOW)}")
        return

    # Display actions and ask for approval
    for i, action in enumerate(actions, 1):
        risk_color = {
            "low": utils.Color.GREEN,
            "medium": utils.Color.YELLOW,
            "high": utils.Color.RED,
        }.get(action.risk, utils.Color.GRAY)

        print(f"  [{i}] {utils.bold(action.title)}")
        print(f"      {action.description}")
        print(f"      预期改善: {utils.colored(action.expected_benefit, utils.Color.GREEN)}")
        print(f"      风险: {utils.colored(action.risk, risk_color)}")
        if action.needs_admin:
            print(f"      {utils.colored('⚠ 需要管理员权限', utils.Color.YELLOW)}")
        print()

    # Ask which to execute
    print(f"  {utils.bold('请输入要执行的优化项编号')}")
    print(f"  （多个用逗号分隔，all=全部，n=跳过）")
    choice = input(f"  > ").strip().lower()

    if choice in ("n", "no", ""):
        print(f"\n  {utils.colored('已跳过优化', utils.Color.GRAY)}")
    else:
        if choice == "all":
            selected = actions
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
                selected = [actions[i] for i in indices if 0 <= i < len(actions)]
            except (ValueError, IndexError):
                print(f"  {utils.colored('输入无效，跳过优化', utils.Color.RED)}")
                selected = []

        # ========== Phase 5: Execute ==========
        if selected:
            print(f"\n{utils.bold('⚡ 第五阶段：执行优化')}\n")

            for action in selected:
                optimizer.execute_action(action, log_callback=_log)
                time.sleep(0.5)

            # Save rollback
            rollback_path = optimizer.save_rollback(selected)
            if rollback_path:
                print(f"\n  {utils.colored(utils.t('rollback_saved', rollback_path), utils.Color.GRAY)}")

    # ========== Phase 6: After Speed Test ==========
    after_speed = None
    after_report = None
    executed_actions = [a for a in actions if a.executed and a.success] if 'actions' in dir() else []

    if executed_actions and not no_speedtest:
        print(f"\n{utils.bold('📊 第六阶段：After 测速')}")
        if _ask_yes_no(f"  {utils.t('after_ask')}"):
            # Quick re-scan DNS timing
            _log("正在重新检测 DNS 响应...")
            scan_results_after = dict(scan_results)
            scan_results_after["dns_timing"] = scanner.scan_dns_timing()

            after_speed = speedtest.run_speedtest(log_callback=_log)
            _print_speed_results(after_speed)

            after_report = diagnosis.diagnose(scan_results_after, after_speed)

            # ========== Phase 7: Comparison ==========
            print(f"\n{utils.bold('📈 第七阶段：Before/After 对比')}\n")

            before_data = {
                "download_mbps": speed_results.get("download_mbps", 0) if speed_results else 0,
                "upload_mbps": speed_results.get("upload_mbps", 0) if speed_results else 0,
                "latency_ms": speed_results.get("latency_ms", -1) if speed_results else report.metrics.get("latency_ms", -1),
                "jitter_ms": speed_results.get("jitter_ms", -1) if speed_results else report.metrics.get("jitter_ms", -1),
                "packet_loss_pct": speed_results.get("packet_loss_pct", -1) if speed_results else report.metrics.get("packet_loss_pct", -1),
                "dns_avg_ms": report.metrics.get("dns_avg_ms", -1),
                "score": report.score,
            }
            after_data = {
                "download_mbps": after_speed.get("download_mbps", 0),
                "upload_mbps": after_speed.get("upload_mbps", 0),
                "latency_ms": after_speed.get("latency_ms", -1),
                "jitter_ms": after_speed.get("jitter_ms", -1),
                "packet_loss_pct": after_speed.get("packet_loss_pct", -1),
                "dns_avg_ms": scan_results_after.get("dns_timing", {}).get("system_avg", -1),
                "score": after_report.score,
            }

            comp = compare.compare(before_data, after_data)
            table = compare.format_comparison_table(comp)
            print(table)
            print()
            print(comp["summary"])

            # Recommendations
            print(f"\n{utils.bold('📋 建议')}")
            for action in executed_actions:
                print(f"  {'✅' if action.success else '❌'} {action.title}: {'建议保留' if action.success else '建议还原'}")

            if rollback_path:
                print(f"\n  如需还原: python netboost.py --rollback")
                print(f"  或运行: {rollback_path}")

    if export_path:
        _export_report(report, scan_results, speed_results, after_speed, after_report, export_path)

    print(f"\n{utils.colored('━' * 50, utils.Color.GRAY)}")
    print(f"{utils.colored('感谢使用 NetBoost ⚡', utils.Color.CYAN)}")
    print(f"{utils.colored('GitHub: https://github.com/yourname/netboost', utils.Color.GRAY)}\n")


def _print_scan_summary(results):
    """Print a brief scan summary."""
    print(f"\n  {utils.bold('扫描结果摘要:')}")

    # Interfaces
    interfaces = results.get("interfaces", [])
    active = [i for i in interfaces if i.get("ipv4")]
    if active:
        for iface in active:
            name = iface.get("description", iface.get("name", "未知"))
            ip = iface.get("ipv4", "")
            print(f"    网络接口: {name} ({ip})")

    # Gateway
    gw = results.get("gateway", {})
    if gw.get("ip"):
        print(f"    默认网关: {gw['ip']}")

    # DNS
    dns = results.get("dns", {})
    if dns.get("servers"):
        print(f"    DNS 服务器: {', '.join(dns['servers'][:3])}")

    # Wi-Fi
    wifi = results.get("wifi", {})
    if wifi.get("connected"):
        sig = f"{wifi['signal_pct']}%" if wifi.get("signal_pct", -1) >= 0 else "未知"
        print(f"    Wi-Fi: {wifi.get('ssid', '已连接')} (信号 {sig})")

    # VPN
    vpn = results.get("vpn", {})
    if vpn.get("active"):
        print(f"    VPN: {utils.colored('活跃', utils.Color.YELLOW)} ({vpn.get('type', '未知类型')})")

    # Proxy
    proxy = results.get("proxy", {})
    if proxy.get("enabled"):
        print(f"    代理: {utils.colored('已启用', utils.Color.YELLOW)}")


def _print_speed_results(results):
    """Print speed test results."""
    print()
    print("  " + utils.bold("????:"))
    dl_str = str(results["download_mbps"]) + " Mbps"
    ul_str = str(results["upload_mbps"]) + " Mbps"
    print("    DL ??: " + utils.colored(dl_str, utils.Color.CYAN))
    print("    UL ??: " + utils.colored(ul_str, utils.Color.CYAN))
    print("    ??: " + str(results["latency_ms"]) + " ms")
    print("    ??: " + str(results["jitter_ms"]) + " ms")
    print("    ??: " + str(results["packet_loss_pct"]) + "%")
    err = results.get("error", "")
    if err:
        print("    " + utils.colored(err, utils.Color.YELLOW))


def _print_diagnosis(report):
    """Print diagnosis report with score and issues."""
    # Score display
    score = report.score
    if score >= 90:
        score_color = utils.Color.GREEN
    elif score >= 70:
        score_color = utils.Color.BLUE
    elif score >= 50:
        score_color = utils.Color.YELLOW
    else:
        score_color = utils.Color.RED

    print(f"  ┌{'─' * 40}┐")
    print(f"  │  网络健康评分: {utils.colored(f'{score}/100', score_color + utils.Color.BOLD):>30} │")
    print(f"  │  状态: {utils.colored(report.score_label, score_color):>35} │")
    print(f"  └{'─' * 40}┘")

    # Score breakdown
    print(f"\n  {utils.bold('评分明细:')}")
    labels = {
        "download": ("下载速度", 25),
        "upload": ("上传速度", 15),
        "latency": ("延迟", 20),
        "dns": ("DNS 响应", 20),
        "packet_loss": ("丢包率", 10),
        "wifi": ("Wi-Fi", 10),
    }
    for key, (label, max_score) in labels.items():
        val = report.score_breakdown.get(key, 0)
        bar_len = int(val / max_score * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        color = utils.Color.GREEN if val >= max_score * 0.8 else (utils.Color.YELLOW if val >= max_score * 0.5 else utils.Color.RED)
        print(f"    {label:<10} {utils.colored(bar, color)} {val}/{max_score}")

    # Issues
    if report.issues:
        print(f"\n  {utils.bold(utils.t('issues_found', len(report.issues)))}\n")
        for issue in report.issues:
            sev_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "⚪")
            sev_label = {
                "critical": utils.t("issue_severity_critical"),
                "warning": utils.t("issue_severity_warning"),
                "info": utils.t("issue_severity_info"),
            }.get(issue.severity, "")

            print(f"  {sev_icon} [{sev_label}] {utils.bold(issue.title)}")
            print(f"     证据: {issue.evidence}")
            print(f"     影响: {issue.impact}")
            risk_color = {"low": utils.Color.GREEN, "medium": utils.Color.YELLOW, "high": utils.Color.RED}.get(issue.risk, "")
            print(f"     风险: {utils.colored(issue.risk, risk_color)} | 建议: {issue.recommendation}")
            print()
    else:
        print(f"\n  {utils.colored('✅ ' + utils.t('no_issues'), utils.Color.GREEN)}\n")


def _ask_yes_no(prompt: str) -> bool:
    """Ask a yes/no question."""
    try:
        choice = input(f"{prompt} (Y/n): ").strip().lower()
        return choice in ("", "y", "yes", "是")
    except (EOFError, KeyboardInterrupt):
        return False


def _do_rollback():
    """Execute rollback."""
    import os
    rollback_file = os.path.join(os.path.expanduser("~"), "netboost_rollback")
    if utils.IS_WIN:
        rollback_file += ".bat"
    else:
        rollback_file += ".sh"

    if not os.path.exists(rollback_file):
        print(f"  {utils.colored('未找到还原文件: ' + rollback_file, utils.Color.YELLOW)}")
        return

    print(f"  找到还原文件: {rollback_file}")
    if _ask_yes_no("  确定要还原所有 NetBoost 的改动吗？"):
        if utils.IS_WIN:
            output = utils.run_cmd(f'"{rollback_file}"', timeout=30)
        else:
            output = utils.run_cmd(f'bash "{rollback_file}"', timeout=30)
        print(output)
        print(f"  {utils.colored('还原完成', utils.Color.GREEN)}")
    else:
        print(f"  {utils.colored('已取消', utils.Color.GRAY)}")


def _do_speedtest_only():
    """Run speed test only."""
    _print_banner()
    print(f"{utils.bold('📊 速度测试')}\n")
    results = speedtest.run_speedtest(log_callback=_log)
    _print_speed_results(results)
    print()


def _export_report(report, scan_results, speed_before, speed_after, report_after, filepath):
    """Export report to markdown file."""
    lines = ["# NetBoost 网络诊断报告\n"]
    lines.append(f"评分: {report.score}/100 ({report.score_label})\n")

    lines.append("## 发现的问题\n")
    for issue in report.issues:
        lines.append(f"### [{issue.severity}] {issue.title}")
        lines.append(f"- 证据: {issue.evidence}")
        lines.append(f"- 影响: {issue.impact}")
        lines.append(f"- 风险: {issue.risk}")
        lines.append(f"- 建议: {issue.recommendation}\n")

    if speed_before:
        lines.append("## 测速结果 (Before)\n")
        lines.append(f"- 下载: {speed_before.get('download_mbps', 0)} Mbps")
        lines.append(f"- 上传: {speed_before.get('upload_mbps', 0)} Mbps")
        lines.append(f"- 延迟: {speed_before.get('latency_ms', -1)} ms\n")

    if speed_after:
        lines.append("## 测速结果 (After)\n")
        lines.append(f"- 下载: {speed_after.get('download_mbps', 0)} Mbps")
        lines.append(f"- 上传: {speed_after.get('upload_mbps', 0)} Mbps")
        lines.append(f"- 延迟: {speed_after.get('latency_ms', -1)} ms\n")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n  {utils.colored(f'报告已导出到: {filepath}', utils.Color.GREEN)}")
    except Exception as e:
        print(f"\n  {utils.colored(f'导出失败: {e}', utils.Color.RED)}")

