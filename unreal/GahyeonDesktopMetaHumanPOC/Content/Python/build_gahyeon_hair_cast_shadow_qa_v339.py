"""Compare Gahyeon Hair Groom cast-shadow on versus off with hair visible."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v335/QA/L_GahyeonHairShadowCompare_v335"
MAP = "/Game/Gahyeon/CharacterPipeline/v339/QA/L_GahyeonHairCastShadowCompare_v339"
SEQUENCE_ROOT = "/Game/Gahyeon/CharacterPipeline/v340/Sequence"
SEQUENCE_NAME = "LS_GahyeonHairCastShadowCompare_v340"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v339-gahyeon-hair-cast-shadow-build/report.json"
)


def hair_component(actor):
    return next(
        component for component in actor.get_components_by_class(unreal.GroomComponent)
        if str(component.get_name()) == "Hair"
    )


def build_gahyeon_hair_cast_shadow_qa_v339():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, MAP):
        raise RuntimeError("failed to duplicate persistent Hair comparison map")
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    left = next(actor for actor in actors if actor.get_actor_label() == "Gahyeon_HairOn_v335")
    right = next(actor for actor in actors if actor.get_actor_label() == "Gahyeon_HairOff_v335")
    left.set_actor_label("Gahyeon_HairShadowOn_v339")
    right.set_actor_label("Gahyeon_HairShadowOff_v339")
    left_hair = hair_component(left)
    right_hair = hair_component(right)
    for component in (left_hair, right_hair):
        component.set_visibility(True, True)
        component.set_hidden_in_game(False, True)
    left_hair.set_editor_property("cast_shadow", True)
    right_hair.set_editor_property("cast_shadow", False)
    camera = next(
        actor for actor in actors
        if actor.get_actor_label() == "CAM_GahyeonHairShadow_v335"
    )
    camera.set_actor_label("CAM_GahyeonHairCastShadow_v339")
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save Hair cast-shadow map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create Hair cast-shadow sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(5)
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to open Hair cast-shadow sequence")
    camera_binding = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).add_actors([camera])[0]
    camera_cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    camera_cut.set_range(0, 5)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    camera_cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save Hair cast-shadow sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v339", "v340"],
        "status": "draft-persistent-hair-cast-shadow-comparison-ready",
        "sourceMap": SOURCE_MAP,
        "map": MAP,
        "sequence": SEQUENCE,
        "cases": [
            {"label": left.get_actor_label(), "hairVisible": True, "castShadow": True},
            {"label": right.get_actor_label(), "hairVisible": True, "castShadow": False},
        ],
        "hypothesis": (
            "Disabling cast_shadow only on the Hair GroomComponent preserves hair while "
            "removing the excessive dark neck patch."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V339_HAIR_CAST=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_hair_cast_shadow_qa_v339()
