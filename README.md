# AngioStress v0.1 Real-Data-First Benchmark

AngioStress is a deterministic benchmark package for stress-testing frozen endovascular perception models on digital subtraction angiography and endovascular segmentation surfaces.

The benchmark core is real data:

- DIAS sequence segmentation: 20 labeled test sequences, 115 evaluated frames per model, 345 prediction rows across three frozen models.
- CathAction human segmentation subset: 128 deterministic nonempty image-mask pairs, 384 prediction rows across three frozen models.

The TopCoW-derived synthetic projection fixture is auxiliary. It is used for controlled stressor and regression checks, not as the core benchmark surface.

## Frozen Model Panel

- SAM ViT-B (`sam_vit_b`)
- SAM ViT-L (`sam_vit_l`)
- MedSAM ViT-B (`medsam_vit_b`)

All model entries are treated as frozen, off-the-shelf evaluation targets. This repository does not train or fine-tune a new backbone.

## Main Benchmark Files

- Contract: `benchmark/contracts/angiostress_v0_1_real_data.json`
- Contract validator: `benchmark/validate_contract.py`
- DIAS benchmark runner: `benchmark/run_dias_contract_full_test.py`
- CathAction benchmark runner: `benchmark/run_cathaction_contract_subset.py`
- Release audit: `benchmark/run_release_audit.py`
- Public release staging/audit: `benchmark/stage_public_release.py`
- DIAS outputs: `experiments/main/run-dias-contract-full-test-v0/outputs/`
- CathAction outputs: `experiments/main/run-cathaction-contract-subset-v0/outputs/`

## Public Artifacts

- GitHub code and lightweight benchmark package: https://github.com/txmed82/angiostress-benchmark
- Hugging Face derived benchmark artifacts: https://huggingface.co/datasets/txmedai/angiostress-benchmark

## Validate The Package

Run the release audit from the repository root:

```bash
python3 benchmark/run_release_audit.py
```

Expected output:

- `experiments/main/run-real-benchmark-release-refresh-v0/outputs/release_audit.json`
- `experiments/main/run-real-benchmark-release-refresh-v0/outputs/release_manifest.json`
- `experiments/main/run-real-benchmark-release-refresh-v0/outputs/metrics_summary.json`
- `experiments/main/run-real-benchmark-release-refresh-v0/outputs/validation_summary.md`

The audit checks that DIAS and CathAction are both present as core real-data surfaces, that copied derived prediction artifacts exist, that metrics are finite, and that private manuscript/LaTeX paths are excluded from the release manifest.

Stage the public upload package:

```bash
python3 benchmark/stage_public_release.py
```

## Data-Source Boundary

DIAS and CathAction source datasets should be obtained from their original sources and licenses. This package records benchmark outputs, derived predictions/overlays, manifests, metrics, and provenance; it should not be treated as a redistribution of raw clinical source data.

## Claim Boundary

AngioStress v0.1 is a benchmark artifact and measurement package. The current DIAS rank-transfer diagnostic is discordant, and the CathAction subset shows partial rank agreement. These results should be reported as benchmark measurements, not as clinical validation, model improvement, or proof of positive synthetic-to-real transfer.
