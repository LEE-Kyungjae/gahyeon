"""Lift Diana's indoor candidate by roughly one stop without restoring hard light."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v405/Runtime/L_DianaMacRuntimeBalancedIndoorHair_v405"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v407/Runtime/L_DianaMacRuntimeBrightIndoorHair_v407"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v407-diana-bright-indoor-hair-runtime/report.json"
INTENSITIES = {
    "KEY_Diana_BalancedIndoor_v405": 3800.0,
    "FILL_Diana_BalancedIndoor_v405": 1600.0,
    "RIM_Diana_BalancedIndoor_v405": 1800.0,
}

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v407 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
updated = []
for actor in actors:
    label = actor.get_actor_label()
    if label not in INTENSITIES:
        continue
    actor.get_component_by_class(unreal.RectLightComponent).set_editor_property(
        "intensity", INTENSITIES[label]
    )
    actor.set_actor_label(label.replace("BalancedIndoor_v405", "BrightIndoor_v407"))
    updated.append(label)
skylights = [actor for actor in actors if isinstance(actor, unreal.SkyLight)]
posts = [actor for actor in actors if isinstance(actor, unreal.PostProcessVolume)]
if world is None or len(updated) != 3 or len(skylights) != 1 or len(posts) != 1:
    raise RuntimeError("v405 lighting composition changed unexpectedly")
skylights[0].get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.65)
settings = posts[0].get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.7)
posts[0].set_editor_property("settings", settings)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v407 bright indoor runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v407-diana-bright-indoor-hair-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "humanFinding": "v405 is too dark",
    "action": "raise exposure, fill, and skylight while preserving the large soft sources",
    "lighting": {
        "keyLumens": 3800.0,
        "fillLumens": 1600.0,
        "rimLumens": 1800.0,
        "skyIntensity": 0.65,
        "mapExposureBias": 0.7,
        "launcherExposureOffset": 0.5
    },
    "preserved": ["v403 hair clearance animation", "v002 original materials", "LOD0", "36mm safe framing", "large soft-light dimensions"],
    "actualResult": "structurally validated; desktop brightness review pending",
    "decision": "candidate; v398 remains canonical fallback",
    "humanApproved": false,
    "productionReady": false
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_BRIGHT_INDOOR_HAIR_RUNTIME_V407=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
