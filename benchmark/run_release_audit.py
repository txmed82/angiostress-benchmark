#!/usr/bin/env python3
"""Audit the AngioStress v0.1 real-data-first benchmark release package."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("experiments/main/run-real-benchmark-release-refresh-v0/outputs")

REQUIRED_CODE_FILES = [
    "README.md",
    "benchmark/README.md",
    "benchmark/contracts/angiostress_v0_1_real_data.json",
    "benchmark/validate_contract.py",
    "benchmark/run_dias_contract_full_test.py",
    "benchmark/run_cathaction_contract_subset.py",
    "benchmark/run_cathaction_full_tier.py",
    "benchmark/run_release_audit.py",
    "benchmark/stage_public_release.py",
]

DIAS_OUTPUT_DIR = Path("experiments/main/run-dias-contract-full-test-v0/outputs")
CATHACTION_QUICK_SUBSET_OUTPUT_DIR = Path("experiments/main/run-cathaction-contract-subset-v0/outputs")
CATHACTION_OUTPUT_DIR = Path("experiments/main/run-cathaction-real-scaleup-v0/outputs/full_nonempty_5225")
CONTRACT_OUTPUT_DIR = Path("experiments/main/run-real-data-first-benchmark-contract/outputs")

DIAS_REQUIRED_OUTPUTS = [
    "benchmark_index.json",
    "manifest.json",
    "sequences.json",
    "per_frame_metrics.json",
    "per_sequence_summary.json",
    "model_summary.json",
    "leaderboard.json",
    "ranking_diagnostics.json",
    "metrics_summary.json",
    "validation_summary.md",
]

CATHACTION_REQUIRED_OUTPUTS = [
    "RUN.md",
    "benchmark_index.json",
    "cleanup_status.json",
    "environment.json",
    "manifest.json",
    "model_ranking_rows.json",
    "samples.json",
    "per_pair_metrics.json",
    "model_summary.json",
    "leaderboard.json",
    "stability_summary.json",
    "metrics_summary.json",
    "validation_summary.md",
]

CONTRACT_REQUIRED_OUTPUTS = [
    "contract_validation_report.json",
    "metrics_summary.json",
    "validation_summary.md",
]

PRIVATE_RELEASE_PATTERNS = [
    "paper/",
    "manuscript.tex",
    "manuscript.pdf",
    "latex",
    "comments",
    "reviewer",
    "response_letter",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def metric_equals(metrics: dict[str, Any], key: str, expected: float) -> bool:
    value = metrics.get(key)
    return finite_number(value) and float(value) == float(expected)


def metric_finite(metrics: dict[str, Any], key: str) -> bool:
    return finite_number(metrics.get(key))


def first_metric(metrics: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if finite_number(metrics.get(key)):
            return float(metrics[key])
    return default


def count_files(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "size_bytes": 0}
    files = [p for p in path.rglob("*") if p.is_file()]
    return {
        "exists": True,
        "file_count": len(files),
        "size_bytes": sum(p.stat().st_size for p in files),
    }


def required_files_status(root: Path, rel_paths: list[str]) -> dict[str, Any]:
    rows = []
    for rel in rel_paths:
        path = root / rel
        rows.append({"path": rel, "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0})
    return {
        "rows": rows,
        "present": sum(1 for row in rows if row["exists"]),
        "total": len(rows),
        "all_present": all(row["exists"] for row in rows),
    }


def safe_public_path(path: str) -> bool:
    lowered = path.lower()
    return not any(pattern in lowered for pattern in PRIVATE_RELEASE_PATTERNS)


def surface_summary(surface_id: str, output_dir: Path, required_outputs: list[str]) -> dict[str, Any]:
    metrics = read_json(output_dir / "metrics_summary.json")
    manifest = read_json(output_dir / "manifest.json")
    leaderboard = read_json(output_dir / "leaderboard.json")
    return {
        "surface_id": surface_id,
        "output_dir": str(output_dir),
        "required_outputs": required_files_status(output_dir, required_outputs),
        "manifest_run_id": manifest.get("run_id"),
        "leaderboard_rows": len(leaderboard.get("rows", [])),
        "metrics": metrics,
    }


def cathaction_sample_count(metrics: dict[str, Any]) -> float:
    return first_metric(metrics, "s3f_sample_count_per_model", "cathaction_contract_sample_count")


def cathaction_prediction_count(metrics: dict[str, Any]) -> float:
    return first_metric(metrics, "s3f_total_prediction_count", "cathaction_contract_prediction_count")


def cathaction_model_count(metrics: dict[str, Any]) -> float:
    return first_metric(metrics, "s3f_model_count", "cathaction_contract_model_count")


def ensure_full_cathaction_release_aliases(root: Path) -> None:
    output_dir = root / CATHACTION_OUTPUT_DIR
    manifest = read_json(output_dir / "manifest.json")
    metrics = read_json(output_dir / "metrics_summary.json")
    model_summary = read_json(output_dir / "model_summary.json")

    model_rows = model_summary.get("rows", [])
    leaderboard_rows = []
    for rank, row in enumerate(
        sorted(model_rows, key=lambda item: item.get("cathaction_sample_mean_dice", float("-inf")), reverse=True),
        start=1,
    ):
        leaderboard_rows.append(
            {
                "model_id": row["model_id"],
                "rank": rank,
                "surface_id": "cathaction_human_segmentation",
                "primary_metric": "cathaction_sample_mean_dice",
                "cathaction_sample_mean_dice": row.get("cathaction_sample_mean_dice"),
                "cathaction_sample_mean_cldice": row.get("cathaction_sample_mean_cldice"),
                "cathaction_sample_min_dice": row.get("cathaction_sample_min_dice"),
                "cathaction_sample_min_cldice": row.get("cathaction_sample_min_cldice"),
                "mean_area_ratio": row.get("cathaction_sample_mean_area_ratio"),
                "prediction_nonempty_rate": row.get("cathaction_prediction_nonempty_rate"),
            }
        )

    write_json(output_dir / "samples.json", {"rows": manifest.get("sampled_pairs", [])})
    write_json(output_dir / "leaderboard.json", {"rows": leaderboard_rows})
    write_json(
        output_dir / "benchmark_index.json",
        {
            "schema_version": 1,
            "benchmark_id": "angiostress-v0.1-real-data",
            "surface_id": "cathaction_human_segmentation",
            "surface_role": "core",
            "dataset": "CathAction",
            "task": "prompted_device_segmentation",
            "run_id": "run-cathaction-real-scaleup-v0",
            "source_run_id": manifest.get("run_id"),
            "sample_count": int(cathaction_sample_count(metrics)),
            "prediction_count": int(cathaction_prediction_count(metrics)),
            "nonempty_pair_universe": int(metrics.get("s3f_nonempty_pair_universe_count", 0)),
            "empty_mask_pairs_excluded": int(metrics.get("s3f_empty_mask_pairs_excluded_count", 0)),
            "model_count": int(cathaction_model_count(metrics)),
            "model_ids": [row["model_id"] for row in model_rows],
            "primary_metric": "cathaction_sample_mean_dice",
            "leaderboard_path": "leaderboard.json",
            "model_summary_path": "model_summary.json",
            "per_pair_metrics_path": "per_pair_metrics.json",
            "samples_path": "samples.json",
            "synthetic_role": "none_core_real_data",
            "quick_subset_reference": str(CATHACTION_QUICK_SUBSET_OUTPUT_DIR),
        },
    )


def build_release_manifest(root: Path, dias: dict[str, Any], cathaction: dict[str, Any]) -> dict[str, Any]:
    public_files = REQUIRED_CODE_FILES + [
        str(CONTRACT_OUTPUT_DIR / "contract_validation_report.json"),
        str(CONTRACT_OUTPUT_DIR / "metrics_summary.json"),
        str(CONTRACT_OUTPUT_DIR / "validation_summary.md"),
    ]
    public_files += [str(DIAS_OUTPUT_DIR / rel) for rel in DIAS_REQUIRED_OUTPUTS]
    public_files += [str(CATHACTION_OUTPUT_DIR / rel) for rel in CATHACTION_REQUIRED_OUTPUTS]
    derived_artifact_dirs = [
        str(DIAS_OUTPUT_DIR / "predictions"),
        str(CATHACTION_OUTPUT_DIR / "cathaction_predictions"),
        str(CATHACTION_OUTPUT_DIR / "cathaction_overlays"),
    ]
    public_files.extend(derived_artifact_dirs)

    return {
        "schema_version": 1,
        "release_id": "angiostress-v0.1-real-data",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": "angiostress-v0.1-real-data",
        "core_surfaces": [
            {
                "surface_id": "dias_sequence_segmentation",
                "dataset": "DIAS",
                "role": "core_real_data",
                "output_dir": str(DIAS_OUTPUT_DIR),
                "sequence_count": int(dias["metrics"].get("dias_contract_sequence_count", 0)),
                "prediction_rows": int(dias["metrics"].get("dias_contract_prediction_count", 0)),
            },
            {
                "surface_id": "cathaction_human_segmentation",
                "dataset": "CathAction",
                "role": "core_real_data",
                "output_dir": str(CATHACTION_OUTPUT_DIR),
                "sample_count": int(cathaction_sample_count(cathaction["metrics"])),
                "prediction_rows": int(cathaction_prediction_count(cathaction["metrics"])),
                "tier": "full_nonempty_human_segmentation_pairs",
            },
        ],
        "auxiliary_surfaces": [
            {
                "surface_id": "topcow_synthetic_stressor_fixture",
                "dataset": "TopCoW-derived synthetic projection",
                "role": "auxiliary_synthetic_fixture",
            }
        ],
        "public_files": public_files,
        "excluded_private_patterns": PRIVATE_RELEASE_PATTERNS,
        "release_policy": "Publish benchmark code, contracts, manifests, metrics, derived predictions/overlays, and provenance only. Do not publish manuscript LaTeX, paper PDFs, comments, or private review material.",
        "raw_data_boundary": "DIAS and CathAction source datasets must be obtained from their original sources and licenses; this package records benchmark outputs and provenance rather than redistributing raw source data.",
        "claim_boundary": "Benchmark artifact and measurement package; no clinical validation, no model improvement claim, and no positive synthetic-to-real transfer claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    root = args.root
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = read_json(root / "benchmark/contracts/angiostress_v0_1_real_data.json")
    surfaces = contract.get("surfaces", [])
    core_surfaces = [s for s in surfaces if s.get("role") == "core"]
    auxiliary_surfaces = [s for s in surfaces if s.get("role") == "auxiliary"]

    ensure_full_cathaction_release_aliases(root)
    dias = surface_summary("dias_sequence_segmentation", root / DIAS_OUTPUT_DIR, DIAS_REQUIRED_OUTPUTS)
    cathaction = surface_summary("cathaction_human_segmentation", root / CATHACTION_OUTPUT_DIR, CATHACTION_REQUIRED_OUTPUTS)
    contract_outputs = required_files_status(root / CONTRACT_OUTPUT_DIR, CONTRACT_REQUIRED_OUTPUTS)
    code_files = required_files_status(root, REQUIRED_CODE_FILES)

    dias_predictions = count_files(root / DIAS_OUTPUT_DIR / "predictions")
    cathaction_predictions = count_files(root / CATHACTION_OUTPUT_DIR / "cathaction_predictions")
    cathaction_overlays = count_files(root / CATHACTION_OUTPUT_DIR / "cathaction_overlays")

    release_manifest = build_release_manifest(root, dias, cathaction)
    private_manifest_hits = [p for p in release_manifest["public_files"] if not safe_public_path(p)]

    checks = {
        "code_files_present": code_files["all_present"],
        "contract_outputs_present": contract_outputs["all_present"],
        "contract_has_two_core_surfaces": len(core_surfaces) == 2,
        "contract_has_one_auxiliary_surface": len(auxiliary_surfaces) == 1,
        "frozen_model_panel_count_is_three": len(contract.get("frozen_model_panel", [])) == 3,
        "dias_outputs_present": dias["required_outputs"]["all_present"],
        "dias_benchmark_passed": metric_equals(dias["metrics"], "dias_contract_benchmark_passed", 1.0),
        "dias_core_surface": metric_equals(dias["metrics"], "dias_contract_surface_role_core", 1.0),
        "dias_sequence_count_is_20": metric_equals(dias["metrics"], "dias_contract_sequence_count", 20.0),
        "dias_prediction_count_is_345": metric_equals(dias["metrics"], "dias_contract_prediction_count", 345.0),
        "dias_model_count_is_three": metric_equals(dias["metrics"], "dias_contract_model_count", 3.0),
        "dias_zero_synthetic_core_rows": metric_equals(dias["metrics"], "dias_contract_synthetic_core_row_count", 0.0),
        "dias_rank_transfer_metrics_finite": all(
            metric_finite(dias["metrics"], key)
            for key in [
                "dias_contract_aggregate_spearman_synthetic_vs_dias",
                "dias_contract_aggregate_kendall_synthetic_vs_dias",
                "dias_contract_sequence_spearman_bootstrap_mean",
            ]
        ),
        "dias_predictions_copied": dias_predictions["file_count"] == 345,
        "cathaction_outputs_present": cathaction["required_outputs"]["all_present"],
        "cathaction_full_tier_finite": metric_equals(cathaction["metrics"], "s3f_finite_metric_check", 1.0),
        "cathaction_sample_count_is_5225": metric_equals(cathaction["metrics"], "s3f_sample_count_per_model", 5225.0),
        "cathaction_prediction_count_is_15675": metric_equals(cathaction["metrics"], "s3f_total_prediction_count", 15675.0),
        "cathaction_model_count_is_three": metric_equals(cathaction["metrics"], "s3f_model_count", 3.0),
        "cathaction_nonempty_pair_universe_is_5225": metric_equals(
            cathaction["metrics"], "s3f_nonempty_pair_universe_count", 5225.0
        ),
        "cathaction_predictions_copied": cathaction_predictions["file_count"] == 31350,
        "cathaction_overlays_copied": cathaction_overlays["file_count"] == 15675,
        "release_manifest_excludes_private_manuscript_paths": not private_manifest_hits,
    }
    release_audit_passed = all(checks.values())

    metrics_summary = {
        "release_audit_passed": float(release_audit_passed),
        "release_code_file_present_count": float(code_files["present"]),
        "release_code_file_total_count": float(code_files["total"]),
        "release_contract_core_surface_count": float(len(core_surfaces)),
        "release_contract_auxiliary_surface_count": float(len(auxiliary_surfaces)),
        "release_real_core_surface_count": 2.0,
        "release_dias_sequence_count": float(dias["metrics"].get("dias_contract_sequence_count", 0.0)),
        "release_dias_prediction_count": float(dias["metrics"].get("dias_contract_prediction_count", 0.0)),
        "release_dias_synthetic_core_row_count": float(dias["metrics"].get("dias_contract_synthetic_core_row_count", 0.0)),
        "release_cathaction_sample_count": cathaction_sample_count(cathaction["metrics"]),
        "release_cathaction_prediction_count": cathaction_prediction_count(cathaction["metrics"]),
        "release_cathaction_nonempty_pair_universe_count": float(
            cathaction["metrics"].get("s3f_nonempty_pair_universe_count", 0.0)
        ),
        "release_cathaction_synthetic_core_row_count": 0.0,
        "release_total_real_prediction_rows": float(
            dias["metrics"].get("dias_contract_prediction_count", 0.0)
            + cathaction_prediction_count(cathaction["metrics"])
        ),
        "release_derived_prediction_file_count": float(
            dias_predictions["file_count"] + cathaction_predictions["file_count"]
        ),
        "release_derived_overlay_file_count": float(cathaction_overlays["file_count"]),
        "release_private_manifest_hit_count": float(len(private_manifest_hits)),
    }

    audit = {
        "schema_version": 1,
        "run_id": "run-real-benchmark-release-refresh-v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_audit_passed": release_audit_passed,
        "checks": checks,
        "private_manifest_hits": private_manifest_hits,
        "code_files": code_files,
        "contract_outputs": contract_outputs,
        "contract_surface_counts": {
            "core": len(core_surfaces),
            "auxiliary": len(auxiliary_surfaces),
            "total": len(surfaces),
        },
        "derived_artifacts": {
            "dias_predictions": dias_predictions,
            "cathaction_predictions": cathaction_predictions,
            "cathaction_overlays": cathaction_overlays,
        },
        "surfaces": {
            "dias_sequence_segmentation": {
                "output_dir": dias["output_dir"],
                "required_outputs": dias["required_outputs"],
                "leaderboard_rows": dias["leaderboard_rows"],
                "key_metrics": {
                    "sequence_count": dias["metrics"].get("dias_contract_sequence_count"),
                    "prediction_count": dias["metrics"].get("dias_contract_prediction_count"),
                    "model_count": dias["metrics"].get("dias_contract_model_count"),
                    "aggregate_spearman_synthetic_vs_dias": dias["metrics"].get("dias_contract_aggregate_spearman_synthetic_vs_dias"),
                    "sequence_spearman_bootstrap_mean": dias["metrics"].get("dias_contract_sequence_spearman_bootstrap_mean"),
                    "sequence_spearman_ci95_low": dias["metrics"].get("dias_contract_sequence_spearman_ci95_low"),
                    "sequence_spearman_ci95_high": dias["metrics"].get("dias_contract_sequence_spearman_ci95_high"),
                },
            },
            "cathaction_human_segmentation": {
                "output_dir": cathaction["output_dir"],
                "required_outputs": cathaction["required_outputs"],
                "leaderboard_rows": cathaction["leaderboard_rows"],
                "key_metrics": {
                    "sample_count": cathaction["metrics"].get("cathaction_contract_sample_count"),
                    "full_tier_sample_count": cathaction["metrics"].get("s3f_sample_count_per_model"),
                    "prediction_count": cathaction_prediction_count(cathaction["metrics"]),
                    "model_count": cathaction_model_count(cathaction["metrics"]),
                    "sam_vit_b_mean_dice": cathaction["metrics"].get("s3f_sam_vit_b_cathaction_sample_mean_dice"),
                    "sam_vit_l_mean_dice": cathaction["metrics"].get("s3f_sam_vit_l_cathaction_sample_mean_dice"),
                    "medsam_vit_b_mean_dice": cathaction["metrics"].get("s3f_medsam_vit_b_cathaction_sample_mean_dice"),
                    "spearman_synthetic_mean_vs_cathaction_mean_dice": cathaction["metrics"].get("s3f_spearman_synthetic_mean_vs_cathaction_mean_dice"),
                    "bootstrap_spearman_mean": cathaction["metrics"].get("s3f_bootstrap_spearman_mean"),
                    "bootstrap_spearman_ci95_low": cathaction["metrics"].get("s3f_bootstrap_spearman_ci95_low"),
                    "bootstrap_spearman_ci95_high": cathaction["metrics"].get("s3f_bootstrap_spearman_ci95_high"),
                },
            },
        },
        "release_manifest": release_manifest,
        "metrics_summary": metrics_summary,
    }

    (output_dir / "release_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    (output_dir / "release_manifest.json").write_text(json.dumps(release_manifest, indent=2, sort_keys=True) + "\n")
    (output_dir / "metrics_summary.json").write_text(json.dumps(metrics_summary, indent=2, sort_keys=True) + "\n")

    lines = [
        "# AngioStress v0.1 Release Audit",
        "",
        f"- release_audit_passed: `{release_audit_passed}`",
        f"- core real-data surfaces: `{len(core_surfaces)}`",
        f"- auxiliary synthetic fixtures: `{len(auxiliary_surfaces)}`",
        f"- DIAS: `{int(metrics_summary['release_dias_sequence_count'])}` sequences, `{int(metrics_summary['release_dias_prediction_count'])}` prediction rows",
        f"- CathAction: `{int(metrics_summary['release_cathaction_sample_count'])}` pairs, `{int(metrics_summary['release_cathaction_prediction_count'])}` prediction rows",
        f"- derived prediction files: `{int(metrics_summary['release_derived_prediction_file_count'])}`",
        f"- private manifest hits: `{int(metrics_summary['release_private_manifest_hit_count'])}`",
        "",
        "## Claim Boundary",
        "",
        "This audit validates benchmark package structure and provenance. It does not claim clinical validation, model improvement, or positive synthetic-to-real transfer.",
    ]
    (output_dir / "validation_summary.md").write_text("\n".join(lines) + "\n")

    print(f"release_audit_passed={int(release_audit_passed)}")
    print(f"output_dir={output_dir}")
    for key, value in metrics_summary.items():
        print(f"{key}={value}")

    if not release_audit_passed:
        failed = [key for key, value in checks.items() if not value]
        raise SystemExit("Release audit failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
