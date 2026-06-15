#!/usr/bin/env python3
"""Stage public AngioStress benchmark artifacts for GitHub and Hugging Face."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("experiments/main/run-public-benchmark-artifact-update-v0/outputs")
DEFAULT_RELEASE_DIR = Path("experiments/main/run-real-benchmark-release-refresh-v0/outputs")
DEFAULT_STAGE_ROOT = Path("tmp/public_upload/angiostress-v0.1")

PRIVATE_PATTERNS = [
    "paper/",
    "manuscript.tex",
    "manuscript.pdf",
    "latex",
    "comments",
    "reviewer",
    "response_letter",
]

DERIVED_DIR_MARKERS = [
    "outputs/predictions",
    "outputs/cathaction_predictions",
    "outputs/cathaction_overlays",
    "cathaction_predictions",
    "cathaction_overlays",
]

ARCHIVE_NAMES = {
    "cathaction_predictions": "cathaction_full_nonempty_5225_predictions.tar",
    "cathaction_overlays": "cathaction_full_nonempty_5225_overlays.tar",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def safe_public_path(rel_path: str) -> bool:
    lowered = rel_path.lower()
    return not any(pattern in lowered for pattern in PRIVATE_PATTERNS)


def is_derived_dir(rel_path: str) -> bool:
    return any(marker in rel_path for marker in DERIVED_DIR_MARKERS)


def github_public_file(rel_path: str) -> bool:
    if is_derived_dir(rel_path):
        return False
    return (
        rel_path == "README.md"
        or rel_path.startswith("benchmark/")
        or rel_path.endswith(".json")
        or rel_path.endswith(".md")
    )


def copy_path(root: Path, rel_path: str, destination_root: Path) -> dict[str, Any]:
    src = root / rel_path
    dst = destination_root / rel_path
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    else:
        return {"path": rel_path, "copied": False, "reason": "missing"}
    return {"path": rel_path, "copied": True, "kind": "dir" if src.is_dir() else "file"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_name_for(rel_path: str) -> str:
    name = Path(rel_path).name
    return ARCHIVE_NAMES.get(name, rel_path.replace("/", "__") + ".tar")


def archive_derived_dir(root: Path, rel_path: str, destination_root: Path) -> dict[str, Any]:
    src = root / rel_path
    archive_dir = destination_root / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / archive_name_for(rel_path)

    files = [p for p in src.rglob("*") if p.is_file()]
    with tarfile.open(archive_path, "w") as tar:
        tar.add(src, arcname=rel_path)

    return {
        "path": rel_path,
        "copied": True,
        "kind": "archive",
        "archive_path": str(archive_path.relative_to(destination_root)),
        "source_file_count": len(files),
        "source_size_bytes": sum(p.stat().st_size for p in files),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": sha256_file(archive_path),
    }


def file_inventory(root: Path) -> dict[str, Any]:
    files = [p for p in root.rglob("*") if p.is_file()]
    rel_paths = sorted(str(p.relative_to(root)) for p in files)
    return {
        "file_count": len(files),
        "size_bytes": sum(p.stat().st_size for p in files),
        "paths": rel_paths,
        "private_hits": [p for p in rel_paths if not safe_public_path(p)],
    }


def write_github_artifact_note(path: Path, github_repo: str, hf_dataset: str) -> None:
    text = f"""# Public Artifacts

This repository contains the lightweight AngioStress v0.1 benchmark code,
contracts, manifests, metrics, and validation outputs.

- GitHub code repository: https://github.com/{github_repo}
- Hugging Face dataset artifact: https://huggingface.co/datasets/{hf_dataset}

The Hugging Face dataset contains browseable metadata and archive payloads for
the larger derived prediction and overlay artifacts staged from the release
manifest. Raw DIAS and CathAction source data remain governed by their original
sources and are not redistributed here.
"""
    (path / "PUBLIC_ARTIFACTS.md").write_text(text)


def write_archive_manifest(path: Path, archive_entries: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    write_json(
        path / "archives" / "derived_artifact_manifest.json",
        {
            "schema_version": 1,
            "format": "uncompressed_tar_archives",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "release_id": manifest.get("release_id"),
            "raw_data_boundary": manifest.get("raw_data_boundary"),
            "extraction": (
                "Extract each archive at the repository root to restore the "
                "source-relative derived benchmark output directories."
            ),
            "archives": archive_entries,
        },
    )


def write_hf_dataset_card(
    path: Path,
    github_repo: str,
    hf_dataset: str,
    manifest: dict[str, Any],
    archive_entries: list[dict[str, Any]],
) -> None:
    metrics = read_json(DEFAULT_RELEASE_DIR / "metrics_summary.json")
    archive_lines = "\n".join(
        f"- `{entry['archive_path']}`: {entry['source_file_count']} files, sha256 `{entry['archive_sha256']}`"
        for entry in archive_entries
    )
    text = f"""---
pretty_name: AngioStress v0.1 Real-Data Benchmark Artifacts
tags:
- medical-imaging
- angiography
- benchmark
- segmentation
license: other
---

# AngioStress v0.1 Real-Data Benchmark Artifacts

This dataset repository contains derived benchmark artifacts for AngioStress
v0.1. The core benchmark surfaces are DIAS and CathAction real angiography
surfaces; the TopCoW-derived synthetic projection is an auxiliary regression
fixture only.

## Public Links

- GitHub code repository: https://github.com/{github_repo}
- Hugging Face dataset artifact: https://huggingface.co/datasets/{hf_dataset}

## Release Boundary

{manifest.get("release_policy")}

{manifest.get("raw_data_boundary")}

{manifest.get("claim_boundary")}

## Audit Summary

