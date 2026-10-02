"""Mark four verified Ururu float curves as morph-target drivers on the shared skeleton."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SKELETON_PATH = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
SKELETON_FILE = ROOT / "unreal/GahyeonStage/Content/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton.uasset"
REPORT = ROOT / "artifacts/living-character-poc-v716-ururu-morph-curve-metadata/report.json"
CURVES = ("EyeBlink_L", "EyeBlink_R", "GazeLeft", "GazeRight")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def enable_ururu_morph_curve_metadata_v716() -> None:
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v716 report")
    if not SKELETON_FILE.is_file():
        raise FileNotFoundError(SKELETON_FILE)
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        raise RuntimeError("validated v585 skeleton is unavailable")
    before_sha = sha256(SKELETON_FILE)
    before_names = [str(name) for name in skeleton.get_curve_meta_data_names()]
    before = {
        name: bool(skeleton.get_curve_meta_data_morph_target(name))
        for name in CURVES
    }
    if any(before.values()):
        raise RuntimeError(f"unexpected pre-existing v716 morph metadata: {before}")

    for name in CURVES:
        skeleton.add_curve_meta_data(name, False)
        skeleton.set_curve_meta_data_morph_target(name, True)
        skeleton.set_curve_meta_data_material(name, False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(skeleton, only_if_is_dirty=False):
        raise RuntimeError("failed to save v716 skeleton curve metadata")

    after_names = [str(name) for name in skeleton.get_curve_meta_data_names()]
    after = {
        name: {
            "morphTargetMetadata": bool(skeleton.get_curve_meta_data_morph_target(name)),
            "materialMetadata": bool(skeleton.get_curve_meta_data_material(name)),
        }
        for name in CURVES
    }
    if not all(value["morphTargetMetadata"] and not value["materialMetadata"] for value in after.values()):
        raise RuntimeError(f"v716 metadata validation failed: {after}")
    missing = sorted(set(CURVES) - set(after_names))
    if missing:
        raise RuntimeError(f"v716 metadata names missing after save: {missing}")
    after_sha = sha256(SKELETON_FILE)
    if before_sha == after_sha:
        raise RuntimeError("v716 skeleton checksum did not change after metadata save")

    report = {
        "schemaVersion": 1,
        "iteration": "v716",
        "status": "validated-draft-morph-curve-metadata-enabled",
        "skeleton": SKELETON_PATH,
        "skeletonFile": str(SKELETON_FILE),
        "beforeSha256": before_sha,
        "afterSha256": after_sha,
        "beforeMetadataNames": before_names,
        "afterMetadataNames": after_names,
        "beforeMorphFlags": before,
        "after": after,
        "scope": "curve metadata only; no bone, bind-pose, mesh, or animation-key mutation",
        "visualValidationPending": True,
        "automaticApproval": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_MORPH_CURVE_METADATA_V716=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


enable_ururu_morph_curve_metadata_v716()
