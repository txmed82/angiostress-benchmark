# AngioStress Real-Data-First Contract Validation

- run_id: `run-real-data-first-benchmark-contract`
- contract_id: `angiostress-v0.1-real-data`
- validation_passed: `True`
- core_surfaces: `2`
- auxiliary_surfaces: `1`

## Surface Results

### dias_sequence_segmentation

- role: `core`
- dataset: `DIAS`
- ok: `True`
- path_checks: `7/7`
- json_checks: `7/7`
- finite_metric_checks: `5/5`

### cathaction_human_segmentation

- role: `core`
- dataset: `CathAction`
- ok: `True`
- path_checks: `4/4`
- json_checks: `9/9`
- finite_metric_checks: `5/5`

### topcow_synthetic_stressor_fixture

- role: `auxiliary`
- dataset: `TopCoW-derived synthetic projection`
- ok: `True`
- path_checks: `3/3`
- json_checks: `3/3`
- finite_metric_checks: `4/4`

## Claim Boundary

This contract defines a real-data-first benchmark surface and validates source/result availability. It is not a final construct-validity estimate, clinical validation, or model-improvement claim.
