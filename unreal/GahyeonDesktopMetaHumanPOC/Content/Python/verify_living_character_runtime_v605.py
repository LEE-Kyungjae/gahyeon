"""Fail closed if any v604 runtime registry asset is unavailable in Unreal."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
REGISTRY = ROOT / "character_pipeline/config/living-character-runtime-v604.json"
REPORT = ROOT / "artifacts/living-character-poc-v605-runtime-registry-verification/report.json"


def verify_living_character_runtime_v605():
    if REPORT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {REPORT}")
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = []
    failures = []
    for character_id, character in payload["characters"].items():
        paths = {
            "skeletalMesh": character["skeletalMesh"],
            "retargeter": character["retargeter"],
            **{f"motion:{key}": value for key, value in character["motions"].items()},
        }
        for role, path in paths.items():
            asset = unreal.load_asset(path)
            record = {
                "character": character_id,
                "role": role,
                "path": path,
                "available": asset is not None,
                "class": asset.get_class().get_name() if asset is not None else None,
            }
            records.append(record)
            if asset is None:
                failures.append(record)
    report = {
        "schemaVersion": 1,
        "iteration": "v605",
        "status": "passed" if not failures else "failed",
        "registry": str(REGISTRY.relative_to(ROOT)),
        "characterCount": len(payload["characters"]),
        "checkedAssetCount": len(records),
        "availableAssetCount": sum(item["available"] for item in records),
        "failures": failures,
        "assets": records,
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError(f"v604 registry has unavailable assets: {failures}")
    unreal.log("LIVING_CHARACTER_RUNTIME_V605=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


verify_living_character_runtime_v605()
