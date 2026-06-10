"""NetBoost - Network Scanner Module.

Read-only network environment scanning. Does NOT modify any settings.
"""
import re
import time
import socket

from netboost import utils


def scan_all(log_callback=None):
    """Run all scans and return a dict of results."""

    def log(msg):
        if log_callback:
            log_callback(msg)

    results = {}

    log("正在检测网络接口...")
    results["interfaces"] = scan_interfaces()

    log("正在检测默认网关...")
    results["gateway"] = scan_gateway()

    log("正在检测 DNS 配置...")
    results["dns"] = scan_dns()

    log("正在测试 DNS 响应速度...")
    results["dns_timing"] = scan_dns_timing()

    log("正在检测 MTU...")
    results["mtu"] = scan_mtu(results.get("gateway", {}).get("ip", ""))

    log("正在检测 Wi-Fi 状态...")
    results["wifi"] = scan_wifi()

    log("正在检测 VPN...")
    results["vpn"] = scan_vpn()

    log("正在检测代理设置...")
    results["proxy"] = scan_proxy()

    log("正在测试网关延迟和丢包...")
    gw_ip = results.get("gateway", {}).get("ip", "")
    if gw_ip:
        results["ping_gateway"] = utils.ping(gw_ip, count=10)
    else:
        results["ping_gateway"] = {"avg_ms": -1, "loss_pct": -1, "jitter_ms": -1}

    log("正在测试公网延迟和丢包...")
    results["ping_public"] = utils.ping("223.5.5.5", count=10)

    log("扫描完成！")
    return results


# ---------- Interface scan ----------

def scan_interfaces() -> list:
    """Get network interface info."""
    interfaces = []
    if utils.IS_WIN:
        output = utils.run_cmd("ipconfig /all")
        blocks = re.split(r"\r?\n(?=\S)", output)
        for block in blocks:
            if not block.strip():
                continue
            iface = {}
            name_match = re.match(r"(.+?):", block)
            if name_match:
                iface["name"] = name_match.group(1).strip()

            for key, pattern in [
                ("description", r"(?:描述|Description)[.\s]*:\s*(.+)"),
                ("mac", r"(?:物理地址|Physical Address)[.\s]*:\s*(.+)"),
                ("ipv4", r"(?:IPv4 地址|IPv4 Address)[.\s]*:\s*([\d.]+)"),
                ("subnet", r"(?:子网掩码|Subnet Mask)[.\s]*:\s*([\d.]+)"),
                ("gateway", r"(?:默认网关|Default Gateway)[.\s]*:\s*([\d.]+)"),
                ("dns", r"(?:DNS 服务器|DNS Servers)[.\s]*:\s*([\d.]+)"),
                ("dhcp", r"(?:DHCP 已启用|DHCP Enabled)[.\s]*:\s*(.+)"),
            ]:
                m = re.search(pattern, block, re.IGNORECASE)
                if m:
                    iface[key] = m.group(1).strip()

            if iface.get("ipv4") or iface.get("description"):
                interfaces.append(iface)
    else:
        output = utils.run_cmd("ip addr" if utils.IS_LINUX else "ifconfig")
        current = {}
        for line in output.splitlines():
            if utils.IS_LINUX:
                m = re.match(r"\d+:\s+(\S+):", line)
                if m:
                    if current.get("name"):
                        interfaces.append(current)
                    current = {"name": m.group(1)}
                ip_m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                if ip_m:
                    current["ipv4"] = ip_m.group(1)
            else:  # macOS
                m = re.match(r"(\S+):\s+flags", line)
                if m:
                    if current.get("name"):
                        interfaces.append(current)
                    current = {"name": m.group(1)}
                ip_m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                if ip_m:
                    current["ipv4"] = ip_m.group(1)
        if current.get("name"):
            interfaces.append(current)

    return interfaces


# ---------- Gateway ----------

