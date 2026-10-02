"""Export the two validated UE living idles for Blender secondary-motion authoring."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
OUTPUT = ROOT / "artifacts/living-character-poc-v612-target-living-idle-exports"
ANIMATIONS = {
    "stella-lily": "/Game/LivingCharacterPOC/v606/Animation/stella/AS_Stella_LivingIdle_v606",
    "ururu": "/Game/LivingCharacterPOC/v606/Animation/ururu/AS_Ururu_LivingIdle_Corrected_v606",
}


def export_target_living_idles_v612():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v612 output: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    records = {}
    for character_id, path in ANIMATIONS.items():
        animation = unreal.load_asset(path)
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError(f"missing AnimSequence: {path}")
        destination = OUTPUT / f"{character_id}-living-idle-v612.fbx"
        options = unreal.FbxExportOption()
        options.set_editor_property("export_preview_mesh", False)
        options.set_editor_property("export_morph_targets", False)
        options.set_editor_property("map_skeletal_motion_to_root", False)
        task = unreal.AssetExportTask()
        task.set_editor_property("object", animation)
        task.set_editor_property("filename", str(destination))
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", False)
        task.set_editor_property("options", options)
        if not unreal.Exporter.run_asset_export_task(task):
            raise RuntimeError(f"FBX export failed: {character_id}")
        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError(f"FBX export produced no file: {destination}")
        records[character_id] = {
            "animation": path,
            "skeleton": str(animation.get_editor_property("skeleton").get_path_name()),
            "durationSeconds": float(animation.get_play_length()),
            "sampledKeys": int(animation.get_editor_property("number_of_sampled_keys")),
            "file": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v612",
        "status": "exported-two-living-idles-for-secondary-motion-authoring",
        "characters": records,
        "humanApproved": False,
        "releaseEligible": False,
    }
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("TARGET_LIVING_IDLE_EXPORTS_V612=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


export_target_living_idles_v612()
