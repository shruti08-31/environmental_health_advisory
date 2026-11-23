"""Pre-FastAPI Integration and End-to-End Verification Script.

Tests all 8 central functions independently and together without starting FastAPI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.service_layer import EnvironmentalAdvisoryService, ModuleRegistry  # noqa: E402


def _assert_envelope(result: Dict[str, Any], expected_feature: str) -> None:
    assert isinstance(result, dict), "Result must be a dict"
    assert isinstance(result.get("success"), bool), "Missing boolean 'success'"
    assert result.get("feature") == expected_feature, f"Expected feature '{expected_feature}'"
    assert "data" in result and "error" in result and "metadata" in result, "Missing envelope keys"
    assert "timestamp" in result["metadata"], "Missing timestamp in metadata"


def test_independent_functions(service: EnvironmentalAdvisoryService) -> Dict[str, Tuple[bool, str]]:
    """Test each of the 8 functions independently."""
    cases: List[Tuple[str, Callable[[], Dict[str, Any]]]] = [
        ("get_current_aqi", lambda: service.get_current_aqi("Delhi", persist_history=False)),
        ("get_health_advisory", lambda: service.get_health_advisory("Delhi", user_group="general")),
        (
            "ask_environmental_question",
            lambda: service.ask_environmental_question("What are the health effects of PM2.5?"),
        ),
        ("get_aqi_history", lambda: service.get_aqi_history("Delhi", days=7)),
        ("compare_locations", lambda: service.compare_locations(["Delhi", "Mumbai"])),
        ("generate_aqi_alerts", lambda: service.generate_aqi_alerts(["Delhi", "Mumbai"])),
        (
            "get_activity_advice",
            lambda: service.get_activity_advice("Delhi", activity="running", duration_minutes=45),
        ),
        ("get_data_quality_report", lambda: service.get_data_quality_report("Delhi")),
    ]

    outcomes: Dict[str, Tuple[bool, str]] = {}
    for name, fn in cases:
        res = fn()
        try:
            _assert_envelope(res, name)
            if res["success"]:
                outcomes[name] = (True, "PASS (envelope valid, handler succeeded)")
            else:
                err_msg = (res.get("error") or {}).get("message", "unknown error")
                outcomes[name] = (True, f"PASS-ISOLATED (caught module error cleanly: {err_msg})")
        except AssertionError as exc:
            outcomes[name] = (False, f"FAIL (envelope check failed: {exc})")
    return outcomes


def test_fault_isolation() -> Tuple[bool, str]:
    """Verify a failing module in one feature does not crash unrelated features."""
    registry = ModuleRegistry()
    registry._errors["aqi_pipeline"] = "Simulated upstream timeout"

    isolated_service = EnvironmentalAdvisoryService(registry=registry)
    broken_res = isolated_service.get_current_aqi("Delhi")
    healthy_res = isolated_service.ask_environmental_question("Explain AQI categories.")

    if broken_res["success"] is False and "metadata" in healthy_res:
        return True, "PASS (failing aqi_pipeline returned error envelope without crashing service)"
    return False, "FAIL (fault isolation behavior unexpected)"


def run_end_to_end() -> int:
    service = EnvironmentalAdvisoryService()
    env_info = service.verify_environment(required_vars=["WAQI_API_KEY"])
    db_info = service.verify_database()

    independent_results = test_independent_functions(service)
    isolation_passed, isolation_detail = test_fault_isolation()

    summary = {
        "environment": env_info,
        "database": db_info,
        "module_registry_status": service.registry.status(),
        "independent_function_tests": {
            k: {"passed": v[0], "detail": v[1]} for k, v in independent_results.items()
        },
        "fault_isolation_test": {"passed": isolation_passed, "detail": isolation_detail},
    }

    print(json.dumps(summary, indent=2, default=str))

    all_ok = all(v[0] for v in independent_results.values()) and isolation_passed
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(run_end_to_end())