def scan_gateway() -> dict:
    """Get default gateway info."""
    gw = {"ip": "", "interface": ""}
    if utils.IS_WIN:
        output = utils.run_cmd("route print 0.0.0.0")
        # Look for default route: 0.0.0.0 ... gateway ... metric
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                gw["ip"] = parts[2]
                break
        if not gw["ip"]:
            # Try ipconfig
            output = utils.run_cmd("ipconfig")
            m = re.search(r"(?:默认网关|Default Gateway)[.\s]*:\s*([\d.]+)", output, re.IGNORECASE)
            if m:
                gw["ip"] = m.group(1)
    elif utils.IS_MAC:
        output = utils.run_cmd("netstat -rn")
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "default":
                gw["ip"] = parts[1]
                if len(parts) >= 4:
                    gw["interface"] = parts[3] if len(parts) > 3 else ""
                break
    else:
        output = utils.run_cmd("ip route show default")
        m = re.search(r"default via (\S+)", output)
        if m:
            gw["ip"] = m.group(1)
        m2 = re.search(r"dev (\S+)", output)
        if m2:
            gw["interface"] = m2.group(1)
    return gw


# ---------- DNS ----------

def scan_dns() -> dict:
    """Get DNS configuration."""
    dns = {"servers": [], "search_domains": []}
    if utils.IS_WIN:
        output = utils.run_cmd("ipconfig /all")
        # Collect all DNS servers
        for m in re.finditer(r"(?:DNS 服务器|DNS Servers)[.\s]*:\s*([\d.]+(?:\.\d+)*)", output, re.IGNORECASE):
            server = m.group(1).strip()
            if server and server not in dns["servers"]:
                dns["servers"].append(server)
        # Also find secondary DNS servers (indented lines after primary)
        in_dns = False
        for line in output.splitlines():
            if re.search(r"(?:DNS 服务器|DNS Servers)", line, re.IGNORECASE):
                in_dns = True
                m = re.search(r":\s*([\d.]+)", line)
                if m and m.group(1) not in dns["servers"]:
                    dns["servers"].append(m.group(1))
            elif in_dns:
                m = re.match(r"\s+([\d.]+(?:\.\d+)*)\s*$", line)
                if m:
                    if m.group(1) not in dns["servers"]:
                        dns["servers"].append(m.group(1))
                else:
                    in_dns = False
    elif utils.IS_MAC:
        output = utils.run_cmd("scutil --dns")
        for m in re.finditer(r"nameserver\[\d+\]\s*:\s*(\S+)", output):
            server = m.group(1)
            if server not in dns["servers"]:
                dns["servers"].append(server)
        for m in re.finditer(r"search domain\[\d+\]\s*:\s*(\S+)", output):
            dns["search_domains"].append(m.group(1))
    else:
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] not in dns["servers"]:
                            dns["servers"].append(parts[1])
                    elif line.startswith("search"):
                        dns["search_domains"] = line.split()[1:]
        except Exception:
            pass
    return dns


# ---------- DNS Timing ----------

DNS_TEST_TARGETS = ["www.baidu.com", "www.google.com", "www.cloudflare.com"]
DNS_PUBLIC_SERVERS = {
    "阿里DNS (223.5.5.5)": "223.5.5.5",
    "腾讯DNS (119.29.29.29)": "119.29.29.29",
    "114DNS (114.114.114.114)": "114.114.114.114",
    "Cloudflare (1.1.1.1)": "1.1.1.1",
    "Google (8.8.8.8)": "8.8.8.8",
}


def scan_dns_timing() -> dict:
    """Test DNS resolution time with different servers."""
    result = {"system": {}, "public": {}}

    # Test system DNS (no specific server)
    for host in DNS_TEST_TARGETS:
        t = utils.dns_resolve_time(host)
        result["system"][host] = t

    # Test public DNS servers
    for name, server in DNS_PUBLIC_SERVERS.items():
        times = []
        for host in DNS_TEST_TARGETS[:2]:  # only test 2 hosts per public DNS to save time
            t = utils.dns_resolve_time(host, dns_server=server)
            if t >= 0:
                times.append(t)
        result["public"][name] = round(sum(times) / len(times), 1) if times else -1

    # Calculate system average
    sys_times = [v for v in result["system"].values() if v >= 0]
    result["system_avg"] = round(sum(sys_times) / len(sys_times), 1) if sys_times else -1

    # Find best public DNS
    valid = {k: v for k, v in result["public"].items() if v >= 0}
    if valid:
        best = min(valid, key=valid.get)
        result["best_public"] = {"name": best, "avg_ms": valid[best]}
    else:
        result["best_public"] = {"name": "", "avg_ms": -1}

    return result


# ---------- MTU ----------

