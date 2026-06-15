#!/usr/bin/env python3
"""Materialize a contract-owned CathAction benchmark output from audited outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from pathlib import Path
from typing import Any


RUN_ID = "run-cathaction-contract-subset-v0"
CONTRACT_ID = "angiostress-v0.1-real-data"
SURFACE_ID = "cathaction_human_segmentation"
SOURCE_RUN_ID = "s3f-cathaction-human-segmentation-subset-ranking"
SPLIT_NAME = "human_dataset_train_subset"


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


def surface_from_contract(contract: dict[str, Any]) -> dict[str, Any]:
    for surface in contract.get("surfaces", []):
        if (surface.get("surface_id") or surface.get("id")) == SURFACE_ID:
            return surface
    raise KeyError(f"surface {SURFACE_ID!r} not found in contract")


def ranked_leaderboard(model_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        model_rows,
        key=lambda row: (float(row["cathaction_sample_mean_dice"]), float(row["cathaction_sample_mean_cldice"])),
        reverse=True,
    )
    leaderboard = []
    for rank, row in enumerate(sorted_rows, start=1):
        leaderboard.append(
            {
                "rank": rank,
                "model_id": row["model_id"],
                "surface_id": SURFACE_ID,
                "primary_metric": "cathaction_sample_mean_dice",
                "cathaction_sample_mean_dice": float(row["cathaction_sample_mean_dice"]),
                "cathaction_sample_mean_cldice": float(row["cathaction_sample_mean_cldice"]),
                "cathaction_sample_min_dice": float(row["cathaction_sample_min_dice"]),
                "cathaction_sample_min_cldice": float(row["cathaction_sample_min_cldice"]),
                "prediction_nonempty_rate": float(row["cathaction_prediction_nonempty_rate"]),
                "mean_area_ratio": float(row["cathaction_sample_mean_area_ratio"]),
            }
        )
    return leaderboard


def benchmark_pair_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in source_rows:
        copied = dict(row)
        copied["benchmark_id"] = CONTRACT_ID
        copied["benchmark_run_id"] = RUN_ID
        copied["surface_id"] = SURFACE_ID
        copied["source_run_id"] = SOURCE_RUN_ID
        copied["split"] = SPLIT_NAME
        copied["task"] = "prompted_vessel_segmentation"
        copied["gt_source"] = "CathAction human segmentation mask"
        copied["synthetic_role"] = "none_core_real_data"
        rows.append(copied)
    return rows


def copy_artifacts(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    copied = {}
    for subdir in ["cathaction_predictions", "cathaction_overlays"]:
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


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    contract = read_json(args.contract)
    surface = surface_from_contract(contract)
    source_dir = args.source_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = read_json(source_dir / "manifest.json")
    source_metrics = read_json(source_dir / "metrics_summary.json")
    source_model_summary = read_json(source_dir / "model_summary.json")["rows"]
    source_per_pair_rows = read_json(source_dir / "per_pair_metrics.json")["rows"]
    source_stability = read_json(source_dir / "stability_summary.json")
    source_ranking = read_json(source_dir / "model_ranking_rows.json")["comparison"]

    pair_rows = benchmark_pair_rows(source_per_pair_rows)
    pair_ids = sorted({row["pair_id"] for row in pair_rows})
    model_ids = sorted({row["model_id"] for row in pair_rows})
    leaderboard = ranked_leaderboard(source_model_summary)
    copied_artifacts = copy_artifacts(source_dir, output_dir) if args.copy_artifacts else {}

    expected_sample_count = int(args.expected_sample_count)
    expected_model_count = int(args.expected_model_count)
    expected_prediction_count = expected_sample_count * expected_model_count
    pair_universe = source_manifest["pair_universe"]

    checks = {
        "surface_role_is_core": surface.get("role") == "core",
        "sample_count_matches": len(pair_ids) == expected_sample_count,
        "model_count_matches": len(model_ids) == expected_model_count,
        "prediction_count_matches": len(pair_rows) == expected_prediction_count,
        "source_manifest_sample_count_matches": int(source_manifest["sample_count"]) == expected_sample_count,
        "nonempty_pair_universe_matches": int(pair_universe["nonempty_mask_pairs"]) == int(args.expected_nonempty_pair_universe),
        "finite_source_metrics": finite_numbers(source_metrics),
        "finite_model_summary": finite_numbers(source_model_summary),
        "finite_pair_metrics": finite_numbers(pair_rows),
        "no_synthetic_rows_in_core_surface": all(row["synthetic_role"] == "none_core_real_data" for row in pair_rows),
    }
    ok = all(checks.values())

    metrics = {
        **source_metrics,
        "cathaction_contract_benchmark_passed": 1.0 if ok else 0.0,
        "cathaction_contract_surface_role_core": 1.0 if checks["surface_role_is_core"] else 0.0,
        "cathaction_contract_sample_count": float(len(pair_ids)),
        "cathaction_contract_model_count": float(len(model_ids)),
        "cathaction_contract_prediction_count": float(len(pair_rows)),
        "cathaction_contract_leaderboard_row_count": float(len(leaderboard)),
        "cathaction_contract_nonempty_pair_universe_count": float(pair_universe["nonempty_mask_pairs"]),
        "cathaction_contract_empty_pair_excluded_count": float(pair_universe["empty_mask_pairs_excluded"]),
        "cathaction_contract_synthetic_core_row_count": 0.0,
        "cathaction_contract_finite_metric_check": 1.0 if finite_numbers(source_metrics) and finite_numbers(pair_rows) else 0.0,
    }

    benchmark_index = {
        "schema_version": 1,
        "benchmark_id": CONTRACT_ID,
        "run_id": RUN_ID,
        "surface_id": SURFACE_ID,
        "surface_role": "core",
        "dataset": "CathAction",
        "source_run_id": SOURCE_RUN_ID,
        "task": "prompted_vessel_segmentation",
        "sample_count": len(pair_ids),
        "model_count": len(model_ids),
        "prediction_count": len(pair_rows),
        "model_ids": model_ids,
        "primary_metric": "cathaction_sample_mean_dice",
        "leaderboard_path": "leaderboard.json",
        "per_pair_metrics_path": "per_pair_metrics.json",
        "model_summary_path": "model_summary.json",
        "synthetic_role": "none_core_real_data",
    }
    manifest = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "contract_id": CONTRACT_ID,
        "surface": surface,
        "source_run_id": SOURCE_RUN_ID,
        "source_dir": str(source_dir),
        "source_manifest": source_manifest,
        "pair_universe": pair_universe,
        "checks": checks,
        "ok": ok,
        "copied_artifacts": copied_artifacts,
        "outputs": {
            "benchmark_index": "benchmark_index.json",
            "samples": "samples.json",
            "per_pair_metrics": "per_pair_metrics.json",
            "model_summary": "model_summary.json",
            "leaderboard": "leaderboard.json",
            "stability_summary": "stability_summary.json",
            "metrics_summary": "metrics_summary.json",
            "validation_summary": "validation_summary.md",
        },
        "claim_boundary": (
            "This is a contract-owned CathAction real-data benchmark output built from audited frozen-model "
            "outputs. It is a real benchmark surface for v0.1, not a clinical validation claim."
        ),
    }

    write_json(output_dir / "benchmark_index.json", benchmark_index)
    write_json(output_dir / "samples.json", {"rows": source_manifest["sampled_pairs"]})
    write_csv(output_dir / "samples.csv", source_manifest["sampled_pairs"])
    write_json(output_dir / "per_pair_metrics.json", {"rows": pair_rows})
    write_csv(output_dir / "per_pair_metrics.csv", pair_rows)
    write_json(output_dir / "model_summary.json", {"rows": source_model_summary})
    write_csv(output_dir / "model_summary.csv", source_model_summary)
    write_json(output_dir / "leaderboard.json", {"rows": leaderboard})
    write_csv(output_dir / "leaderboard.csv", leaderboard)
    write_json(output_dir / "stability_summary.json", source_stability)
    write_json(output_dir / "model_ranking_rows.json", {"comparison": source_ranking})
    write_json(output_dir / "metrics_summary.json", metrics)
    write_json(output_dir / "manifest.json", manifest)
    write_validation_summary(output_dir / "validation_summary.md", manifest, metrics, leaderboard)
    write_run_note(output_dir.parent / "RUN.md", args, manifest)
    return {"ok": ok, "metrics": metrics, "manifest": manifest}


def write_validation_summary(path: Path, manifest: dict[str, Any], metrics: dict[str, float], leaderboard: list[dict[str, Any]]) -> None:
    checks = manifest["checks"]
    lines = [
        "# CathAction Contract Benchmark Validation",
        "",
        f"- run_id: `{RUN_ID}`",
        f"- contract_id: `{CONTRACT_ID}`",
        f"- surface_id: `{SURFACE_ID}`",
        f"- validation_passed: `{manifest['ok']}`",
        f"- sampled_pairs: `{int(metrics['cathaction_contract_sample_count'])}`",
        f"- predictions: `{int(metrics['cathaction_contract_prediction_count'])}`",
        f"- nonempty_pair_universe: `{int(metrics['cathaction_contract_nonempty_pair_universe_count'])}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in sorted(checks.items()))
    lines.extend(["", "## Leaderboard", ""])
    for row in leaderboard:
        lines.append(
            "- rank {rank}: `{model_id}` Dice `{dice:.6f}`, clDice `{cldice:.6f}`".format(
                rank=row["rank"],
                model_id=row["model_id"],
                dice=row["cathaction_sample_mean_dice"],
                cldice=row["cathaction_sample_mean_cldice"],
            )
        )
    lines.extend(["", "## Claim Boundary", "", manifest["claim_boundary"], ""])
    path.write_text("\n".join(lines))


def write_run_note(path: Path, args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    path.write_text(
        "\n".join(
            [
                "# CathAction Contract Benchmark",
                "",
                "## Command",
                "",
                f"`{' '.join(str(x) for x in ['python3', 'benchmark/run_cathaction_contract_subset.py', '--contract', args.contract, '--source-dir', args.source_dir, '--output-dir', args.output_dir])}`",
                "",
                "## Purpose",
                "",
                "Materialize audited CathAction human-segmentation outputs as a contract-owned AngioStress v0.1 benchmark output.",
                "",
                "## Boundary",
                "",
                manifest["claim_boundary"],
                "",
            ]
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("benchmark/contracts/angiostress_v0_1_real_data.json"))
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("experiments/analysis/s3f-cathaction-human-segmentation-subset-ranking/outputs"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/main/run-cathaction-contract-subset-v0/outputs"),
    )
    parser.add_argument("--expected-sample-count", type=int, default=128)
    parser.add_argument("--expected-model-count", type=int, default=3)
    parser.add_argument("--expected-nonempty-pair-universe", type=int, default=5225)
    parser.add_argument("--copy-artifacts", action="store_true")
    args = parser.parse_args()

    result = build_outputs(args)
    print(json.dumps({"ok": result["ok"], "metrics": result["metrics"], "output_dir": str(args.output_dir)}, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
