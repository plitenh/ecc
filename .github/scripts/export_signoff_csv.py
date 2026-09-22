#!/usr/bin/env python3
"""CLI wrapper → chipcompiler.engine.signoff.csv.cli"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from chipcompiler.engine.signoff.csv.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
