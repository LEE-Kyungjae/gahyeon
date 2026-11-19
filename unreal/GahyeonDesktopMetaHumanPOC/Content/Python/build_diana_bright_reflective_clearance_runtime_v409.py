"""Combine brighter soft lighting, readable reflections, and v408 hair clearance."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v407/Runtime/L_DianaMacRuntimeBrightIndoorHair_v407"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v408/Animation/AS_Diana_Idle_JacketClearance_v408"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v409/Runtime/L_DianaMacRuntimeBrightReflectiveClearance_v409"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v409-diana-bright-reflective-clearance-runtime/report.json"
LIGHTS = {
    "KEY_Diana_BrightIndoor_v407": (4200.0, 1.25),
    "FILL_Diana_BrightIndoor_v407": (2100.0, 0.75),
    "RIM_Diana_BrightIndoor_v407": (2400.0, 1.35),
}

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v409 runtime")
animation = unreal.load_asset(ANIMATION)
if animation is None:
    raise RuntimeError(f"Diana v408 animation unavailable: {ANIMATION}")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
updated = []
for actor in actors:
    label = actor.get_actor_label()
    if label not in LIGHTS:
        continue
    intensity, specular = LIGHTS[label]
    component = actor.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("specular_scale", specular)
    actor.set_actor_label(label.replace("BrightIndoor_v407", "BrightReflective_v409"))
    updated.append(label)
skylights = [actor for actor in actors if isinstance(actor, unreal.SkyLight)]
posts = [actor for actor in actors if isinstance(actor, unreal.PostProcessVolume)]
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(updated) != 3 or len(skylights) != 1 or len(posts) != 1 or len(characters) != 1:
    raise RuntimeError("v407 runtime composition changed unexpectedly")
skylights[0].get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
settings = posts[0].get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 0.95)
posts[0].set_editor_property("settings", settings)
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=animation,
        saved_looping=True,
        saved_playing=True,
        saved_position=0.0,
        saved_play_rate=1.0,
    ),
)
characters[0].set_actor_label("Diana_BrightReflective_Clearance_v409")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v409 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v409-diana-bright-reflective-clearance-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "animation": ANIMATION,
    "changes": [
        "raise fill and environment brightness without shrinking soft sources",
        "increase key and rim specular response for readable material reflection",
        "replace v403 weak hair profile with v408 jacket-clearance profile"
    ],
    "preserved": ["v002 original materials", "LOD0", "36mm safe framing", "native alpha runtime"],
    "actualResult": "structurally validated; desktop brightness, reflection, and penetration review pending",
    "decision": "candidate; v398 remains canonical fallback",
    "humanApproved": False,
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_BRIGHT_REFLECTIVE_CLEARANCE_V409=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