def scan_mtu(gateway: str = "") -> dict:
    """Detect optimal MTU by binary search."""
    target = gateway or "223.5.5.5"
    mtu_info = {"current": 1500, "optimal": 1500, "needs_change": False}

    # Detect current MTU
    if utils.IS_WIN:
        output = utils.run_cmd("netsh interface ipv4 show subinterfaces")
        # Find the interface with the largest MTU (likely the active one)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                try:
                    mtu_val = int(parts[0])
                    if mtu_val > 0:
                        mtu_info["current"] = mtu_val
                except ValueError:
                    pass
    elif utils.IS_MAC:
        output = utils.run_cmd("ifconfig en0")
        m = re.search(r"mtu (\d+)", output)
        if m:
            mtu_info["current"] = int(m.group(1))
    else:
        output = utils.run_cmd("ip link show")
        m = re.search(r"mtu (\d+)", output)
        if m:
            mtu_info["current"] = int(m.group(1))

    # Binary search for optimal MTU
    low, high = 1300, mtu_info["current"]
    best = low

    for _ in range(10):  # max 10 iterations
        if low > high:
            break
        mid = (low + high) // 2
        payload = mid - 28  # IP header (20) + ICMP header (8)
        if payload <= 0:
            break

        if utils.IS_WIN:
            cmd = f"ping -f -l {payload} -n 1 -w 2000 {target}"
        elif utils.IS_MAC:
            cmd = f"ping -D -s {payload} -c 1 -W 2 {target}"
        else:
            cmd = f"ping -M do -s {payload} -c 1 -W 2 {target}"

        output = utils.run_cmd(cmd, timeout=5)

        # Check if ping succeeded (no fragmentation needed)
        if utils.IS_WIN:
            needs_frag = "需要拆分" in output or "fragmented" in output.lower() or "DF" in output
            success = "TTL=" in output or "ttl=" in output.lower()
        else:
            needs_frag = "frag needed" in output.lower() or "message too long" in output.lower()
            success = "1 received" in output or "1 packets received" in output or " 0% packet loss" in output

        if success and not needs_frag:
            best = mid
            low = mid + 1
        else:
            high = mid - 1

    mtu_info["optimal"] = best
    mtu_info["needs_change"] = best < mtu_info["current"] - 10  # only flag if significant difference

    return mtu_info


# ---------- Wi-Fi ----------

