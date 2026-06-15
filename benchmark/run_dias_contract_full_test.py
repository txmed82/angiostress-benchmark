#!/usr/bin/env python3
"""Materialize a contract-owned DIAS full-test benchmark from audited outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any


RUN_ID = "run-dias-contract-full-test-v0"
CONTRACT_ID = "angiostress-v0.1-real-data"
SURFACE_ID = "dias_sequence_segmentation"
SOURCE_RUN_ID = "s3b-dias-full-test-split-ranking"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def finite_numbers(data: Any) -> bool:
    if isinstance(data, dict):
        return all(finite_numbers(value) for value in data.values())
    if isinstance(data, list):
        return all(finite_numbers(value) for value in data)
    if is_number(data):
        return math.isfinite(float(data))
    return True


def rows_from(data: Any, label: str) -> list[dict[str, Any]]:
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise TypeError(f"{label} must be a list or a dict with rows")
    return [dict(row) for row in rows]


def surface_from_contract(contract: dict[str, Any]) -> dict[str, Any]:
    for surface in contract.get("surfaces", []):
        if (surface.get("surface_id") or surface.get("id")) == SURFACE_ID:
            return surface
    raise KeyError(f"surface {SURFACE_ID!r} not found in contract")


def ranked_leaderboard(model_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        model_rows,
        key=lambda row: (
            float(row["dias_multisequence_mean_dice"]),
            float(row["dias_multisequence_mean_cldice"]),
        ),
        reverse=True,
    )
    leaderboard = []
    for rank, row in enumerate(sorted_rows, start=1):
        leaderboard.append(
            {
                "rank": rank,
                "model_id": row["model_id"],
                "surface_id": SURFACE_ID,
                "primary_metric": "dias_multisequence_mean_dice",
                "dias_multisequence_mean_dice": float(row["dias_multisequence_mean_dice"]),
                "dias_multisequence_mean_cldice": float(row["dias_multisequence_mean_cldice"]),
                "dias_multisequence_median_dice": float(row["dias_multisequence_median_dice"]),
                "sequence_mean_dice_min": float(row["sequence_mean_dice_min"]),
                "sequence_mean_dice_max": float(row["sequence_mean_dice_max"]),
                "evaluated_sequence_count": int(row["evaluated_sequence_count"]),
                "evaluated_frame_count": int(row["evaluated_frame_count"]),
            }
        )
    return leaderboard


def benchmark_frame_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in source_rows:
        copied = dict(row)
        copied["benchmark_id"] = CONTRACT_ID
        copied["benchmark_run_id"] = RUN_ID
        copied["surface_id"] = SURFACE_ID
        copied["source_run_id"] = SOURCE_RUN_ID
        copied["task"] = "prompted_vessel_segmentation"
        copied["gt_source"] = "DIAS sequence-level binary vessel mask"
        copied["synthetic_role"] = "none_core_real_data"
        rows.append(copied)
    return rows


def benchmark_sequence_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in source_rows:
        copied = dict(row)
        copied["benchmark_id"] = CONTRACT_ID
        copied["benchmark_run_id"] = RUN_ID
        copied["surface_id"] = SURFACE_ID
        copied["source_run_id"] = SOURCE_RUN_ID
        copied["task"] = "prompted_vessel_segmentation"
        copied["gt_source"] = "DIAS sequence-level binary vessel mask"
        copied["synthetic_role"] = "none_core_real_data"
        rows.append(copied)
    return rows


def sequence_index_rows(manifest: dict[str, Any], sequence_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sequence: dict[str, dict[str, Any]] = {}
    for row in sequence_rows:
        seq = str(row["sequence_id"])
        entry = by_sequence.setdefault(
            seq,
            {
                "benchmark_id": CONTRACT_ID,
                "benchmark_run_id": RUN_ID,
                "surface_id": SURFACE_ID,
                "sequence_id": seq,
                "split": row.get("split", "test"),
                "available_frame_count": row.get("available_frame_count"),
                "evaluated_frame_count": row.get("evaluated_frame_count"),
                "gt_area_pixels": row.get("gt_area_pixels"),
                "gt_component_count": row.get("gt_component_count"),
                "model_count": 0,
                "synthetic_role": "none_core_real_data",
            },
        )
        entry["model_count"] += 1

    selected = manifest.get("selected_sequences") or manifest.get("selected_sequence_ids") or []
    for item in selected:
        seq = item.get("sequence_id") if isinstance(item, dict) else str(item)
        by_sequence.setdefault(
            str(seq),
            {
                "benchmark_id": CONTRACT_ID,
                "benchmark_run_id": RUN_ID,
                "surface_id": SURFACE_ID,
                "sequence_id": str(seq),
                "split": "test",
                "model_count": 0,
                "synthetic_role": "none_core_real_data",
            },
        )

    return [by_sequence[seq] for seq in sorted(by_sequence)]


def copy_artifacts(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    copied = {}
    for subdir in ["predictions"]:
        src = source_dir / subdir
        dst = output_dir / subdir
        if not src.exists():
            copied[subdir] = {"source_exists": False, "file_count": 0, "size_bytes": 0}
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        files = [p for p in dst.rglob("*") if p.is_file()]
        copied[subdir] = {
            "source_exists": True,
            "file_count": len(files),
            "size_bytes": sum(p.stat().st_size for p in files),
        }
    return copied


def count_unique(rows: list[dict[str, Any]], key: str) -> int:
    return len({row[key] for row in rows})


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    contract = read_json(args.contract)
    surface = surface_from_contract(contract)

    source_dir = args.source_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = read_json(source_dir / "manifest.json")
    source_metrics = read_json(source_dir / "metrics_summary.json")
    model_rows = rows_from(read_json(source_dir / "model_summary.json"), "model_summary")
    frame_rows = rows_from(read_json(source_dir / "per_frame_metrics.json"), "per_frame_metrics")
    sequence_summary_rows = rows_from(
        read_json(source_dir / "per_sequence_summary.json"),
        "per_sequence_summary",
    )
    ranking_diagnostics = read_json(source_dir / "ranking_diagnostics.json")

    contract_metrics = {}
    if args.contract_validation_metrics.exists():
        contract_metrics = read_json(args.contract_validation_metrics)

    benchmark_frames = benchmark_frame_rows(frame_rows)
    benchmark_sequences = benchmark_sequence_rows(sequence_summary_rows)
    sequence_index = sequence_index_rows(source_manifest, sequence_summary_rows)
    leaderboard = ranked_leaderboard(model_rows)

    model_count = count_unique(model_rows, "model_id")
    sequence_count = count_unique(frame_rows, "sequence_id")
    frame_count = len(frame_rows)
    per_model_frame_counts = {
        model_id: sum(1 for row in frame_rows if row["model_id"] == model_id)
        for model_id in sorted({row["model_id"] for row in frame_rows})
    }
    frame_count_per_model = min(per_model_frame_counts.values()) if per_model_frame_counts else 0
    synthetic_core_rows = sum(1 for row in benchmark_frames if row["synthetic_role"] != "none_core_real_data")

    checks = {
        "surface_role_is_core": surface.get("role") == "core",
        "sequence_count_matches": sequence_count == args.expected_sequence_count,
        "frame_count_per_model_matches": all(
            count == args.expected_frame_count_per_model for count in per_model_frame_counts.values()
        ),
        "prediction_count_matches": frame_count == args.expected_prediction_count,
        "model_count_matches": model_count == args.expected_model_count,
        "per_sequence_row_count_matches": len(sequence_summary_rows)
        == args.expected_sequence_count * args.expected_model_count,
        "source_manifest_sequence_count_matches": source_manifest.get("available_labeled_test_sequence_count")
        == args.expected_sequence_count,
        "finite_source_metrics": finite_numbers(source_metrics),
        "finite_model_summary": finite_numbers(model_rows),
        "finite_frame_metrics": finite_numbers(frame_rows),
        "finite_sequence_summary": finite_numbers(sequence_summary_rows),
        "finite_ranking_diagnostics": finite_numbers(ranking_diagnostics),
        "no_synthetic_rows_in_core_surface": synthetic_core_rows == 0,
    }
    validation_passed = all(checks.values())

    copied_artifacts = copy_artifacts(source_dir, output_dir) if args.copy_artifacts else {}

    topcow_metrics = {
        key: value for key, value in contract_metrics.items() if key.startswith("topcow_")
    }
    metrics = {
        "dias_contract_benchmark_passed": 1.0 if validation_passed else 0.0,
        "dias_contract_surface_role_core": 1.0 if surface.get("role") == "core" else 0.0,
        "dias_contract_sequence_count": float(sequence_count),
        "dias_contract_model_count": float(model_count),
        "dias_contract_frame_count_per_model": float(frame_count_per_model),
        "dias_contract_prediction_count": float(frame_count),
        "dias_contract_per_sequence_row_count": float(len(sequence_summary_rows)),
        "dias_contract_leaderboard_row_count": float(len(leaderboard)),
        "dias_contract_synthetic_core_row_count": float(synthetic_core_rows),
        "dias_contract_finite_metric_check": 1.0 if finite_numbers(source_metrics) else 0.0,
        "dias_contract_aggregate_spearman_synthetic_vs_dias": float(
            ranking_diagnostics["aggregate_spearman_s2c_synthetic_vs_dias_multisequence_mean_dice"]
        ),
        "dias_contract_aggregate_kendall_synthetic_vs_dias": float(
            ranking_diagnostics["aggregate_kendall_s2c_synthetic_vs_dias_multisequence_mean_dice"]
        ),
        "dias_contract_sequence_spearman_bootstrap_mean": float(
            ranking_diagnostics["sequence_spearman_bootstrap"]["mean"]
        ),
        "dias_contract_sequence_spearman_ci95_low": float(
            ranking_diagnostics["sequence_spearman_bootstrap"]["ci95_low"]
        ),
        "dias_contract_sequence_spearman_ci95_high": float(
            ranking_diagnostics["sequence_spearman_bootstrap"]["ci95_high"]
        ),
    }
    metrics.update({key: float(value) for key, value in source_metrics.items() if is_number(value)})
    metrics.update({key: float(value) for key, value in topcow_metrics.items() if is_number(value)})

    benchmark_index = {
        "benchmark_id": CONTRACT_ID,
        "run_id": RUN_ID,
        "surface_id": SURFACE_ID,
        "surface_role": surface.get("role"),
        "source_run_id": SOURCE_RUN_ID,
        "source_dir": str(source_dir),
        "sequence_count": sequence_count,
        "frame_count_per_model": frame_count_per_model,
        "prediction_count": frame_count,
        "model_count": model_count,
        "validation_passed": validation_passed,
        "claim_boundary": "Contract-owned DIAS real-data full-test benchmark surface; preserves discordant rank-transfer evidence.",
        "primary_outputs": [
            "manifest.json",
            "sequences.json",
            "per_frame_metrics.json",
            "per_sequence_summary.json",
            "model_summary.json",
            "leaderboard.json",
            "ranking_diagnostics.json",
            "metrics_summary.json",
            "validation_summary.md",
        ],
    }

    benchmark_manifest = {
        "benchmark_id": CONTRACT_ID,
        "run_id": RUN_ID,
        "surface": surface,
        "source_run_id": SOURCE_RUN_ID,
        "source_manifest": source_manifest,
        "source_dir": str(source_dir),
        "expected_counts": {
            "sequence_count": args.expected_sequence_count,
            "frame_count_per_model": args.expected_frame_count_per_model,
            "prediction_count": args.expected_prediction_count,
            "model_count": args.expected_model_count,
        },
        "observed_counts": {
            "sequence_count": sequence_count,
            "frame_count_per_model": frame_count_per_model,
            "prediction_count": frame_count,
            "model_count": model_count,
            "per_sequence_summary_rows": len(sequence_summary_rows),
        },
        "checks": checks,
        "validation_passed": validation_passed,
        "copied_artifacts": copied_artifacts,
        "command": " ".join(
            [
                "python3",
                "benchmark/run_dias_contract_full_test.py",
                "--contract",
                str(args.contract),
                "--source-dir",
                str(source_dir),
                "--output-dir",
                str(output_dir),
                "--copy-artifacts" if args.copy_artifacts else "",
            ]
        ).strip(),
    }

    write_json(output_dir / "benchmark_index.json", benchmark_index)
    write_json(output_dir / "manifest.json", benchmark_manifest)
    write_json(output_dir / "sequences.json", {"rows": sequence_index})
    write_csv(output_dir / "sequences.csv", sequence_index)
    write_json(output_dir / "per_frame_metrics.json", {"rows": benchmark_frames})
    write_csv(output_dir / "per_frame_metrics.csv", benchmark_frames)
    write_json(output_dir / "per_sequence_summary.json", {"rows": benchmark_sequences})
    write_csv(output_dir / "per_sequence_summary.csv", benchmark_sequences)
    write_json(output_dir / "model_summary.json", {"rows": model_rows})
    write_csv(output_dir / "model_summary.csv", model_rows)
    write_json(output_dir / "leaderboard.json", {"rows": leaderboard})
    write_csv(output_dir / "leaderboard.csv", leaderboard)
    write_json(output_dir / "ranking_diagnostics.json", ranking_diagnostics)
    write_json(output_dir / "metrics_summary.json", metrics)
    write_validation_summary(output_dir / "validation_summary.md", checks, leaderboard, metrics, validation_passed)
    write_run_note(args, validation_passed)

    return {"ok": validation_passed, "output_dir": str(output_dir), "metrics": metrics}


def write_validation_summary(
    path: Path,
    checks: dict[str, bool],
    leaderboard: list[dict[str, Any]],
    metrics: dict[str, float],
    validation_passed: bool,
) -> None:
    lines = [
        "# DIAS Contract Full-Test Validation",
        "",
        f"- run_id: `{RUN_ID}`",
        f"- contract_id: `{CONTRACT_ID}`",
        f"- surface_id: `{SURFACE_ID}`",
        f"- validation_passed: `{validation_passed}`",
        f"- sequences: `{int(metrics['dias_contract_sequence_count'])}`",
        f"- frames_per_model: `{int(metrics['dias_contract_frame_count_per_model'])}`",
        f"- predictions: `{int(metrics['dias_contract_prediction_count'])}`",
        "",
        "## Checks",
        "",
    ]
    for key in sorted(checks):
        lines.append(f"- {key}: `{checks[key]}`")
    lines.extend(
        [
            "",
            "## Leaderboard",
            "",
        ]
    )
    for row in leaderboard:
        lines.append(
            "- rank {rank}: `{model_id}` Dice `{dice:.6f}`, clDice `{cldice:.6f}`".format(
                rank=row["rank"],
                model_id=row["model_id"],
                dice=row["dias_multisequence_mean_dice"],
                cldice=row["dias_multisequence_mean_cldice"],
            )
        )
    lines.extend(
        [
            "",
            "## Rank-Transfer Diagnostic",
            "",
            "- aggregate Spearman synthetic-vs-DIAS: `{:.6f}`".format(
                metrics["dias_contract_aggregate_spearman_synthetic_vs_dias"]
            ),
            "- aggregate Kendall synthetic-vs-DIAS: `{:.6f}`".format(
                metrics["dias_contract_aggregate_kendall_synthetic_vs_dias"]
            ),
            "- sequence bootstrap Spearman mean: `{:.6f}`".format(
                metrics["dias_contract_sequence_spearman_bootstrap_mean"]
            ),
            "- sequence bootstrap Spearman 95% CI: `[{:.6f}, {:.6f}]`".format(
                metrics["dias_contract_sequence_spearman_ci95_low"],
                metrics["dias_contract_sequence_spearman_ci95_high"],
            ),
            "",
            "## Claim Boundary",
            "",
            "This is a contract-owned DIAS real-data benchmark surface built from audited frozen-model outputs. It preserves the discordant DIAS rank-transfer result and does not claim positive construct validity or clinical validation.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def write_run_note(args: argparse.Namespace, validation_passed: bool) -> None:
    run_dir = args.output_dir.parent
    run_dir.mkdir(parents=True, exist_ok=True)
    command = " ".join(
        [
            "python3",
            "benchmark/run_dias_contract_full_test.py",
            "--contract",
            str(args.contract),
            "--source-dir",
            str(args.source_dir),
            "--output-dir",
            str(args.output_dir),
            "--copy-artifacts" if args.copy_artifacts else "",
        ]
    ).strip()
    run_note = f"""# {RUN_ID}

