#!/usr/bin/env python3
from __future__ import annotations

import csv
import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "content-rights" / "assets-register.csv"
ASSET_DIRS = [ROOT / "frontend" / "public", ROOT / "backend" / "media"]
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp3", ".ogg"}


def _tracked_assets() -> list[str]:
    assets: list[str] = []
    for directory in ASSET_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES:
                assets.append(path.relative_to(ROOT).as_posix())
    return sorted(assets)


def _registered_patterns() -> list[str]:
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            row["path_or_pattern"].strip()
            for row in reader
            if row.get("path_or_pattern", "").strip()
        ]


def main() -> int:
    if not REGISTER.exists():
        print(f"::warning::Content rights register is missing: {REGISTER}")
        return 0

    patterns = _registered_patterns()
    uncovered = [
        asset
        for asset in _tracked_assets()
        if not any(fnmatch.fnmatch(asset, pattern) for pattern in patterns)
    ]
    if not uncovered:
        print("Content rights check: all tracked media assets are covered by register patterns.")
        return 0

    print("::warning::Content rights register does not cover these media assets:")
    for asset in uncovered:
        print(f"  - {asset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
