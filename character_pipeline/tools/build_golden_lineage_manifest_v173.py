#!/usr/bin/env python3
"""Build an evidence-only asset lineage inventory without mutating Unreal assets."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


ASSET_PATTERN = re.compile(r"/Game/[A-Za-z0-9_./-]+")
ROLE_NAMES = {
    "SOURCE", "SOURCE_CHARACTER", "SOURCE_CHARACTER_PATH", "CHARACTER",
    "TARGET", "TARGET_CHARACTER", "BLUEPRINT", "BLUEPRINT_PATH", "MAP",
    "MAP_PATH", "SOURCE_MAP", "TARGET_MAP", "IDENTITY_ASSET", "WARDROBE_ITEM",
    "BUILD_ROOT", "COMMON_ROOT",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string_constants(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return {}
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in ROLE_NAMES:
                values[target.id] = value.value
    return values


def build_golden_lineage_manifest_v173(workspace: Path) -> dict:
    source_asset = "/Game/Fab/MetaHuman/Skotukeda"
    source_file = workspace / "unreal/GahyeonStage/Content/Fab/MetaHuman/Skotukeda.uasset"
    scripts_root = workspace / "unreal/GahyeonStage/Content/Python"
    records = []
    for script in sorted(scripts_root.glob("*.py")):
        constants = _string_constants(script)
        assets = sorted({value for value in constants.values() if value.startswith("/Game/")})
        if not assets:
            continue
        source_values = sorted({
            value for name, value in constants.items()
            if name.startswith("SOURCE") or name in {"CHARACTER", "BLUEPRINT", "BLUEPRINT_PATH", "MAP"}
        })
        target_values = sorted({
            value for name, value in constants.items()
            if name.startswith("TARGET") or name in {"BUILD_ROOT", "COMMON_ROOT", "MAP_PATH"}
        })
        if source_asset not in assets and not any(
            value.startswith("/Game/Gahyeon/CharacterPipeline/") for value in assets
        ):
            continue
        records.append({
            "script": str(script.relative_to(workspace)),
            "sha256": _sha256(script),
            "declaredAssets": assets,
            "declaredSources": source_values,
            "declaredTargets": target_values,
            "edgeAuthority": "declared-script-constants-only",
        })

    character_assets = []
    content_root = workspace / "unreal/GahyeonStage/Content"
    for path in sorted(content_root.glob("Gahyeon/CharacterPipeline/**/Character/MHC_*.uasset")):
        character_assets.append({
            "asset": "/Game/" + str(path.relative_to(content_root).with_suffix("")),
            "file": str(path.relative_to(workspace)),
            "sizeBytes": path.stat().st_size,
            "sha256": _sha256(path),
        })

    assemblies = []
    for path in sorted(content_root.glob("Gahyeon/CharacterPipeline/**/BP_*.uasset")):
        assemblies.append({
            "asset": "/Game/" + str(path.relative_to(content_root).with_suffix("")),
            "file": str(path.relative_to(workspace)),
            "sizeBytes": path.stat().st_size,
            "sha256": _sha256(path),
        })

    return {
        "schemaVersion": 1,
        "iteration": "v173",
        "state": "forensic-lineage-inventory-awaiting-human-golden-selection",
        "sourceFabListing": {
            "listingId": "41e1b941-3b4e-468d-b6a7-2ce3e8ef1e32",
            "title": "Skotukeda",
            "url": "https://www.fab.com/listings/41e1b941-3b4e-468d-b6a7-2ce3e8ef1e32",
        },
        "sourceAsset": {
            "asset": source_asset,
            "file": str(source_file.relative_to(workspace)),
            "sizeBytes": source_file.stat().st_size,
            "sha256": _sha256(source_file),
        },
        "identityAuthority": {
            "manifest": "artifacts/gahyeon-ch/identity-reference.json",
            "board": "artifacts/gahyeon-ch/identity-reference-board.png",
            "meaning": "Gahyeon canonical images, not the Fab source face",
        },
        "declaredScriptLineage": records,
        "materializedCharacterAssets": character_assets,
        "materializedAssemblies": assemblies,
        "counts": {
            "scripts": len(records),
            "characters": len(character_assets),
            "assemblies": len(assemblies),
        },
        "limitations": [
            "Script constant edges show declared intent and do not prove successful execution.",
            "Materialized assets prove file existence, not visual quality or exact ancestry.",
            "Golden Identity and Production Foundation remain separate until human confirmation.",
        ],
        "automaticGoldenSelection": False,
        "assetsMutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite immutable output: {args.output}")
    result = build_golden_lineage_manifest_v173(args.workspace.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "counts": result["counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
