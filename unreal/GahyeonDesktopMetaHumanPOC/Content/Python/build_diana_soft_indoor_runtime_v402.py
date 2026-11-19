"""Build a softer indoor-lighting candidate from Diana's stable v398 runtime."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v402/Runtime/L_DianaMacRuntimeSoftIndoor_v402"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v402-diana-soft-indoor-runtime/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v402 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
if world is None:
    raise RuntimeError("v398 world unavailable")

profiles = {
    "KEY_Diana_PBR_v379": {"intensity": 1350.0, "width": 230.0, "height": 260.0,
                            "color": unreal.Color(255, 221, 190, 255)},
    "FILL_Diana_PBR_v379": {"intensity": 420.0, "width": 260.0, "height": 280.0,
                             "color": unreal.Color(205, 224, 255, 255)},
    "RIM_Diana_PBR_v379": {"intensity": 620.0, "width": 150.0, "height": 210.0,
                            "color": unreal.Color(218, 233, 255, 255)},
}
updated_lights = []
for actor in actors:
    label = actor.get_actor_label()
    if label not in profiles:
        continue
    profile = profiles[label]
    component = actor.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", profile["intensity"])
    component.set_editor_property("source_width", profile["width"])
    component.set_editor_property("source_height", profile["height"])
    component.set_editor_property("light_color", profile["color"])
    actor.set_actor_label(label.replace("PBR_v379", "SoftIndoor_v402"))
    updated_lights.append(label)

skylights = [actor for actor in actors if isinstance(actor, unreal.SkyLight)]
posts = [actor for actor in actors if isinstance(actor, unreal.PostProcessVolume)]
if len(updated_lights) != 3 or len(skylights) != 1 or len(posts) != 1:
    raise RuntimeError("v398 lighting composition changed unexpectedly")
skylights[0].get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.3)
settings = posts[0].get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_method", True)
settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
settings.set_editor_property("override_auto_exposure_bias", True)
# The native launcher currently adds +0.5; this restores a neutral combined exposure.
settings.set_editor_property("auto_exposure_bias", -0.5)
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
posts[0].set_editor_property("settings", settings)

if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v402 soft-indoor map")
report = {
    "schemaVersion": 1,
    "iteration": "v402-diana-soft-indoor-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "lighting": {
        "key": "large warm 1350 lm",
        "fill": "large cool-neutral 420 lm",
        "rim": "subtle cool 620 lm",
        "skyIntensity": 0.3,
        "mapExposureBias": -0.5,
        "launcherExposureOffset": 0.5,
        "combinedExposureOffset": 0.0,
    },
    "preserved": ["v002 original materials", "LOD0", "36mm safe framing", "v375 approved idle"],
    "hairCollision": "pending v401 chain inspection; no blind collision inflation applied",
    "actualResult": "structurally validated; fixed-camera and desktop validation pending",
    "decision": "candidate; v398 retained as stable fallback",
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SOFT_INDOOR_RUNTIME_V402=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
