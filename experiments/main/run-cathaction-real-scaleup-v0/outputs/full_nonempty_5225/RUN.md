# S3f CathAction Human Segmentation Subset Ranking

## Identity

- run_id: `s3f-cathaction-human-segmentation-subset-ranking`
- parent_run_id: `run-angiostress-s2c-third-frozen-model-panel-extension`
- route_decision: `decision-21f6663a`
- storage_decision: `decision-06a3b189`
- command: `experiments/analysis/s3f-cathaction-human-segmentation-subset-ranking/run_cathaction_human_segmentation_subset.py --zip-path tmp/cathaction_real_scaleup/segmentation_human_train.zip --out experiments/main/run-cathaction-real-scaleup-v0/outputs/full_nonempty_5225 --workspace-root /Users/colin/DeepScientist/quests/010/.ds/worktrees/run-cathaction-real-scaleup-v0 --device auto --sample-count 5225 --bootstrap-iterations 1000 --bootstrap-seed 20260615`
- device: `mps`

## Inputs

- CathAction retained zip: `gs://seldinger-datasets-raw/angiostress/cathaction/hf/segmentation_human_train.zip`
- Local zip path during run: `tmp/cathaction_real_scaleup/segmentation_human_train.zip`
- Local zip source sha256: `087c8f971e0455ad67d092a944df75ee7244cbead10e1091c26046ea271e2cf5`
- Sample count per model: `5225`
- Pair selection: deterministic evenly spaced index selection over nonempty human-mask pairs.
- Pair universe: `5225` nonempty pairs from `5283` image-mask pairs; `58` empty masks excluded before sampling.
- Model panel: SAM ViT-B, MedSAM ViT-B, and SAM ViT-L, all frozen.
- Bootstrap stability: `1000` deterministic resamples over the fixed sampled pair ids.

## Method

The runner imports the S2c frozen-panel helpers for checkpoint verification, SAM predictor construction, bbox prompting, Dice/clDice, and overlay rendering. It reads sampled JPG/PNG pairs directly from the zip into memory without extracting the archive. Prompts are CathAction mask-derived bounding boxes for measurement plumbing only. Stability is estimated by deterministic bootstrap resampling over the fixed sampled pair ids.

## Claim Boundary

This is a scaled CathAction human-segmentation subset check. It tests whether the frozen panel's CathAction ordering is stable enough to justify paper-outline repair and later construct-validity mapping. It does not estimate final DIAS + CathAction construct validity across all stressors or clinical accuracy.
