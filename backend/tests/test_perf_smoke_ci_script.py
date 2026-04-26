from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db


def _load_perf_smoke_module():
    script_path = Path(__file__).resolve().parents[1].parent / "scripts" / "perf_smoke_ci.py"
    if not script_path.exists():
        pytest.skip("perf_smoke_ci.py is outside the backend-only docker volume")
    spec = importlib.util.spec_from_file_location("perf_smoke_ci", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_perf_smoke_enforces_p99_budget(monkeypatch):
    perf_smoke = _load_perf_smoke_module()
    latencies = iter([10.0, 20.0, 30.0, 400.0])

    def fake_request_once(base_url: str, path: str, timeout: float):
        del base_url, path, timeout
        return True, next(latencies), 200

    monkeypatch.setattr(perf_smoke, "_request_once", fake_request_once)

    case = perf_smoke.PerfCase(
        path="/api/test",
        requests=4,
        concurrency=1,
        warmup=0,
        p95_budget_ms=1000.0,
        p99_budget_ms=100.0,
    )

    report, errors = perf_smoke._run_case(
        "http://127.0.0.1:8000",
        case,
        timeout=1.0,
    )

    assert report["p99_ms"] > case.p99_budget_ms
    assert any("p99=" in error for error in errors)


def test_perf_smoke_local_profile_scales_load_for_dev_rate_limit():
    perf_smoke = _load_perf_smoke_module()
    case = perf_smoke.PerfCase(
        path="/api/test",
        requests=120,
        concurrency=12,
        warmup=5,
        p95_budget_ms=700.0,
        p99_budget_ms=1100.0,
    )

    local_case = perf_smoke._case_for_profile(case, "local")

    assert local_case.requests == 20
    assert local_case.concurrency == 4
    assert local_case.warmup == 2
    assert local_case.p95_budget_ms == case.p95_budget_ms
    assert local_case.p99_budget_ms == case.p99_budget_ms
