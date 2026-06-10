"""NetBoost - Diagnosis Engine.

Analyzes scan + speedtest results, generates score and issue list.
"""
from netboost import utils


class Issue:
    """Represents a detected network issue."""
    def __init__(self, severity, title, evidence, impact, risk, recommendation, category):
        self.severity = severity  # "critical" | "warning" | "info"
        self.title = title
        self.evidence = evidence
        self.impact = impact
        self.risk = risk  # "low" | "medium" | "high"
        self.recommendation = recommendation
        self.category = category  # "dns" | "mtu" | "wifi" | "vpn" | "packet_loss" | "latency" | "proxy"
        self.optimizable = risk != "high"  # don't auto-optimize high risk

    def to_dict(self):
        return {
            "severity": self.severity,
            "title": self.title,
            "evidence": self.evidence,
            "impact": self.impact,
            "risk": self.risk,
            "recommendation": self.recommendation,
            "category": self.category,
            "optimizable": self.optimizable,
        }


class DiagnosisReport:
    """Full diagnosis report with score and issues."""
    def __init__(self):
        self.score = 100
        self.score_breakdown = {}
        self.score_label = ""
        self.issues = []
        self.summary = ""
        self.metrics = {}

    def to_dict(self):
        return {
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "score_label": self.score_label,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "metrics": self.metrics,
        }


