"""Build a five-frame Gahyeon diagnostic with body baked normals disabled."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
TARGET_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v302/Sequence/LS_GahyeonBodyNormalOff_v302"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
SOURCE_MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/Materials/MI_Body_Baked"
)
TARGET_MATERIAL = (
    "/Game/Gahyeon/TalkingPOC/v302/Materials/MI_Body_Baked_NormalOff_v302"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v302-gahyeon-body-normal-off-build/report.json"
)


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(
        unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id)
    )


def build_normal_disabled_diagnostic():
    for path in (TARGET_SEQUENCE, TARGET_MATERIAL):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable diagnostic: {path}")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_SEQUENCE, TARGET_SEQUENCE
    )
    material = unreal.EditorAssetLibrary.duplicate_asset(
        SOURCE_MATERIAL, TARGET_MATERIAL
    )
    if sequence is None or material is None:
        raise RuntimeError("failed to duplicate sequence or body material")
    if not unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, "Normal Global Strength Post-Bake", 0.0
    ):
        raise RuntimeError("body material has no baked-normal strength parameter")
    sequence.set_playback_end(5)

    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError(f"could not open sequence: {TARGET_SEQUENCE}")
    unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
    unreal.LevelSequenceEditorBlueprintLibrary.force_update()
    character_binding = next(
        (
            binding
            for binding in sequence.get_bindings()
            if "BP Gahyeon Animation POC" in str(binding.get_name())
        ),
        None,
    )
    if character_binding is None:
        raise RuntimeError("character binding unavailable")
    actors = [
        value
        for value in bound_objects(character_binding)
        if isinstance(value, unreal.Actor)
    ]
    if len(actors) != 1:
        raise RuntimeError(f"expected one character actor, got {len(actors)}")
    body = next(
        (
            component
            for component in actors[0].get_components_by_class(
                unreal.SkeletalMeshComponent
            )
            if str(component.get_name()) == "Body"
        ),
        None,
    )
    if body is None:
        raise RuntimeError("runtime Body component unavailable")
    body.set_material(0, material)
    sequence_subsystem = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    )
    sequence_subsystem.save_default_spawnable_state(character_binding)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("failed to save diagnostic body material")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save diagnostic sequence")
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    return {
        "schemaVersion": 1,
        "iteration": "v302",
        "status": "draft-body-baked-normal-disabled",
        "sourceSequence": SOURCE_SEQUENCE,
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "sourceMaterial": SOURCE_MATERIAL,
        "material": TARGET_MATERIAL,
        "changedParameter": "Normal Global Strength Post-Bake",
        "changedValue": 0.0,
        "playbackFrames": [0, 5],
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }


report = build_normal_disabled_diagnostic()
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V302_NORMAL_DIAGNOSTIC=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
