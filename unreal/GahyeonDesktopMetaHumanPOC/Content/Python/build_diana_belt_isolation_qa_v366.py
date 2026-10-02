"""Compare Diana with all materials against a belt-only hidden derivative."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v358/QA/L_DianaReferenceAnimationCompare_v358"
MAP = "/Game/Gahyeon/Character2/Diana/v366/QA/L_DianaBeltIsolation_v366"
SEQUENCE_ROOT = "/Game/Gahyeon/Character2/Diana/v367/Sequence"
SEQUENCE_NAME = "LS_DianaBeltIsolation_v367"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v345/Animation/AS_Diana_Idle_v244_APose_v345"
HIDDEN = "/Game/Gahyeon/Character2/Diana/v034/QA/M_Diana_HiddenAccessories_v034"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v366-diana-belt-isolation-build/report.json"
)


def build_diana_belt_isolation_qa_v366():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    hidden = unreal.load_asset(HIDDEN)
    animation = unreal.load_asset(ANIMATION)
    if hidden is None or animation is None:
        raise RuntimeError("Diana hidden material or animation unavailable")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, MAP):
        raise RuntimeError("failed to duplicate Diana comparison map")
    if not unreal.EditorLevelLibrary.load_level(MAP):
        raise RuntimeError("failed to load Diana belt-isolation map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    by_label = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
    original = by_label.get("Diana_Reference_v358")
    fixed = by_label.get("Diana_Animated_v358")
    camera = by_label.get("CAM_DianaReferenceAnimationCompare_v358")
    if original is None or fixed is None or camera is None:
        raise RuntimeError(f"comparison actors missing: {sorted(by_label)}")
    fixed.set_actor_label("Diana_BeltHidden_v366")
    camera.set_actor_label("CAM_DianaBeltIsolation_v366")
    fixed_component = fixed.get_component_by_class(unreal.SkeletalMeshComponent)
    fixed_component.set_material(14, hidden)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save Diana belt-isolation map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(1)
    sequence.set_playback_end(31)
    unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence)
    sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    bindings = sequencer.add_actors([fixed, camera])
    by_name = {str(binding.get_name()): binding for binding in bindings}
    section = by_name["Diana_BeltHidden_v366"].add_track(
        unreal.MovieSceneSkeletalAnimationTrack
    ).add_section()
    section.set_range(0, 31)
    section.params.animation = animation
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(1, 31)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", by_name["CAM_DianaBeltIsolation_v366"].get_id())
    cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Diana belt-isolation sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v366", "v367"],
        "status": "draft-belt-isolation-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "animation": ANIMATION,
        "hiddenMaterialSlotsOnRight": [14],
        "preservedMaterialSlotsOnRight": list(range(14)) + [15, 16, 17],
        "hypothesis": (
            "Hiding only the independently identified NeoBelt section removes the horizontal "
            "strap islands without deleting anatomy or NeoJacket geometry."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("DIANA_V366_BELT_ISOLATION=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_diana_belt_isolation_qa_v366()
