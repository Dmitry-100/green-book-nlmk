from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db


def _load_bundle_budget_module():
    script_path = (
        Path(__file__).resolve().parents[1].parent
        / "scripts"
        / "frontend_bundle_budget.py"
    )
    if not script_path.exists():
        pytest.skip("frontend_bundle_budget.py is outside the backend-only docker volume")
    spec = importlib.util.spec_from_file_location("frontend_bundle_budget", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bundle_budget_accepts_matching_asset_under_limit(tmp_path: Path):
    bundle_budget = _load_bundle_budget_module()
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "AdminView-abc.js").write_bytes(b"x" * 100)

    reports, errors = bundle_budget._check_budgets(
        assets_dir,
        [bundle_budget.BundleBudget("AdminView-*.js", 120)],
    )

    assert errors == []
    assert reports[0]["largest_asset"] == "AdminView-abc.js"
    assert reports[0]["largest_bytes"] == 100


def test_bundle_budget_reports_asset_over_limit(tmp_path: Path):
    bundle_budget = _load_bundle_budget_module()
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "AdminView-abc.js").write_bytes(b"x" * 121)

    reports, errors = bundle_budget._check_budgets(
        assets_dir,
        [bundle_budget.BundleBudget("AdminView-*.js", 120)],
    )

    assert reports[0]["over_budget_bytes"] == 1
    assert any("AdminView-*.js" in error and "121 B" in error for error in errors)


def test_bundle_budget_reports_missing_required_asset(tmp_path: Path):
    bundle_budget = _load_bundle_budget_module()
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    _, errors = bundle_budget._check_budgets(
        assets_dir,
        [bundle_budget.BundleBudget("AdminView-*.js", 120)],
    )

    assert errors == ["missing required asset for pattern AdminView-*.js"]


def test_bundle_budget_lists_largest_js_and_css_assets(tmp_path: Path):
    bundle_budget = _load_bundle_budget_module()
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "small.js").write_bytes(b"x" * 10)
    (assets_dir / "large.css").write_bytes(b"x" * 30)
    (assets_dir / "ignored.map").write_bytes(b"x" * 100)

    reports = bundle_budget._largest_assets(assets_dir, limit=2)

    assert reports == [
        {"asset": "large.css", "bytes": 30},
        {"asset": "small.js", "bytes": 10},
    ]


def test_default_bundle_budgets_cover_hot_routes():
    bundle_budget = _load_bundle_budget_module()

    patterns = {budget.pattern for budget in bundle_budget.DEFAULT_BUDGETS}

    assert {
        "_plugin-vue_export-helper-*.js",
        "index-*.js",
        "axios-*.js",
        "AdminView-*.js",
        "AdminSpeciesTab-*.js",
        "AdminCatalogQualityPanel-*.js",
        "AdminSpeciesCatalogTable-*.js",
        "AdminAuditTab-*.js",
        "AdminSpeciesFormDialog-*.js",
        "AdminCatalogImportPanel-*.js",
        "AdminZoneImportPanel-*.js",
        "ObserveView-*.js",
        "SpeciesListView-*.js",
        "ExpertQueueView-*.js",
        "ExpertQueueDialogs-*.js",
        "IdentifyView-*.js",
        "LoginView-*.js",
    } <= patterns


def test_default_admin_bundle_budget_tracks_lazy_route_shell():
    bundle_budget = _load_bundle_budget_module()

    budgets = {budget.pattern: budget.max_bytes for budget in bundle_budget.DEFAULT_BUDGETS}

    assert budgets["AdminView-*.js"] <= 8_000


def test_default_shared_bundle_budgets_track_runtime_and_vendor_chunks():
    bundle_budget = _load_bundle_budget_module()

    budgets = {budget.pattern: budget.max_bytes for budget in bundle_budget.DEFAULT_BUDGETS}

    assert budgets["_plugin-vue_export-helper-*.js"] <= 70_000
    assert budgets["index-*.js"] <= 55_000
    assert budgets["axios-*.js"] <= 45_000


def test_default_admin_lazy_tab_budgets_track_split_chunks():
    bundle_budget = _load_bundle_budget_module()

    budgets = {budget.pattern: budget.max_bytes for budget in bundle_budget.DEFAULT_BUDGETS}

    assert budgets["AdminSpeciesTab-*.js"] <= 22_000
    assert budgets["AdminCatalogQualityPanel-*.js"] <= 5_000
    assert budgets["AdminSpeciesCatalogTable-*.js"] <= 7_000
    assert budgets["AdminAuditTab-*.js"] <= 16_000


def test_default_admin_secondary_budgets_track_heavy_lazy_chunks():
    bundle_budget = _load_bundle_budget_module()

    budgets = {budget.pattern: budget.max_bytes for budget in bundle_budget.DEFAULT_BUDGETS}

    assert budgets["AdminSpeciesFormDialog-*.js"] <= 12_000
    assert budgets["AdminCatalogImportPanel-*.js"] <= 9_000
    assert budgets["AdminZoneImportPanel-*.js"] <= 3_000


def test_default_expert_dialog_budget_tracks_lazy_chunk():
    bundle_budget = _load_bundle_budget_module()

    budgets = {budget.pattern: budget.max_bytes for budget in bundle_budget.DEFAULT_BUDGETS}

    assert budgets["ExpertQueueDialogs-*.js"] <= 7_000
