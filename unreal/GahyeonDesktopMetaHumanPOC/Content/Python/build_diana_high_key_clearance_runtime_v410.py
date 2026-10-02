"""Lift Diana v409 another half stop while preserving its reflection and hair work."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v409/Runtime/L_DianaMacRuntimeBrightReflectiveClearance_v409"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v410-diana-high-key-clearance-runtime/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v410 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
fills = [actor for actor in actors if actor.get_actor_label() == "FILL_Diana_BrightReflective_v409"]
skylights = [actor for actor in actors if isinstance(actor, unreal.SkyLight)]
posts = [actor for actor in actors if isinstance(actor, unreal.PostProcessVolume)]
if world is None or len(fills) != 1 or len(skylights) != 1 or len(posts) != 1:
    raise RuntimeError("v409 lighting composition changed unexpectedly")
fill = fills[0].get_component_by_class(unreal.RectLightComponent)
fill.set_editor_property("intensity", 2800.0)
fill.set_editor_property("specular_scale", 0.8)
fills[0].set_actor_label("FILL_Diana_HighKey_v410")
skylights[0].get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.0)
settings = posts[0].get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 1.3)
posts[0].set_editor_property("settings", settings)
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v410 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v410-diana-high-key-clearance-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "humanFinding": "v409 still needs more brightness",
    "action": "add 0.35 exposure bias and lift fill/skylight; preserve key/rim specular and v408 hair clearance",
    "lighting": {
        "fillLumens": 2800.0,
        "skyIntensity": 1.0,
        "mapExposureBias": 1.3,
        "launcherExposureOffset": 0.5
    },
    "preserved": ["v408 jacket-clearance hair", "v409 key/rim reflection", "v002 original materials", "LOD0", "native alpha"],
    "actualResult": "structurally validated; desktop highlight review pending",
    "decision": "candidate; v398 remains canonical fallback",
    "humanApproved": False,
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_HIGH_KEY_CLEARANCE_V410=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
