"""Combine the v402 soft indoor look with Diana's v403 restrained hair idle."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v402/Runtime/L_DianaMacRuntimeSoftIndoor_v402"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v403/Animation/AS_Diana_Idle_HairClearance_v403"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v404/Runtime/L_DianaMacRuntimeSoftIndoorHair_v404"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v404-diana-soft-indoor-hair-runtime/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v404 runtime")
animation = unreal.load_asset(ANIMATION)
if animation is None:
    raise RuntimeError(f"Diana v403 hair animation unavailable: {ANIMATION}")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v402 character composition changed unexpectedly")
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
characters[0].set_actor_label("Diana_SoftIndoor_HairClearance_v404")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v404 runtime")
report = {
    "schemaVersion": 1,
    "iteration": "v404-diana-soft-indoor-hair-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "animation": ANIMATION,
    "preserved": ["v002 original materials", "LOD0", "36mm safe framing", "native alpha runtime"],
    "changes": ["soft indoor lighting", "scalp-anchored hair clearance", "restrained hair secondary motion"],
    "actualResult": "structurally validated; desktop visual validation pending",
    "decision": "candidate; v398 retained as stable fallback",
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SOFT_INDOOR_HAIR_RUNTIME_V404=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
