from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db


def _frontend_file(path: str) -> Path:
    file_path = Path(__file__).resolve().parents[1].parent / "frontend" / "src" / path
    if not file_path.exists():
        pytest.skip(f"{file_path} is outside the backend-only docker volume")
    return file_path


def _frontend_root_file(path: str) -> Path:
    file_path = Path(__file__).resolve().parents[1].parent / "frontend" / path
    if not file_path.exists():
        pytest.skip(f"{file_path} is outside the backend-only docker volume")
    return file_path


def test_frontend_package_does_not_depend_on_element_plus():
    package_json = _frontend_root_file("package.json").read_text()

    assert '"element-plus"' not in package_json


def test_frontend_vite_config_does_not_use_element_plus_resolver():
    package_json = _frontend_root_file("package.json").read_text()
    vite_config = _frontend_root_file("vite.config.ts").read_text()

    assert '"unplugin-vue-components"' not in package_json
    assert "ElementPlusResolver" not in vite_config


def test_admin_species_catalog_table_stays_native():
    source = _frontend_file("components/admin/AdminSpeciesCatalogTable.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_catalog_quality_panel_stays_native():
    source = _frontend_file("components/admin/AdminCatalogQualityPanel.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_catalog_import_panel_stays_native():
    source = _frontend_file("components/admin/AdminCatalogImportPanel.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_audit_panel_stays_native():
    source = _frontend_file("components/admin/AdminAuditPanel.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_ops_panel_stays_native():
    source = _frontend_file("components/admin/AdminOpsPanel.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_zone_import_panel_stays_native():
    source = _frontend_file("components/admin/AdminZoneImportPanel.vue").read_text()

    assert "<el-" not in source
    assert "v-loading" not in source


def test_admin_species_tab_defers_catalog_import_panel():
    source = _frontend_file("components/admin/AdminSpeciesTab.vue").read_text()

    assert 'v-if="showCatalogImportPanel"' in source
    assert "void loadCatalogImportBatches()" not in source


def test_expert_queue_dialogs_stay_native():
    source = _frontend_file("components/expert/ExpertQueueDialogs.vue").read_text()

    assert "<el-" not in source
