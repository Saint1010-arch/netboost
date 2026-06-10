"""NetBoost - Built-in Speed Test Module.

Zero-dependency speed test using public CDN endpoints.
"""
import time
import threading
import urllib.request
import urllib.error
import ssl
import io
import os

from netboost import utils


# ---------- Speed test servers ----------

DOWNLOAD_URLS = [
    # Cloudflare speed test - various sizes
    ("Cloudflare", "https://speed.cloudflare.com/__down?bytes=25000000"),
    # Cloudflare 10MB
    ("Cloudflare-10M", "https://speed.cloudflare.com/__down?bytes=10000000"),
]

UPLOAD_URL = "https://speed.cloudflare.com/__up"

# Create SSL context that works everywhere
def _ssl_ctx():
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        ctx = ssl._create_unverified_context()
    return ctx


# ---------- Download speed test ----------

def test_download(duration: float = 10.0, progress_callback=None) -> dict:
    """Test download speed. Returns dict with mbps, bytes, duration."""
    result = {"mbps": 0, "bytes_total": 0, "duration": 0, "error": ""}

    total_bytes = 0
    start_time = time.time()

    try:
        ctx = _ssl_ctx()
        # Try each URL until one works
        for name, url in DOWNLOAD_URLS:
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "NetBoost/1.0")

                elapsed = 0
                with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                    chunk_size = 65536
                    while elapsed < duration:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        elapsed = time.time() - start_time

                        if progress_callback:
                            speed_mbps = (total_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
                            progress_callback(elapsed / duration, speed_mbps)

                if total_bytes > 0:
                    break  # success, don't try next URL

            except Exception as e:
                continue

        elapsed = time.time() - start_time
        if total_bytes > 0 and elapsed > 0:
            result["mbps"] = round((total_bytes * 8) / (elapsed * 1_000_000), 2)
            result["bytes_total"] = total_bytes
            result["duration"] = round(elapsed, 2)
        else:
            result["error"] = "所有测速节点均不可达"

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------- Upload speed test ----------

def test_upload(duration: float = 8.0, progress_callback=None) -> dict:
    """Test upload speed. Returns dict with mbps, bytes, duration."""
    result = {"mbps": 0, "bytes_total": 0, "duration": 0, "error": ""}

    # Generate random data block
    block = os.urandom(131072)  # 128KB blocks
    total_bytes = 0
    start_time = time.time()

    try:
        ctx = _ssl_ctx()
        elapsed = 0

        while elapsed < duration:
            try:
                data = block * 4  # 512KB per request
                req = urllib.request.Request(
                    UPLOAD_URL,
                    data=data,
                    method="POST",
                )
                req.add_header("User-Agent", "NetBoost/1.0")
                req.add_header("Content-Type", "application/octet-stream")

                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    resp.read()

                total_bytes += len(data)
                elapsed = time.time() - start_time

                if progress_callback:
                    speed_mbps = (total_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
                    progress_callback(elapsed / duration, speed_mbps)

            except Exception:
                elapsed = time.time() - start_time
                continue

        elapsed = time.time() - start_time
        if total_bytes > 0 and elapsed > 0:
            result["mbps"] = round((total_bytes * 8) / (elapsed * 1_000_000), 2)
            result["bytes_total"] = total_bytes
            result["duration"] = round(elapsed, 2)
        else:
            result["error"] = "上传测试失败"

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------- Full speed test ----------

def run_speedtest(log_callback=None, progress_callback=None) -> dict:
    """Run full speed test: download + upload + latency + jitter + packet loss.

    progress_callback(phase, fraction, value):
        phase: "download" | "upload" | "latency"
        fraction: 0.0 ~ 1.0
        value: current speed/latency
    """

    def log(msg):
        if log_callback:
            log_callback(msg)

    def prog(phase):
        def inner(frac, val):
            if progress_callback:
                progress_callback(phase, frac, val)
        return inner

    results = {
        "download_mbps": 0,
        "upload_mbps": 0,
        "latency_ms": -1,
        "jitter_ms": -1,
        "packet_loss_pct": -1,
        "download_detail": {},
        "upload_detail": {},
        "latency_detail": {},
        "error": "",
    }

    # 1. Latency test first (it's quick)
    log(utils.t("speedtest_running") + " - Ping...")
    ping_result = utils.ping("223.5.5.5", count=15)
    results["latency_ms"] = ping_result["avg_ms"]
    results["jitter_ms"] = ping_result["jitter_ms"]
    results["packet_loss_pct"] = ping_result["loss_pct"]
    results["latency_detail"] = ping_result

    if progress_callback:
        progress_callback("latency", 1.0, ping_result["avg_ms"])

    # 2. Download test
    log(utils.t("speedtest_download"))
    dl = test_download(duration=10, progress_callback=prog("download"))
    results["download_mbps"] = dl["mbps"]
    results["download_detail"] = dl
    if dl.get("error"):
        results["error"] = dl["error"]

    # 3. Upload test
    log(utils.t("speedtest_upload"))
    ul = test_upload(duration=8, progress_callback=prog("upload"))
    results["upload_mbps"] = ul["mbps"]
    results["upload_detail"] = ul
    if ul.get("error") and not results["error"]:
        results["error"] = ul["error"]

    log(utils.t("speedtest_done"))
    return results

