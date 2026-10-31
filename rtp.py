#!/usr/bin/env python3
"""Entry point: ``python rtp.py register.csv --treatments treatments.csv --out output``.

Thin wrapper around the ``rtp`` package so the tool works from a plain checkout
without installing anything (openpyxl only, and only for the .xlsx).
"""
from __future__ import annotations

import sys

from rtp.cli import main

if __name__ == "__main__":
    sys.exit(main())
