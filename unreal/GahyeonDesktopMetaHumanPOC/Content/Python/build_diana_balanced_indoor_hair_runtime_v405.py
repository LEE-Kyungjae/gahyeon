"""Rebalance v404 indoor lighting after the first desktop candidate proved too dark."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v404/Runtime/L_DianaMacRuntimeSoftIndoorHair_v404"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v405/Runtime/L_DianaMacRuntimeBalancedIndoorHair_v405"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v405-diana-balanced-indoor-hair-runtime/report.json"
INTENSITIES = {
    "KEY_Diana_SoftIndoor_v402": 3000.0,
    "FILL_Diana_SoftIndoor_v402": 1050.0,
    "RIM_Diana_SoftIndoor_v402": 1200.0,
}

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v405 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
updated = []
for actor in actors:
    label = actor.get_actor_label()
    if label in INTENSITIES:
        actor.get_component_by_class(unreal.RectLightComponent).set_editor_property(
            "intensity", INTENSITIES[label]
        )
        actor.set_actor_label(label.replace("SoftIndoor_v402", "BalancedIndoor_v405"))
        updated.append(label)
skylights = [actor for actor in actors if isinstance(actor, unreal.SkyLight)]
posts = [actor for actor in actors if isinstance(actor, unreal.PostProcessVolume)]
if world is None or len(updated) != 3 or len(skylights) != 1 or len(posts) != 1:
    raise RuntimeError("v404 lighting composition changed unexpectedly")
skylights[0].get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.45)
settings = posts[0].get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.1)
posts[0].set_editor_property("settings", settings)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v405 balanced indoor runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v405-diana-balanced-indoor-hair-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "rejectedEvidence": "v404 desktop capture was too dark for skin, cloth, and hair readability",
    "lighting": {
        "key": "large warm 3000 lm",
        "fill": "large cool-neutral 1050 lm",
        "rim": "subtle cool 1200 lm",
        "skyIntensity": 0.45,
        "mapExposureBias": 0.1,
        "launcherExposureOffset": 0.5,
    },
    "preserved": ["v403 hair clearance animation", "v002 original materials", "LOD0", "36mm safe framing"],
    "actualResult": "structurally validated; second desktop visual validation pending",
    "decision": "candidate; v398 remains canonical fallback",
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_BALANCED_INDOOR_HAIR_RUNTIME_V405=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
