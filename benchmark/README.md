# Benchmark Package

This directory contains the runnable AngioStress v0.1 benchmark contract and validation tools.

## Core Surfaces

| Surface | Role | Output directory | Primary result files |
|---|---|---|---|
| DIAS sequence segmentation | core real-data surface | `experiments/main/run-dias-contract-full-test-v0/outputs/` | `manifest.json`, `per_frame_metrics.json`, `per_sequence_summary.json`, `model_summary.json`, `leaderboard.json`, `ranking_diagnostics.json` |
| CathAction human segmentation full nonempty tier | core real-data surface | `experiments/main/run-cathaction-real-scaleup-v0/outputs/full_nonempty_5225/` | `manifest.json`, `samples.json`, `per_pair_metrics.json`, `model_summary.json`, `leaderboard.json`, `stability_summary.json` |
| TopCoW-derived synthetic fixture | auxiliary surface | `experiments/main/run-angiostress-s2c-third-frozen-model-panel-extension/outputs/` | synthetic stressor/regression fixture outputs |

## Commands

Validate the contract:

```bash
python3 benchmark/validate_contract.py \
  --contract benchmark/contracts/angiostress_v0_1_real_data.json
```

Materialize the DIAS benchmark-owned output from the audited DIAS result:

```bash
python3 benchmark/run_dias_contract_full_test.py \
  --contract benchmark/contracts/angiostress_v0_1_real_data.json \
  --source-dir experiments/analysis/s3b-dias-full-test-split-ranking/outputs \
  --output-dir experiments/main/run-dias-contract-full-test-v0/outputs \
  --copy-artifacts
```

Materialize the full CathAction benchmark-owned output from the audited full nonempty tier:

```bash
python3 benchmark/run_cathaction_full_tier.py
```

Materialize the older quick CathAction subset output, useful only as a smoke-scale compatibility check:

```bash
python3 benchmark/run_cathaction_contract_subset.py \
  --contract benchmark/contracts/angiostress_v0_1_real_data.json \
  --source-dir experiments/analysis/s3f-cathaction-human-segmentation-subset-ranking/outputs \
  --output-dir experiments/main/run-cathaction-contract-subset-v0/outputs \
  --copy-artifacts
```

Audit the complete release package:

```bash
python3 benchmark/run_release_audit.py
```

Stage the public upload package:

```bash
python3 benchmark/stage_public_release.py
```

## Public Artifact Rule

Public benchmark artifacts should include code, contracts, manifests, metrics, derived predictions/overlays, and provenance. They should not include LaTeX source, manuscript PDFs, reviewer comments, or private paper-build material.
