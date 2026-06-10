#!/usr/bin/env python3
"""
NetBoost - One-click network diagnosis, speed test, and optimization.
https://github.com/yourname/netboost

Usage:
    python netboost.py          # Launch GUI (default)
    python netboost.py --cli    # CLI mode
    python netboost.py --help   # See all options

Zero dependencies. Cross-platform. Python 3.7+.
"""
import sys
import os

# Ensure we can import the package
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(script_dir, "netboost")):
    sys.path.insert(0, script_dir)

from netboost.__main__ import main

if __name__ == "__main__":
    main()
