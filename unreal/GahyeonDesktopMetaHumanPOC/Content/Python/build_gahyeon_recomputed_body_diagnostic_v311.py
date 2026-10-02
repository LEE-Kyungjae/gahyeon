"""Build a short Gahyeon sequence using the v310 recomputed-normal body."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
TARGET_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v311/Sequence/LS_GahyeonRecomputedBody_v311"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
BODY = (
    "/Game/Gahyeon/CharacterPipeline/v310/Body/"
    "SKM_Gahyeon_Body_RecomputedNormals_v310"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v311-gahyeon-recomputed-body-sequence/report.json"
)


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id))


def build_recomputed_body_diagnostic_v311():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_SEQUENCE):
        raise RuntimeError(f"refusing to overwrite diagnostic: {TARGET_SEQUENCE}")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
    body_asset = unreal.load_asset(BODY)
    if sequence is None or body_asset is None:
        raise RuntimeError("sequence or recomputed body unavailable")
    sequence.set_playback_end(5)
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError(f"could not open sequence: {TARGET_SEQUENCE}")
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
    unreal.LevelSequenceEditorBlueprintLibrary.force_update()
    binding = next(
        item for item in sequence.get_bindings()
        if "BP Gahyeon Animation POC" in str(item.get_name())
    )
    actor = next(value for value in bound_objects(binding) if isinstance(value, unreal.Actor))
    body = next(
        component for component in actor.get_components_by_class(unreal.SkeletalMeshComponent)
        if str(component.get_name()) == "Body"
    )
    body.set_editor_property("skeletal_mesh_asset", body_asset)
    unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).save_default_spawnable_state(binding)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save recomputed-body diagnostic sequence")
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    return {
        "schemaVersion": 1,
        "iteration": "v311",
        "status": "draft-recomputed-body-diagnostic",
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "body": BODY,
        "playbackFrames": [0, 5],
        "hypothesis": (
            "Recomputing normals and tangents coherently on all body LODs removes "
            "the dark neck patch while preserving identity, rig, and skin materials."
        ),
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }


report = build_recomputed_body_diagnostic_v311()
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V311_SEQUENCE=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
