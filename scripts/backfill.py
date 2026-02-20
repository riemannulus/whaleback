#!/usr/bin/env python
"""Standalone backfill script for historical data collection.

Usage:
    python -m scripts.backfill --start 20200101 --end 20261231
    python -m scripts.backfill --start 20200101 --type ohlcv --type fundamentals
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from whaleback.__main__ import cli

if __name__ == "__main__":
    cli(["backfill"] + sys.argv[1:])
