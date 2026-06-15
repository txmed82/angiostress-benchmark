# CathAction Contract Benchmark Validation

- run_id: `run-cathaction-real-scaleup-v0`
- contract_id: `angiostress-v0.1-real-data`
- surface_id: `cathaction_human_segmentation`
- validation_passed: `True`
- sampled_pairs: `5225`
- predictions: `15675`
- nonempty_pair_universe: `5225`

## Checks

- finite_model_summary: `True`
- finite_pair_metrics: `True`
- finite_source_metrics: `True`
- model_count_matches: `True`
- no_synthetic_rows_in_core_surface: `True`
- nonempty_pair_universe_matches: `True`
- prediction_count_matches: `True`
- sample_count_matches: `True`
- source_manifest_sample_count_matches: `True`
- surface_role_is_core: `True`

## Leaderboard

- rank 1: `sam_vit_b` Dice `0.365830`, clDice `0.401462`
- rank 2: `sam_vit_l` Dice `0.357713`, clDice `0.384013`
- rank 3: `medsam_vit_b` Dice `0.116660`, clDice `0.108312`

## Claim Boundary

This is a contract-owned CathAction real-data benchmark output built from audited frozen-model outputs. It is a real benchmark surface for v0.1, not a clinical validation claim.
