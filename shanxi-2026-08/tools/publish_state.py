#!/usr/bin/env python3
"""Print GitHub Actions outputs for the trip publication state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: 缺少 PyYAML；请先安装 requirements.lock", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    path = args.project_dir.resolve() / "trip.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    enabled = data.get("publish") is True and data.get("stage") in {"approved", "published"}
    print(f"enabled={'true' if enabled else 'false'}")
    print(f"stage={data.get('stage', 'unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
