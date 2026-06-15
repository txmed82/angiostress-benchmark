# DIAS Contract Full-Test Validation

- run_id: `run-dias-contract-full-test-v0`
- contract_id: `angiostress-v0.1-real-data`
- surface_id: `dias_sequence_segmentation`
- validation_passed: `True`
- sequences: `20`
- frames_per_model: `115`
- predictions: `345`

## Checks

- finite_frame_metrics: `True`
- finite_model_summary: `True`
- finite_ranking_diagnostics: `True`
- finite_sequence_summary: `True`
- finite_source_metrics: `True`
- frame_count_per_model_matches: `True`
- model_count_matches: `True`
- no_synthetic_rows_in_core_surface: `True`
- per_sequence_row_count_matches: `True`
- prediction_count_matches: `True`
- sequence_count_matches: `True`
- source_manifest_sequence_count_matches: `True`
- surface_role_is_core: `True`

## Leaderboard

- rank 1: `medsam_vit_b` Dice `0.295327`, clDice `0.271700`
- rank 2: `sam_vit_l` Dice `0.262846`, clDice `0.269089`
- rank 3: `sam_vit_b` Dice `0.240471`, clDice `0.239050`

## Rank-Transfer Diagnostic

- aggregate Spearman synthetic-vs-DIAS: `-0.500000`
- aggregate Kendall synthetic-vs-DIAS: `-0.333333`
- sequence bootstrap Spearman mean: `-0.425000`
- sequence bootstrap Spearman 95% CI: `[-0.675000, -0.125000]`

## Claim Boundary

This is a contract-owned DIAS real-data benchmark surface built from audited frozen-model outputs. It preserves the discordant DIAS rank-transfer result and does not claim positive construct validity or clinical validation.
