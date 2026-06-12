#!/usr/bin/env python3
"""
NetBoost - Network diagnostics, speed test, and optimization.
https://github.com/Saint1010-arch/netboost
"""
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(script_dir, "netboost")):
    sys.path.insert(0, script_dir)

from netboost.__main__ import main

if __name__ == "__main__":
    main()