def diagnose(scan_results: dict, speed_results: dict = None) -> DiagnosisReport:
    """Generate diagnosis report from scan and speed test results."""
    report = DiagnosisReport()

    # Collect metrics
    metrics = {}

    # DNS metrics
    dns_timing = scan_results.get("dns_timing", {})
    metrics["dns_avg_ms"] = dns_timing.get("system_avg", -1)
    best_dns = dns_timing.get("best_public", {})
    metrics["best_dns_name"] = best_dns.get("name", "")
    metrics["best_dns_ms"] = best_dns.get("avg_ms", -1)

    # Wi-Fi metrics
    wifi = scan_results.get("wifi", {})
    metrics["wifi_connected"] = wifi.get("connected", False)
    metrics["wifi_signal_pct"] = wifi.get("signal_pct", -1)
    metrics["wifi_signal_dbm"] = wifi.get("signal_dbm", -1)
    metrics["wifi_ssid"] = wifi.get("ssid", "")
    metrics["wifi_channel"] = wifi.get("channel", "")

    # Gateway ping
    gw_ping = scan_results.get("ping_gateway", {})
    metrics["gateway_latency_ms"] = gw_ping.get("avg_ms", -1)
    metrics["gateway_loss_pct"] = gw_ping.get("loss_pct", -1)

    # Public ping
    pub_ping = scan_results.get("ping_public", {})
    metrics["public_latency_ms"] = pub_ping.get("avg_ms", -1)
    metrics["public_loss_pct"] = pub_ping.get("loss_pct", -1)
    metrics["public_jitter_ms"] = pub_ping.get("jitter_ms", -1)

    # MTU
    mtu = scan_results.get("mtu", {})
    metrics["mtu_current"] = mtu.get("current", 1500)
    metrics["mtu_optimal"] = mtu.get("optimal", 1500)
    metrics["mtu_needs_change"] = mtu.get("needs_change", False)

    # VPN
    vpn = scan_results.get("vpn", {})
    metrics["vpn_active"] = vpn.get("active", False)
    metrics["vpn_type"] = vpn.get("type", "")

    # Proxy
    proxy = scan_results.get("proxy", {})
    metrics["proxy_enabled"] = proxy.get("enabled", False)

    # Speed test metrics (if available)
    if speed_results:
        metrics["download_mbps"] = speed_results.get("download_mbps", 0)
        metrics["upload_mbps"] = speed_results.get("upload_mbps", 0)
        metrics["latency_ms"] = speed_results.get("latency_ms", -1)
        metrics["jitter_ms"] = speed_results.get("jitter_ms", -1)
        metrics["packet_loss_pct"] = speed_results.get("packet_loss_pct", -1)
    else:
        metrics["download_mbps"] = 0
        metrics["upload_mbps"] = 0
        metrics["latency_ms"] = pub_ping.get("avg_ms", -1)
        metrics["jitter_ms"] = pub_ping.get("jitter_ms", -1)
        metrics["packet_loss_pct"] = pub_ping.get("loss_pct", -1)

    report.metrics = metrics

    # ---------- Score calculation ----------
    scores = {}

    # DNS score (20 points)
    dns_ms = metrics["dns_avg_ms"]
    if dns_ms < 0:
        scores["dns"] = 15  # unknown, give average
    elif dns_ms <= 30:
        scores["dns"] = 20
    elif dns_ms <= 50:
        scores["dns"] = 18
    elif dns_ms <= 100:
        scores["dns"] = 14
    elif dns_ms <= 200:
        scores["dns"] = 10
    elif dns_ms <= 500:
        scores["dns"] = 5
    else:
        scores["dns"] = 2

    # Latency score (20 points)
    lat_ms = metrics["latency_ms"]
    if lat_ms < 0:
        scores["latency"] = 15
    elif lat_ms <= 10:
        scores["latency"] = 20
    elif lat_ms <= 20:
        scores["latency"] = 18
    elif lat_ms <= 50:
        scores["latency"] = 14
    elif lat_ms <= 100:
        scores["latency"] = 10
    else:
        scores["latency"] = 5

    # Download score (25 points)
    dl = metrics["download_mbps"]
    if dl <= 0:
        scores["download"] = 15  # no test, give average
    elif dl >= 100:
        scores["download"] = 25
    elif dl >= 50:
        scores["download"] = 22
    elif dl >= 30:
        scores["download"] = 18
    elif dl >= 10:
        scores["download"] = 12
    elif dl >= 5:
        scores["download"] = 8
    else:
        scores["download"] = 4

    # Upload score (15 points)
    ul = metrics["upload_mbps"]
    if ul <= 0:
        scores["upload"] = 10
    elif ul >= 50:
        scores["upload"] = 15
    elif ul >= 20:
        scores["upload"] = 13
    elif ul >= 10:
        scores["upload"] = 11
    elif ul >= 5:
        scores["upload"] = 8
    else:
        scores["upload"] = 4

    # Packet loss score (10 points)
    loss = metrics["packet_loss_pct"]
    if loss < 0:
        scores["packet_loss"] = 8
    elif loss == 0:
        scores["packet_loss"] = 10
    elif loss <= 1:
        scores["packet_loss"] = 7
    elif loss <= 3:
        scores["packet_loss"] = 4
    else:
        scores["packet_loss"] = 1

    # Wi-Fi score (10 points)
    wifi_sig = metrics["wifi_signal_pct"]
    if not metrics["wifi_connected"]:
        scores["wifi"] = 8  # might be wired, that's fine
    elif wifi_sig < 0:
        scores["wifi"] = 7
    elif wifi_sig >= 80:
        scores["wifi"] = 10
    elif wifi_sig >= 60:
        scores["wifi"] = 8
    elif wifi_sig >= 40:
        scores["wifi"] = 5
    else:
        scores["wifi"] = 2

    report.score_breakdown = scores
    report.score = sum(scores.values())
    report.score = max(0, min(100, report.score))

    # Score label
    if report.score >= 90:
        report.score_label = utils.t("score_excellent")
    elif report.score >= 70:
        report.score_label = utils.t("score_good")
    elif report.score >= 50:
        report.score_label = utils.t("score_fair")
    else:
        report.score_label = utils.t("score_poor")

    # ---------- Issue detection ----------

    # DNS issues
    if dns_ms > 50:
        best_name = metrics.get("best_dns_name", "")
        best_ms = metrics.get("best_dns_ms", -1)
        issue = Issue(
            severity="critical" if dns_ms > 200 else "warning",
            title="DNS 响应慢",
            evidence=f"系统 DNS 平均响应 {dns_ms}ms" + (f"，而 {best_name} 仅需 {best_ms}ms" if best_ms > 0 else ""),
            impact=f"每次打开网页额外等待约 {int(dns_ms - 30)}ms",
            risk="low",
            recommendation=f"建议切换为 {best_name}" if best_name else "建议切换为公共 DNS",
            category="dns",
        )
        report.issues.append(issue)

    # MTU issues
    if metrics["mtu_needs_change"]:
        diff = metrics["mtu_current"] - metrics["mtu_optimal"]
        issue = Issue(
            severity="warning",
            title="MTU 设置可能不是最优",
            evidence=f"当前 MTU={metrics['mtu_current']}，测试最佳值为 {metrics['mtu_optimal']}",
            impact=f"当前设置可能导致数据包分片，增加约 {min(5, diff // 10)}% 的延迟",
            risk="low",
            recommendation=f"建议调整 MTU 为 {metrics['mtu_optimal']}",
            category="mtu",
        )
        report.issues.append(issue)

    # Wi-Fi signal issues
    if metrics["wifi_connected"] and metrics["wifi_signal_pct"] >= 0:
        if metrics["wifi_signal_pct"] < 40:
            issue = Issue(
                severity="critical",
                title="Wi-Fi 信号很弱",
                evidence=f"信号强度 {metrics['wifi_signal_pct']}% ({metrics['wifi_signal_dbm']} dBm)",
                impact="可能导致频繁断连、高延迟和低速度",
                risk="low",
                recommendation="建议靠近路由器或检查是否有遮挡物",
                category="wifi",
            )
            issue.optimizable = False  # can't fix via software
            report.issues.append(issue)
        elif metrics["wifi_signal_pct"] < 60:
            issue = Issue(
                severity="warning",
                title="Wi-Fi 信号较弱",
                evidence=f"信号强度 {metrics['wifi_signal_pct']}% ({metrics['wifi_signal_dbm']} dBm)",
                impact="可能影响速度稳定性",
                risk="low",
                recommendation="建议检查路由器位置或减少遮挡物",
                category="wifi",
            )
            issue.optimizable = False
            report.issues.append(issue)

    # Packet loss
    if metrics["packet_loss_pct"] > 0:
        issue = Issue(
            severity="critical" if metrics["packet_loss_pct"] > 3 else "warning",
            title="检测到丢包",
            evidence=f"丢包率 {metrics['packet_loss_pct']}%",
            impact="导致网页加载慢、视频卡顿、游戏延迟高",
            risk="medium" if metrics["packet_loss_pct"] > 5 else "low",
            recommendation="建议检查网线/Wi-Fi 连接质量，或联系运营商",
            category="packet_loss",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # High latency
    if metrics["latency_ms"] > 30:
        issue = Issue(
            severity="warning" if metrics["latency_ms"] < 100 else "critical",
            title="网络延迟较高",
            evidence=f"平均延迟 {metrics['latency_ms']}ms",
            impact="网页响应慢、视频通话卡顿",
            risk="low",
            recommendation="可能与 VPN 或路由有关" if metrics["vpn_active"] else "建议检查网络链路",
            category="latency",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # VPN notice
    if metrics["vpn_active"]:
        # Compare gateway vs public latency to estimate VPN overhead
        gw_lat = metrics.get("gateway_latency_ms", -1)
        pub_lat = metrics.get("public_latency_ms", -1)
        vpn_overhead = ""
        if gw_lat > 0 and pub_lat > 0:
            overhead = pub_lat - gw_lat
            vpn_overhead = f"，估计 VPN 增加约 {int(overhead)}ms 延迟" if overhead > 5 else ""

        issue = Issue(
            severity="info",
            title="检测到 VPN 活跃",
            evidence=f"类型: {metrics['vpn_type']}" + vpn_overhead,
            impact="VPN 加密会增加延迟，属正常情况" if not vpn_overhead else f"VPN 对延迟有影响{vpn_overhead}",
            risk="high",  # don't touch VPN
            recommendation="VPN 保持不动；如需极致延迟可临时断开",
            category="vpn",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # Proxy notice
    if metrics["proxy_enabled"]:
        issue = Issue(
            severity="info",
            title="检测到代理设置",
            evidence=f"HTTP 代理: {scan_results.get('proxy', {}).get('http', '未知')}",
            impact="代理可能影响部分网站的访问速度",
            risk="medium",
            recommendation="如非必需，可考虑关闭代理",
            category="proxy",
        )
        report.issues.append(issue)

    # High jitter
    if metrics["jitter_ms"] > 10:
        issue = Issue(
            severity="warning",
            title="网络抖动较大",
            evidence=f"抖动 {metrics['jitter_ms']}ms",
            impact="视频通话和游戏体验不稳定",
            risk="low",
            recommendation="可能与 Wi-Fi 干扰或带宽争用有关",
            category="latency",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # Download speed issues
    if metrics["download_mbps"] > 0 and metrics["download_mbps"] < 10:
        issue = Issue(
            severity="critical" if metrics["download_mbps"] < 5 else "warning",
            title="下载速度偏低",
            evidence="下载速度仅 " + str(metrics["download_mbps"]) + " Mbps",
            impact="网页加载慢、视频缓冲、大文件下载耗时长",
            risk="medium",
            recommendation="建议检查是否有后台程序占用带宽，或联系运营商确认签约带宽",
            category="download",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # Upload speed issues
    if metrics["upload_mbps"] > 0 and metrics["upload_mbps"] < 3:
        issue = Issue(
            severity="warning",
            title="上传速度偏低",
            evidence="上传速度仅 " + str(metrics["upload_mbps"]) + " Mbps",
            impact="视频通话画质差、文件上传慢",
            risk="low",
            recommendation="上传速度通常由运营商决定，可联系运营商了解套餐详情",
            category="upload",
        )
        issue.optimizable = False
        report.issues.append(issue)

    # Summary
    optimizable = [i for i in report.issues if i.optimizable]
    if not report.issues:
        report.summary = utils.t("no_issues")
    elif optimizable:
        report.summary = utils.t("issues_found", len(report.issues)) + " | " + utils.t("recommend_optimize")
    else:
        report.summary = utils.t("issues_found", len(report.issues))

    return report



