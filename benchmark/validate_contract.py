#!/usr/bin/env python3
"""Validate the AngioStress real-data-first benchmark contract."""

from __future__ import annotations

import argparse
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_nested(data: Any, dotted_key: str) -> Any:
    current = data
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted_key)
    return current


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def numeric_equal(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-9)
    return left == right


def validate_surface(root: Path, surface: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "surface_id": surface["surface_id"],
        "role": surface["role"],
        "dataset": surface["dataset"],
        "path_checks": [],
        "json_checks": [],
        "finite_metric_checks": [],
        "ok": True,
    }

    declared_paths = list(surface.get("source_paths", [])) + list(surface.get("prior_pilot_outputs", []))
    seen_paths = sorted(set(declared_paths))
    for rel_path in seen_paths:
        path = root / rel_path
        check = {"path": rel_path, "exists": path.exists()}
        result["path_checks"].append(check)
        if not check["exists"]:
            result["ok"] = False

    for validation in surface.get("validation_checks", []):
        rel_path = validation["path"]
        path = root / rel_path
        if not path.exists():
            result["json_checks"].append({"path": rel_path, "ok": False, "error": "missing_file"})
            result["ok"] = False
            continue

        try:
            data = load_json(path)
        except Exception as exc:  # noqa: BLE001 - report exact parse failure in validation artifact
            result["json_checks"].append({"path": rel_path, "ok": False, "error": f"json_parse_failed: {exc}"})
            result["ok"] = False
            continue

        for key, expected in validation.get("json_equals", {}).items():
            try:
                actual = get_nested(data, key)
                passed = numeric_equal(actual, expected)
                check = {"path": rel_path, "key": key, "expected": expected, "actual": actual, "ok": passed}
            except KeyError:
                check = {"path": rel_path, "key": key, "expected": expected, "actual": None, "ok": False, "error": "missing_key"}
            result["json_checks"].append(check)
            if not check["ok"]:
                result["ok"] = False

        for key in validation.get("finite_metrics", []):
            try:
                actual = get_nested(data, key)
                passed = is_finite_number(actual)
                check = {"path": rel_path, "key": key, "actual": actual, "ok": passed}
            except KeyError:
                check = {"path": rel_path, "key": key, "actual": None, "ok": False, "error": "missing_key"}
            result["finite_metric_checks"].append(check)
            if not check["ok"]:
                result["ok"] = False

    return result


def summarize(report: dict[str, Any]) -> dict[str, float]:
    surfaces = report["surface_results"]
    path_checks = [check for surface in surfaces for check in surface["path_checks"]]
    json_checks = [check for surface in surfaces for check in surface["json_checks"]]
    finite_checks = [check for surface in surfaces for check in surface["finite_metric_checks"]]
    core_surfaces = [surface for surface in surfaces if surface["role"] == "core"]
    auxiliary_surfaces = [surface for surface in surfaces if surface["role"] == "auxiliary"]

    def rate(checks: list[dict[str, Any]]) -> float:
        if not checks:
            return 1.0
        return sum(1 for check in checks if check.get("ok") or check.get("exists")) / len(checks)

    metrics = {
        "benchmark_contract_surface_count": float(len(surfaces)),
        "benchmark_contract_core_surface_count": float(len(core_surfaces)),
        "benchmark_contract_auxiliary_surface_count": float(len(auxiliary_surfaces)),
        "benchmark_contract_required_path_count": float(len(path_checks)),
        "benchmark_contract_required_file_exists_rate": rate(path_checks),
        "benchmark_contract_json_check_count": float(len(json_checks)),
        "benchmark_contract_json_check_pass_rate": rate(json_checks),
        "benchmark_contract_finite_metric_check_count": float(len(finite_checks)),
        "benchmark_contract_finite_metric_pass_rate": rate(finite_checks),
        "benchmark_contract_core_surface_pass_rate": rate(core_surfaces),
        "benchmark_contract_validation_passed": 1.0 if report["ok"] else 0.0,
        "benchmark_contract_synthetic_auxiliary_marked": 1.0
        if any(surface["role"] == "auxiliary" and "synthetic" in surface["surface_id"] for surface in surfaces)
        else 0.0,
    }

    for surface in surfaces:
        for check in surface["json_checks"]:
            if check.get("ok") and isinstance(check.get("actual"), (int, float)):
                metric_key = f"source_{surface['surface_id']}_{check['key'].replace('.', '_')}"
                metrics[metric_key] = float(check["actual"])

    return metrics


def write_summary_md(report: dict[str, Any], metrics: dict[str, float], output_path: Path) -> None:
    lines = [
        "# AngioStress Real-Data-First Contract Validation",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- contract_id: `{report['contract_id']}`",
        f"- validation_passed: `{report['ok']}`",
        f"- core_surfaces: `{int(metrics['benchmark_contract_core_surface_count'])}`",
        f"- auxiliary_surfaces: `{int(metrics['benchmark_contract_auxiliary_surface_count'])}`",
        "",
        "## Surface Results",
        "",
    ]
    for surface in report["surface_results"]:
        lines.extend(
            [
                f"### {surface['surface_id']}",
                "",
                f"- role: `{surface['role']}`",
                f"- dataset: `{surface['dataset']}`",
                f"- ok: `{surface['ok']}`",
                f"- path_checks: `{sum(1 for c in surface['path_checks'] if c.get('exists'))}/{len(surface['path_checks'])}`",
                f"- json_checks: `{sum(1 for c in surface['json_checks'] if c.get('ok'))}/{len(surface['json_checks'])}`",
                f"- finite_metric_checks: `{sum(1 for c in surface['finite_metric_checks'] if c.get('ok'))}/{len(surface['finite_metric_checks'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default="benchmark/contracts/angiostress_v0_1_real_data.json")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contract_path = (root / args.contract).resolve()
    contract = load_json(contract_path)
    output_dir = root / (args.output_dir or contract["validation_output"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    surface_results = [validate_surface(root, surface) for surface in contract["surfaces"]]
    ok = all(surface["ok"] for surface in surface_results)
    report = {
        "schema_version": 1,
        "run_id": contract["validation_output"]["run_id"],
        "contract_id": contract["benchmark_id"],
        "contract_path": str(contract_path.relative_to(root)),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": contract["claim_boundary"],
        "benchmark_role": contract["benchmark_role"],
        "surface_results": surface_results,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "ok": ok,
    }
    metrics = summarize(report)

    (output_dir / "contract_validation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "metrics_summary.json").write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    write_summary_md(report, metrics, output_dir / "validation_summary.md")

    print(json.dumps({"ok": ok, "output_dir": str(output_dir), "metrics": metrics}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