## Purpose

Materialize the audited S3b DIAS full-test split result as a contract-owned AngioStress v0.1 real-data benchmark surface.

## Command

```bash
{command}
```

## Source

- source run: `{SOURCE_RUN_ID}`
- source dir: `{args.source_dir}`
- contract: `{args.contract}`

## Output

- output dir: `{args.output_dir}`
- validation passed: `{validation_passed}`

## Boundary

This run imports and validates an existing DIAS full-test result. It is benchmark materialization and provenance repair, not new frozen-model inference and not a positive construct-validity claim.
"""
    (run_dir / "RUN.md").write_text(run_note)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("benchmark/contracts/angiostress_v0_1_real_data.json"),
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("experiments/analysis/s3b-dias-full-test-split-ranking/outputs"),
    )
    parser.add_argument(
        "--contract-validation-metrics",
        type=Path,
        default=Path("experiments/main/run-real-data-first-benchmark-contract/outputs/metrics_summary.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/main/run-dias-contract-full-test-v0/outputs"),
    )
    parser.add_argument("--expected-sequence-count", type=int, default=20)
    parser.add_argument("--expected-frame-count-per-model", type=int, default=115)
    parser.add_argument("--expected-prediction-count", type=int, default=345)
    parser.add_argument("--expected-model-count", type=int, default=3)
    parser.add_argument("--copy-artifacts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_outputs(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
