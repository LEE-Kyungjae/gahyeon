"""Build a transparent runtime candidate for Diana's actual +90 pitch sleeve sweep."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v421/Runtime/L_DianaMacRuntimeAttachmentGravity_v421"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v432/Runtime/L_DianaMacRuntimeSleevePitchPos90_v432"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v431/Animation/AS_Diana_Idle_Sleeve_yaw_pos90_v431"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v432-diana-sleeve-pitch-pos90-runtime/report.json"
)


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v432 runtime")
if unreal.load_asset(ANIMATION) is None:
    raise RuntimeError(f"missing v431 pitch candidate: {ANIMATION}")
if not unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP):
    raise RuntimeError(f"failed to load retained runtime: {SOURCE_MAP}")
characters = [
    actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
    if isinstance(actor, unreal.SkeletalMeshActor)
]
if len(characters) != 1:
    raise RuntimeError(f"expected one Diana actor, got {len(characters)}")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=unreal.load_asset(ANIMATION),
        saved_looping=True,
        saved_playing=True,
        saved_position=0.0,
        saved_play_rate=1.0,
    ),
)
characters[0].set_actor_label("Diana_SleevePitchPos90_v432")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v432 runtime")
report = {
    "schemaVersion": 1,
    "iteration": "v432",
    "status": "draft-runtime-visual-validation-required",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "animation": ANIMATION,
    "actualDeltaRotatorDegrees": {"pitch": 90.0, "yaw": 0.0, "roll": 0.0},
    "expectedResult": "sleeve rods rotate from rigid horizontal to a gravity-readable hanging orientation",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SLEEVE_PITCH_RUNTIME_V432=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
