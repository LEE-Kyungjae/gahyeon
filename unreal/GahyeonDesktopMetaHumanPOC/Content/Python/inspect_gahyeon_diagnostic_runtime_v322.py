"""Verify whether diagnostic sequence component overrides survive evaluation."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
SEQUENCES = (
    "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291",
    "/Game/Gahyeon/TalkingPOC/v306/Sequence/LS_GahyeonNeutralBody_v306",
    "/Game/Gahyeon/TalkingPOC/v311/Sequence/LS_GahyeonRecomputedBody_v311",
    "/Game/Gahyeon/TalkingPOC/v318/Sequence/LS_GahyeonBodyOnly_v318",
    "/Game/Gahyeon/TalkingPOC/v319/Sequence/LS_GahyeonFaceOnly_v319",
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v322-gahyeon-diagnostic-runtime/report.json"
)


def path_of(value):
    return str(value.get_path_name()) if value is not None else None


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id))


def inspect_gahyeon_diagnostic_runtime_v322():
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    cases = []
    for sequence_path in SEQUENCES:
        sequence = unreal.load_asset(sequence_path)
        if sequence is None:
            raise RuntimeError(f"sequence unavailable: {sequence_path}")
        if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
            raise RuntimeError(f"could not open sequence: {sequence_path}")
        unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
        unreal.LevelSequenceEditorBlueprintLibrary.force_update()
        binding = next(
            item for item in sequence.get_bindings()
            if "BP Gahyeon Animation POC" in str(item.get_name())
        )
        actor = next(value for value in bound_objects(binding) if isinstance(value, unreal.Actor))
        components = []
        for name in ("Body", "Face"):
            component = next(
                item for item in actor.get_components_by_class(unreal.SkeletalMeshComponent)
                if str(item.get_name()) == name
            )
            mesh = component.get_editor_property("skeletal_mesh_asset")
            components.append(
                {
                    "name": name,
                    "mesh": path_of(mesh),
                    "visible": bool(component.is_visible()),
                    "hiddenInGame": bool(component.get_editor_property("hidden_in_game")),
                    "materials": [path_of(item) for item in component.get_materials()],
                }
            )
        cases.append({"sequence": sequence_path, "components": components})
        unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    report = {
        "schemaVersion": 1,
        "iteration": "v322",
        "status": "read-only-runtime-inspection",
        "map": MAP,
        "cases": cases,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V322_RUNTIME=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_diagnostic_runtime_v322()
