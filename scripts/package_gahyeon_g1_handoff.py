#!/usr/bin/env python3
"""Build a deterministic, self-verifying G1 modeling handoff archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from verify_gahyeon_g1_authoring_work_order import verify as verify_work_order
from verify_gahyeon_modeling_input import verify as verify_modeling


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts/gahyeon-ch/modeling-input.json"
DEFAULT_OUTPUT = ROOT / "artifacts/gahyeon-g1-handoff.zip"
FIXED_TIMESTAMP = (2026, 8, 12, 0, 0, 0)
WORKSTATION_TOOLS = {
    "tools/build-g1-scene-plan.py": ROOT / "scripts/build_gahyeon_blender_g1_scene_plan.py",
    "tools/blender-bootstrap-g1.py": ROOT / "scripts/blender_bootstrap_gahyeon_g1.py",
    "tools/blender-import-g1-base.py": ROOT / "scripts/blender_import_gahyeon_g1_base.py",
    "tools/blender-render-g1-evidence.py": ROOT / "scripts/blender_render_gahyeon_g1_evidence.py",
    "tools/package-g1-submission.py": ROOT / "scripts/package_gahyeon_g1_submission.py",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def build_reference_map(references: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=("index", "classification", "packagedPath", "sourceFile", "bytes", "sha256"),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(references)
    return stream.getvalue().encode("utf-8-sig")


def build_readme(modeling: dict, references: list[dict]) -> bytes:
    canonical = sum(item["classification"] == "canonical" for item in references)
    supporting = len(references) - canonical
    content = f"""# Gahyeon G1 modeling handoff

Character: `{modeling['characterId']}`

This archive is a self-verifying input package for G1 model-sheet authoring.

- `references/canonical/`: {canonical} identity/geometry-authoritative user originals
- `references/supporting/`: {supporting} supporting-only user originals
- `reference-map.csv`: portable filename to original filename/checksum mapping
- `modeling-input.json`: geometry anchors and authority rules
- `g1-authoring-work-order.json`: required output/evidence checklist
- `g1-review-template.json`: empty review record; do not pre-approve it
- `g1-drafts/`: non-authoritative generated drafts; never use as identity truth
- `tools/build-g1-scene-plan.py`: standalone integrity check and Blender scene-plan builder
- `tools/blender-bootstrap-g1.py`: Blender-side scene bootstrap (does not create the character)
- `tools/blender-import-g1-base.py`: non-destructive FBX/GLB/glTF base import with source provenance
- `tools/blender-render-g1-evidence.py`: render all sealed review cameras after modeling
- `tools/package-g1-submission.py`: seal one model and all 15 review captures for return
- `package-manifest.json`: complete byte-level inventory

Do not promote supporting references or generated drafts into geometry authority.
Preserve proportions from canonical originals and deliver all evidence requested by the work order.
After extracting this archive, create a sealed scene plan without cloning the repository:

`python3 tools/build-g1-scene-plan.py --handoff-dir . --output work/gahyeon-g1-scene-plan.json`

Then create a new Blender workspace (Blender must be installed and on PATH):

`blender --background --factory-startup --python tools/blender-bootstrap-g1.py -- --plan work/gahyeon-g1-scene-plan.json --handoff-dir . --output work/gahyeon-g1-blockout.blend`

Optionally import a MetaHuman/custom base into a new, still-unreviewed scene (the input scene is
never overwritten):

`blender work/gahyeon-g1-blockout.blend --background --python tools/blender-import-g1-base.py -- --base path/to/base.glb --output work/gahyeon-g1-base-imported.blend`

After modeling, render the exact review set from the saved scene:

`blender work/gahyeon-g1-blockout.blend --background --python tools/blender-render-g1-evidence.py -- --plan work/gahyeon-g1-scene-plan.json --output-dir work/evidence`

Both tools fail closed on changed package inputs, and the Blender tool refuses to overwrite an
existing output. The repository-side archive verifier command is:

`python3 scripts/verify_gahyeon_g1_handoff.py artifacts/gahyeon-g1-handoff.zip`

After authoring all required captures as `<view>.png`, build the return package:

