<div align="center">

# NetBoost

**Network Diagnostics & Optimization**

Scan . Speedtest . Diagnose . Optimize . Verify

[![Release](https://img.shields.io/github/v/release/Saint1010-arch/netboost?style=flat-square)](https://github.com/Saint1010-arch/netboost/releases)
[![License](https://img.shields.io/github/license/Saint1010-arch/netboost?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue?style=flat-square)](https://python.org)

</div>

---

## What It Does

Identifies why your network is slow and fixes it.

Scans DNS, Wi-Fi signal, MTU, proxy settings, packet loss, and latency. Runs a built-in speed test. Generates a scored diagnosis with actionable fixes. Applies optimizations with your confirmation. Re-tests and shows before/after comparison. Full rollback available.

## Quick Start

```bash
python netboost.py          # Opens web dashboard at localhost:7890
python netboost.py --cli    # CLI mode
```

**Windows:** Double-click `launcher.bat`
**macOS:** Double-click `other-platforms/NetBoost.command`
**Linux:** `bash other-platforms/NetBoost.sh`

## Features

- Zero dependencies - pure Python 3.7+
- Web dashboard with dark theme
- Built-in speed test (Cloudflare CDN)
- 100-point scoring system
- 6+ optimization types (DNS, TCP, MTU, Wi-Fi, proxy, cache)
- Before/after comparison
- One-click rollback
- Cross-platform

## License

MIT