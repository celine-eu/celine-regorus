#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path even when invoked as /app/main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from celine_regorus_builder.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