def scan_wifi() -> dict:
    """Get Wi-Fi signal strength and channel info."""
    wifi = {
        "connected": False,
        "ssid": "",
        "signal_pct": -1,
        "signal_dbm": -1,
        "channel": "",
        "speed": "",
        "band": "",
        "noise_dbm": -1,
        "snr": -1,
    }

    if utils.IS_WIN:
        output = utils.run_cmd("netsh wlan show interfaces")
        if not output.strip() or "没有" in output or "not" in output.lower():
            return wifi

        wifi["connected"] = "已连接" in output or "connected" in output.lower()

        patterns = {
            "ssid": r"SSID\s*:\s*(.+)",
            "signal_pct": r"(?:信号|Signal)\s*:\s*(\d+)\s*%",
            "channel": r"(?:频道|通道|Channel)\s*:\s*(\S+)",
            "speed": r"(?:接收速率|Receive rate).*?:\s*(\S+)",
            "band": r"(?:无线电类型|Radio type)\s*:\s*(.+)",
        }
        # Also check for RSSI
        rssi_m = re.search(r"Rssi\s*:\s*(-?\d+)", output, re.IGNORECASE)
        if rssi_m:
            wifi["signal_dbm"] = int(rssi_m.group(1))
        for key, pat in patterns.items():
            m = re.search(pat, output, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if key == "signal_pct":
                    wifi["signal_pct"] = int(val)
                    # Approximate dBm from percentage
                    wifi["signal_dbm"] = int(-100 + (int(val) / 2))
                else:
                    wifi[key] = val

    elif utils.IS_MAC:
        # Try system_profiler or airport
        output = utils.run_cmd(
            "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I"
        )
        if output.strip():
            for key, pat in [
                ("ssid", r"\s+SSID:\s*(.+)"),
                ("signal_dbm", r"\s+agrCtlRSSI:\s*(-?\d+)"),
                ("noise_dbm", r"\s+agrCtlNoise:\s*(-?\d+)"),
                ("channel", r"\s+channel:\s*(.+)"),
            ]:
                m = re.search(pat, output)
                if m:
                    val = m.group(1).strip()
                    if key in ("signal_dbm", "noise_dbm"):
                        wifi[key] = int(val)
                    else:
                        wifi[key] = val

            wifi["connected"] = bool(wifi["ssid"])
            if wifi["signal_dbm"] != -1:
                wifi["signal_pct"] = max(0, min(100, 2 * (wifi["signal_dbm"] + 100)))
            if wifi["signal_dbm"] != -1 and wifi["noise_dbm"] != -1:
                wifi["snr"] = wifi["signal_dbm"] - wifi["noise_dbm"]
    else:
        output = utils.run_cmd("iwconfig 2>/dev/null || iw dev")
        m = re.search(r"ESSID:\"(.+?)\"", output)
        if m:
            wifi["ssid"] = m.group(1)
            wifi["connected"] = True
        m = re.search(r"Signal level[=:](-?\d+)", output)
        if m:
            wifi["signal_dbm"] = int(m.group(1))
            wifi["signal_pct"] = max(0, min(100, 2 * (int(m.group(1)) + 100)))
        m = re.search(r"Bit Rate[=:](\S+)", output)
        if m:
            wifi["speed"] = m.group(1)

    return wifi


# ---------- VPN ----------

def scan_vpn() -> dict:
    """Detect VPN connections."""
    vpn = {"active": False, "type": "", "interface": "", "details": ""}

    if utils.IS_WIN:
        # Check for VPN adapters
        output = utils.run_cmd("ipconfig /all")
        vpn_keywords = ["VPN", "TAP", "TUN", "WireGuard", "OpenVPN", "Cisco", "Fortinet",
                        "GlobalProtect", "Pulse", "虚拟", "PPP"]
        for keyword in vpn_keywords:
            if keyword.lower() in output.lower():
                vpn["active"] = True
                vpn["type"] = keyword
                break

        # Also check route table for VPN routes
        routes = utils.run_cmd("route print")
        # VPN often adds a 0.0.0.0/0 or 0.0.0.0/128 route with lower metric
        route_lines = routes.splitlines()
        default_routes = [l for l in route_lines if "0.0.0.0" in l and l.strip().startswith("0.0.0.0")]
        if len(default_routes) > 1:
            vpn["active"] = True
            vpn["details"] = f"检测到 {len(default_routes)} 条默认路由（可能存在 VPN 分流）"

        # Check for known VPN processes
        try:
            output = utils.run_cmd("tasklist /FO CSV /NH")
            vpn_procs = ["openvpn", "wireguard", "vpnclient", "cisco", "fortitray",
                         "pangpa", "globalprotect", "v2ray", "clash", "trojan", "ssr"]
            for proc in vpn_procs:
                if proc in output.lower():
                    vpn["active"] = True
                    vpn["type"] = proc
                    break
        except Exception:
            pass

    elif utils.IS_MAC:
        output = utils.run_cmd("ifconfig")
        for iface in ["utun", "tun", "tap", "ppp", "ipsec"]:
            if iface in output:
                vpn["active"] = True
                vpn["interface"] = iface
                break
        # Check scutil
        proxy = utils.run_cmd("scutil --proxy")
        if "SOCKS" in proxy or "Proxy" in proxy:
            vpn["details"] = "检测到代理配置"

    else:
        output = utils.run_cmd("ip link show")
        for iface in ["tun", "tap", "wg", "ppp"]:
            if iface in output:
                vpn["active"] = True
                vpn["interface"] = iface
                break

    return vpn


# ---------- Proxy ----------

def scan_proxy() -> dict:
    """Detect proxy settings."""
    proxy = {"enabled": False, "http": "", "https": "", "socks": "", "pac": ""}

    # Check environment variables
    for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"]:
        val = os.environ.get(var, "")
        if val:
            proxy["enabled"] = True
            if "http" in var.lower():
                proxy["http"] = val
            else:
                proxy["https"] = val

    socks = os.environ.get("ALL_PROXY", "") or os.environ.get("all_proxy", "")
    if socks:
        proxy["enabled"] = True
        proxy["socks"] = socks

    if utils.IS_WIN:
        # Check registry
        try:
            output = utils.run_cmd(
                'reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable'
            )
            if "0x1" in output:
                proxy["enabled"] = True
                output2 = utils.run_cmd(
                    'reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyServer'
                )
                m = re.search(r"ProxyServer\s+REG_SZ\s+(\S+)", output2)
                if m:
                    proxy["http"] = m.group(1)
        except Exception:
            pass

    return proxy


import os




