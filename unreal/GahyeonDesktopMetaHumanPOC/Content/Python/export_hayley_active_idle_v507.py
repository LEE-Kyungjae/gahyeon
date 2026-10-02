"""Export Hayley's verified v466 active idle for deterministic facial layering."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
ANIMATION_PATH = "/Game/LivingCharacterPOC/v466/Animation/AS_HayleyClean_CyberIdle_v466"
OUTPUT_DIR = ROOT / "artifacts/living-character-poc-v507-hayley-active-idle-export"
OUTPUT = OUTPUT_DIR / "AS_HayleyClean_CyberIdle_v466.fbx"
REPORT = OUTPUT_DIR / "report.json"


def export_hayley_active_idle_v507():
    if OUTPUT_DIR.exists() or OUTPUT.exists() or REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v507 outputs")
    animation = unreal.load_asset(ANIMATION_PATH)
    if not isinstance(animation, unreal.AnimSequence):
        raise RuntimeError(f"active idle is unavailable: {ANIMATION_PATH}")
    OUTPUT_DIR.mkdir(parents=True)
    options = unreal.FbxExportOption()
    options.set_editor_property("export_preview_mesh", False)
    options.set_editor_property("export_morph_targets", False)
    options.set_editor_property("map_skeletal_motion_to_root", False)
    task = unreal.AssetExportTask()
    task.set_editor_property("object", animation)
    task.set_editor_property("filename", str(OUTPUT))
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", False)
    task.set_editor_property("options", options)
    if not unreal.Exporter.run_asset_export_task(task):
        raise RuntimeError("active idle FBX export failed")
    if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
        raise RuntimeError("active idle FBX export produced no file")
    report = {
        "schemaVersion": 1, "iteration": "v507", "status": "exported-active-idle-source",
        "animation": ANIMATION_PATH, "skeleton": str(animation.get_editor_property("skeleton").get_path_name()),
        "durationSeconds": float(animation.get_play_length()),
        "sampledKeys": int(animation.get_editor_property("number_of_sampled_keys")),
        "output": str(OUTPUT), "outputBytes": OUTPUT.stat().st_size,
        "outputSha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "humanApproved": False, "releaseEligible": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_ACTIVE_IDLE_EXPORT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


export_hayley_active_idle_v507()
