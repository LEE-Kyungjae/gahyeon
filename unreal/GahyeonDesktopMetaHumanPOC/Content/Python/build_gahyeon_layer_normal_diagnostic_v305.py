"""Build a short diagnostic overriding Gahyeon's body layer normal strength."""

import json
from pathlib import Path

import unreal


SOURCE_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
TARGET_SEQUENCE = "/Game/Gahyeon/TalkingPOC/v305/Sequence/LS_GahyeonBodyNormalOff_v305"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
SOURCE_MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/Materials/MI_Body_Baked"
)
TARGET_MATERIAL = "/Game/Gahyeon/TalkingPOC/v305/Materials/MI_Body_NormalOff_v305"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v305-gahyeon-layer-normal-off-build/report.json"
)
PARAMETER = "Normal Global Strength Post-Bake"
ASSOCIATION = unreal.MaterialParameterAssociation.LAYER_PARAMETER


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id))


def build_layer_normal_diagnostic():
    for path in (TARGET_SEQUENCE, TARGET_MATERIAL):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable diagnostic: {path}")
    sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_SEQUENCE, TARGET_SEQUENCE)
    material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MATERIAL, TARGET_MATERIAL)
    if sequence is None or material is None:
        raise RuntimeError("failed to duplicate diagnostic assets")
    override_result = unreal.MaterialEditingLibrary.set_material_instance_parameter_override(
        material, PARAMETER, True, ASSOCIATION
    )
    value_result = unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, PARAMETER, 0.0, ASSOCIATION
    )
    effective_value = float(
        unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            material, PARAMETER, ASSOCIATION
        )
    )
    if not override_result or abs(effective_value) > 0.000001:
        raise RuntimeError(
            f"layer normal override failed: override={override_result}, "
            f"setter={value_result}, effective={effective_value}"
        )
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
    actors = [value for value in bound_objects(binding) if isinstance(value, unreal.Actor)]
    if len(actors) != 1:
        raise RuntimeError(f"expected one character actor, got {len(actors)}")
    body = next(
        component for component in actors[0].get_components_by_class(unreal.SkeletalMeshComponent)
        if str(component.get_name()) == "Body"
    )
    body.set_material(0, material)
    unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).save_default_spawnable_state(binding)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("failed to save material")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save sequence")
    unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    return {
        "schemaVersion": 1,
        "iteration": "v305",
        "status": "draft-layer-normal-disabled",
        "sequence": TARGET_SEQUENCE,
        "map": MAP,
        "material": TARGET_MATERIAL,
        "parameter": PARAMETER,
        "association": str(ASSOCIATION),
        "setterResult": bool(value_result),
        "effectiveValue": effective_value,
        "playbackFrames": [0, 5],
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }


report = build_layer_normal_diagnostic()
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V305_LAYER_NORMAL=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
