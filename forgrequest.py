#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility launcher for the src/forgrequest package."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
src_path = str(SRC)
sys.path[:] = [entry for entry in sys.path if entry != src_path]
sys.path.insert(0, src_path)

from forgrequest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