- Real core surfaces: {int(metrics["release_real_core_surface_count"])}
- Real prediction rows: {int(metrics["release_total_real_prediction_rows"])}
- CathAction full-tier pairs: {int(metrics["release_cathaction_sample_count"])}
- Derived prediction files: {int(metrics["release_derived_prediction_file_count"])}
- Derived overlay files: {int(metrics["release_derived_overlay_file_count"])}
- Private manifest hits: {int(metrics["release_private_manifest_hit_count"])}

## Large Derived Artifacts

Large prediction and overlay directories are stored as tar archives so the
benchmark remains practical to download from the Hub without expanding tens of
thousands of small files in the repository tree.

{archive_lines}
"""
    (path / "README.md").write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--stage-root", type=Path, default=DEFAULT_STAGE_ROOT)
    parser.add_argument("--github-repo", default="txmed82/angiostress-benchmark")
    parser.add_argument("--hf-dataset", default="txmedai/angiostress-benchmark")
    args = parser.parse_args()

    root = args.root
    release_manifest_path = root / args.release_dir / "release_manifest.json"
    manifest = read_json(release_manifest_path)
    public_files = manifest["public_files"]

    github_stage = root / args.stage_root / "github"
    hf_stage = root / args.stage_root / "hf_dataset"
    for stage_dir in [github_stage, hf_stage]:
        if stage_dir.exists():
            shutil.rmtree(stage_dir)
        stage_dir.mkdir(parents=True)

    missing = []
    github_copies = []
    hf_copies = []
    hf_archives = []
    for rel_path in public_files:
        if not safe_public_path(rel_path):
            continue
        src = root / rel_path
        if not src.exists():
            missing.append(rel_path)
            continue
        if is_derived_dir(rel_path) and src.is_dir():
            archive_entry = archive_derived_dir(root, rel_path, hf_stage)
            hf_copies.append(archive_entry)
            hf_archives.append(archive_entry)
        else:
            hf_copies.append(copy_path(root, rel_path, hf_stage))
        if github_public_file(rel_path):
            github_copies.append(copy_path(root, rel_path, github_stage))

    write_github_artifact_note(github_stage, args.github_repo, args.hf_dataset)
    write_archive_manifest(hf_stage, hf_archives, manifest)
    write_hf_dataset_card(hf_stage, args.github_repo, args.hf_dataset, manifest, hf_archives)

    github_inventory = file_inventory(github_stage)
    hf_inventory = file_inventory(hf_stage)
    checks = {
        "release_manifest_present": release_manifest_path.exists(),
        "manifest_private_hits_zero": not [p for p in public_files if not safe_public_path(p)],
        "all_manifest_entries_present": not missing,
        "github_private_hits_zero": not github_inventory["private_hits"],
        "hf_private_hits_zero": not hf_inventory["private_hits"],
        "github_excludes_large_derived_dirs": not any(is_derived_dir(p) for p in github_inventory["paths"]),
        "hf_archives_large_derived_dirs": len(hf_archives) >= 3
        and all(entry["archive_size_bytes"] > 0 for entry in hf_archives)
        and any(entry["path"].endswith("/cathaction_predictions") for entry in hf_archives)
        and any(entry["path"].endswith("/cathaction_overlays") for entry in hf_archives),
        "hf_does_not_expand_large_derived_dirs": not any(is_derived_dir(p) for p in hf_inventory["paths"]),
    }
    passed = all(checks.values())

    audit = {
        "schema_version": 1,
        "run_id": "run-public-benchmark-artifact-update-v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "github_repo": args.github_repo,
        "hf_dataset": args.hf_dataset,
        "github_stage_dir": str(github_stage),
        "hf_stage_dir": str(hf_stage),
        "release_manifest_path": str(release_manifest_path),
        "manifest_public_entry_count": len(public_files),
        "missing_manifest_entries": missing,
        "checks": checks,
        "passed": passed,
        "github_inventory": github_inventory,
        "hf_inventory": hf_inventory,
        "hf_archive_entries": hf_archives,
        "github_copied_entries": github_copies,
        "hf_copied_entries": hf_copies,
        "release_boundary": {
            "release_policy": manifest.get("release_policy"),
            "raw_data_boundary": manifest.get("raw_data_boundary"),
            "claim_boundary": manifest.get("claim_boundary"),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "public_upload_audit.json", audit)
    write_json(
        args.output_dir / "metrics_summary.json",
        {
            "public_upload_audit_passed": 1.0 if passed else 0.0,
            "public_upload_manifest_entry_count": float(len(public_files)),
            "public_upload_github_file_count": float(github_inventory["file_count"]),
            "public_upload_hf_file_count": float(hf_inventory["file_count"]),
            "public_upload_github_private_hit_count": float(len(github_inventory["private_hits"])),
            "public_upload_hf_private_hit_count": float(len(hf_inventory["private_hits"])),
            "public_upload_missing_manifest_entry_count": float(len(missing)),
        },
    )
    (args.output_dir / "validation_summary.md").write_text(
        "\n".join(
            [
                "# Public Upload Audit",
                "",
                f"- passed: `{passed}`",
                f"- github_repo: `https://github.com/{args.github_repo}`",
                f"- hf_dataset: `https://huggingface.co/datasets/{args.hf_dataset}`",
                f"- github_file_count: `{github_inventory['file_count']}`",
                f"- hf_file_count: `{hf_inventory['file_count']}`",
                f"- missing_manifest_entries: `{len(missing)}`",
                f"- github_private_hits: `{len(github_inventory['private_hits'])}`",
                f"- hf_private_hits: `{len(hf_inventory['private_hits'])}`",
                "",
            ]
        )
    )

    print(json.dumps({"passed": passed, "github_stage": str(github_stage), "hf_stage": str(hf_stage)}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
