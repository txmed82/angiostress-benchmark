#!/usr/bin/env python3
"""Materialize the full CathAction nonempty-pair benchmark tier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_cathaction_contract_subset as cathaction_runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("benchmark/contracts/angiostress_v0_1_real_data.json"))
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("experiments/main/run-cathaction-real-scaleup-v0/outputs/full_nonempty_5225"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/main/run-cathaction-real-scaleup-v0/outputs/full_nonempty_5225"),
    )
    parser.add_argument("--copy-artifacts", action="store_true")
    args = parser.parse_args()

    cathaction_runner.RUN_ID = "run-cathaction-real-scaleup-v0"
    cathaction_runner.SPLIT_NAME = "human_dataset_train_full_nonempty"
    run_args = argparse.Namespace(
        contract=args.contract,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        expected_sample_count=5225,
        expected_model_count=3,
        expected_nonempty_pair_universe=5225,
        copy_artifacts=args.copy_artifacts,
    )
    result = cathaction_runner.build_outputs(run_args)
    print(f"full_tier_validation_passed={int(result['ok'])}")
    print(f"output_dir={args.output_dir}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
