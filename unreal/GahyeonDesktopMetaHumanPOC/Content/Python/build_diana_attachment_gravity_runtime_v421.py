"""Build an immutable transparent-runtime candidate using Diana v420 idle."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v418/Runtime/L_DianaMacRuntimeShoulderOccluded_v418"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v421/Runtime/L_DianaMacRuntimeAttachmentGravity_v421"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v420/Animation/AS_Diana_Idle_AttachmentGravity_v420"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v421-diana-attachment-gravity-runtime/report.json"
)

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v421 runtime")
if not unreal.EditorAssetLibrary.does_asset_exist(ANIMATION):
    raise RuntimeError(f"Diana v420 animation unavailable: {ANIMATION}")
if not unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP):
    raise RuntimeError("failed to load retained transparent runtime")

actors = unreal.EditorLevelLibrary.get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if len(characters) != 1:
    raise RuntimeError(f"expected one Diana actor, got {len(characters)}")
character = characters[0]
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
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
character.set_actor_label("Diana_AttachmentGravity_v421")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v421 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v421-diana-attachment-gravity-runtime",
    "status": "draft",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "animation": ANIMATION,
    "retainedTransport": "native direct alpha CPU fallback",
    "expectedResult": "transparent retained framing with restrained sleeve attachment gravity",
    "actualResult": "runtime assembled; visual and motion validation pending",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_ATTACHMENT_GRAVITY_RUNTIME_V421=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