`python3 tools/package-g1-submission.py --handoff-dir . --model work/gahyeon-g1.blend --format blend --evidence-dir work/evidence --output work/gahyeon-g1-submission.zip`
"""
    return content.encode("utf-8")


def package(modeling_path: Path, output: Path) -> dict:
    modeling_path = modeling_path.resolve()
    verify_modeling(modeling_path)
    modeling = json.loads(modeling_path.read_text(encoding="utf-8"))
    identity_path = (modeling_path.parent / modeling["identityManifest"]).resolve()
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    review_path = modeling_path.parent / "g1-review-template.json"
    work_order_path = modeling_path.parent / "g1-authoring-work-order.json"
    drafts_manifest_path = modeling_path.parent / "g1-drafts/drafts-manifest.json"
    if not review_path.is_file():
        raise ValueError(f"G1 review template is missing: {review_path}")
    verify_work_order(work_order_path)
    drafts_manifest = json.loads(drafts_manifest_path.read_text(encoding="utf-8"))

    files: list[tuple[str, bytes]] = [
        ("modeling-input.json", modeling_path.read_bytes()),
        ("identity-reference.json", identity_path.read_bytes()),
        ("g1-review-template.json", review_path.read_bytes()),
        ("g1-authoring-work-order.json", work_order_path.read_bytes()),
        ("g1-drafts/drafts-manifest.json", drafts_manifest_path.read_bytes()),
    ]
    for packaged_name, source in WORKSTATION_TOOLS.items():
        if not source.is_file():
            raise ValueError(f"G1 workstation tool is missing: {source}")
        files.append((packaged_name, source.read_bytes()))
    for asset in drafts_manifest["assets"]:
        name = Path(asset["file"])
        if name.is_absolute() or len(name.parts) != 1:
            raise ValueError(f"draft must use a pack-local filename: {asset['file']}")
        source = drafts_manifest_path.parent / name
        data = source.read_bytes()
        if digest(data) != asset["sha256"]:
            raise ValueError(f"G1 draft changed during packaging: {source.name}")
        files.append((f"g1-drafts/{name.name}", data))
    all_references = identity["references"] + identity["supportingReferences"]
    canonical_indices = {item["index"] for item in identity["references"]}
    packaged_references = []
    for reference in sorted(all_references, key=lambda item: item["index"]):
        reference_name = Path(reference["file"])
        if reference_name.is_absolute() or len(reference_name.parts) != 1:
            raise ValueError(f"reference must be a pack-local filename: {reference['file']}")
        source = identity_path.parent / reference_name
        data = source.read_bytes()
        if digest(data) != reference["sha256"]:
            raise ValueError(f"canonical source changed during packaging: {source.name}")
        classification = "canonical" if reference["index"] in canonical_indices else "supporting"
        suffix = reference_name.suffix.lower()
        if not suffix or not suffix.isascii():
            raise ValueError(f"reference has no portable extension: {reference['file']}")
        packaged_path = f"references/{classification}/ref-{reference['index']:03d}{suffix}"
        files.append((packaged_path, data))
        packaged_references.append({
            "index": reference["index"],
            "classification": classification,
            "sourceFile": reference["file"],
            "packagedPath": packaged_path,
            "bytes": len(data),
            "sha256": digest(data),
        })

    files.append(("reference-map.csv", build_reference_map(packaged_references)))
    files.append(("README.md", build_readme(modeling, packaged_references)))

    inventory = {
        "schemaVersion": 2,
        "characterId": modeling["characterId"],
        "purpose": "G1-model-sheet-authoring",
        "identityAuthority": "user-provided-originals",
        "sourceInventory": identity["sourceInventory"],
        "referenceCount": len(all_references),
        "canonicalReferenceCount": len(identity["references"]),
        "supportingReferenceCount": len(identity["supportingReferences"]),
        "referencePathPolicy": "portable-ascii-alias-v1",
        "references": packaged_references,
        "referenceMap": "reference-map.csv",
        "usageGuide": "README.md",
        "reviewTemplate": "g1-review-template.json",
        "authoringWorkOrder": "g1-authoring-work-order.json",
        "nonAuthoritativeDraftManifest": "g1-drafts/drafts-manifest.json",
        "nonAuthoritativeDraftCount": len(drafts_manifest["assets"]),
        "workstationTools": list(WORKSTATION_TOOLS),
        "files": [
            {"path": name, "bytes": len(data), "sha256": digest(data)}
            for name, data in files
        ],
    }
    inventory_data = (json.dumps(inventory, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
        for name, data in files:
            add_bytes(archive, name, data)
        add_bytes(archive, "package-manifest.json", inventory_data)
    temporary.replace(output)

    archive_sha = digest(output.read_bytes())
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{archive_sha}  {output.name}\n", encoding="ascii")
    return {**inventory, "archive": str(output), "archiveSha256": archive_sha}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(package(args.input, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
