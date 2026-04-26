#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import NamedTuple


class BundleBudget(NamedTuple):
    pattern: str
    max_bytes: int
    required: bool = True


DEFAULT_BUDGETS = (
    BundleBudget("_plugin-vue_export-helper-*.js", 70_000),
    BundleBudget("index-*.js", 55_000),
    BundleBudget("axios-*.js", 45_000),
    BundleBudget("AdminView-*.js", 8_000),
    BundleBudget("AdminSpeciesTab-*.js", 22_000),
    BundleBudget("AdminCatalogQualityPanel-*.js", 5_000),
    BundleBudget("AdminSpeciesCatalogTable-*.js", 7_000),
    BundleBudget("AdminAuditTab-*.js", 16_000),
    BundleBudget("AdminSpeciesFormDialog-*.js", 12_000),
    BundleBudget("AdminCatalogImportPanel-*.js", 9_000),
    BundleBudget("AdminZoneImportPanel-*.js", 3_000),
    BundleBudget("ObserveView-*.js", 25_000),
    BundleBudget("SpeciesListView-*.js", 15_000),
    BundleBudget("ExpertQueueView-*.js", 12_000),
    BundleBudget("ExpertQueueDialogs-*.js", 7_000),
    BundleBudget("IdentifyView-*.js", 10_000),
    BundleBudget("LoginView-*.js", 8_000),
)


def _format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.2f} KB"
    return f"{value / 1024 / 1024:.2f} MB"


def _parse_budget(value: str) -> BundleBudget:
    if ":" not in value:
        raise argparse.ArgumentTypeError("budget must use PATTERN:MAX_BYTES format")
    pattern, raw_limit = value.rsplit(":", 1)
    pattern = pattern.strip()
    if not pattern:
        raise argparse.ArgumentTypeError("budget pattern cannot be empty")
    try:
        max_bytes = int(raw_limit)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("budget MAX_BYTES must be an integer") from exc
    if max_bytes <= 0:
        raise argparse.ArgumentTypeError("budget MAX_BYTES must be positive")
    return BundleBudget(pattern, max_bytes)


def _check_budgets(
    assets_dir: Path,
    budgets: list[BundleBudget] | tuple[BundleBudget, ...],
) -> tuple[list[dict[str, int | str]], list[str]]:
    reports: list[dict[str, int | str]] = []
    errors: list[str] = []

    for budget in budgets:
        matches = sorted(
            (path for path in assets_dir.glob(budget.pattern) if path.is_file()),
            key=lambda path: path.stat().st_size,
            reverse=True,
        )
        if not matches:
            if budget.required:
                errors.append(f"missing required asset for pattern {budget.pattern}")
            continue

        largest = matches[0]
        largest_bytes = largest.stat().st_size
        over_budget_bytes = max(0, largest_bytes - budget.max_bytes)
        reports.append({
            "pattern": budget.pattern,
            "largest_asset": largest.name,
            "largest_bytes": largest_bytes,
            "max_bytes": budget.max_bytes,
            "over_budget_bytes": over_budget_bytes,
        })
        if over_budget_bytes > 0:
            errors.append(
                f"{budget.pattern}: {largest.name} is {_format_bytes(largest_bytes)}, "
                f"budget {_format_bytes(budget.max_bytes)}, over by {_format_bytes(over_budget_bytes)}"
            )

    return reports, errors


def _largest_assets(assets_dir: Path, limit: int) -> list[dict[str, int | str]]:
    assets = sorted(
        (
            path for path in assets_dir.iterdir()
            if path.is_file() and path.suffix in {".js", ".css"}
        ),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )
    return [
        {
            "asset": path.name,
            "bytes": path.stat().st_size,
        }
        for path in assets[:limit]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Vite frontend bundle budgets.")
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("frontend/dist/assets"),
        help="Directory with built Vite assets.",
    )
    parser.add_argument(
        "--budget",
        action="append",
        type=_parse_budget,
        help="Budget in PATTERN:MAX_BYTES format. Can be passed multiple times.",
    )
    parser.add_argument(
        "--top-assets",
        type=int,
        default=0,
        help="Print the largest JS/CSS assets from the build output.",
    )
    args = parser.parse_args()

    assets_dir: Path = args.assets_dir
    if not assets_dir.exists():
        print(f"ERROR: assets directory does not exist: {assets_dir}")
        return 2

    budgets = args.budget or DEFAULT_BUDGETS
    reports, errors = _check_budgets(assets_dir, budgets)

    if args.top_assets > 0:
        print(f"Top {args.top_assets} frontend assets:")
        for asset in _largest_assets(assets_dir, args.top_assets):
            print(f"  {asset['asset']}: {_format_bytes(int(asset['bytes']))}")

    for report in reports:
        print(
            f"{report['pattern']}: {report['largest_asset']} "
            f"{_format_bytes(int(report['largest_bytes']))} "
            f"/ budget {_format_bytes(int(report['max_bytes']))}"
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("FRONTEND_BUNDLE_BUDGET_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
