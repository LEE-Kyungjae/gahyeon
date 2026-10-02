"""Build a short Gahyeon diagnostic using a neutral body material."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
TARGET_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v306/Sequence/LS_GahyeonNeutralBody_v306"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
NEUTRAL_MATERIAL = "/Engine/EngineMaterials/DefaultMaterial"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v306-gahyeon-neutral-body-build/report.json"
)


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id))


def build_neutral_body_diagnostic():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_SEQUENCE):
        raise RuntimeError(f"refusing to overwrite diagnostic: {TARGET_SEQUENCE}")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
    material = unreal.EditorAssetLibrary.load_asset(NEUTRAL_MATERIAL)
    if sequence is None or material is None:
        raise RuntimeError("sequence or neutral material unavailable")
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
    actor = next(
        value for value in bound_objects(binding) if isinstance(value, unreal.Actor)
    )
    body = next(
        component for component in actor.get_components_by_class(unreal.SkeletalMeshComponent)
        if str(component.get_name()) == "Body"
    )
    body.set_material(0, material)
    unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).save_default_spawnable_state(binding)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save diagnostic sequence")
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    return {
        "schemaVersion": 1,
        "iteration": "v306",
        "status": "draft-neutral-body-diagnostic",
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "neutralMaterial": NEUTRAL_MATERIAL,
        "playbackFrames": [0, 5],
        "hypothesis": (
            "If the dark neck patch disappears with a neutral material, the defect "
            "is in the body skin material/normal texture; if it remains, it is in "
            "the mesh vertex normals or tangents."
        ),
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }


report = build_neutral_body_diagnostic()
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V306_NEUTRAL_BODY=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
