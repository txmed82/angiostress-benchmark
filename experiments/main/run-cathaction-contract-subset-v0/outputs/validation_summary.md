# CathAction Contract Subset Validation

- run_id: `run-cathaction-contract-subset-v0`
- contract_id: `angiostress-v0.1-real-data`
- surface_id: `cathaction_human_segmentation`
- validation_passed: `True`
- sampled_pairs: `128`
- predictions: `384`
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

- rank 1: `sam_vit_b` Dice `0.364747`, clDice `0.402258`
- rank 2: `sam_vit_l` Dice `0.346362`, clDice `0.364272`
- rank 3: `medsam_vit_b` Dice `0.099729`, clDice `0.087055`

## Claim Boundary

This is a contract-owned CathAction real-data benchmark subset built from audited frozen-model outputs. It is a real benchmark surface for v0.1, not a final powered estimate over all CathAction or DIAS data and not a clinical validation claim.
