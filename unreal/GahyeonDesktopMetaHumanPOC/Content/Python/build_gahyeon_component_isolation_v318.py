"""Create immutable body-only and face-only neck diagnostics for Gahyeon."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
CASES = (
    (
        "v318",
        "/Game/Gahyeon/TalkingPOC/v318/Sequence/LS_GahyeonBodyOnly_v318",
        "Face",
    ),
    (
        "v319",
        "/Game/Gahyeon/TalkingPOC/v319/Sequence/LS_GahyeonFaceOnly_v319",
        "Body",
    ),
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v318-gahyeon-component-isolation-build/report.json"
)


def bound_objects(binding):
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    return list(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id))


def build_gahyeon_component_isolation_v318():
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    results = []
    for iteration, target, hidden_component in CASES:
        if unreal.EditorAssetLibrary.does_asset_exist(target):
            raise RuntimeError(f"refusing to overwrite immutable sequence: {target}")
        sequence = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, target)
        if sequence is None:
            raise RuntimeError(f"failed to duplicate diagnostic: {target}")
        sequence.set_playback_end(5)
        if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
            raise RuntimeError(f"could not open sequence: {target}")
        unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
        unreal.LevelSequenceEditorBlueprintLibrary.force_update()
        binding = next(
            item for item in sequence.get_bindings()
            if "BP Gahyeon Animation POC" in str(item.get_name())
        )
        actor = next(value for value in bound_objects(binding) if isinstance(value, unreal.Actor))
        component = next(
            item for item in actor.get_components_by_class(unreal.SkeletalMeshComponent)
            if str(item.get_name()) == hidden_component
        )
        component.set_visibility(False, True)
        component.set_hidden_in_game(True, True)
        unreal.get_editor_subsystem(
            unreal.LevelSequenceEditorSubsystem
        ).save_default_spawnable_state(binding)
        if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
            raise RuntimeError(f"failed to save diagnostic: {target}")
        unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
        results.append(
            {
                "iteration": iteration,
                "sequence": target,
                "hiddenComponent": hidden_component,
                "playbackFrames": [0, 5],
            }
        )
    report = {
        "schemaVersion": 1,
        "iteration": "v318-v319",
        "status": "draft-component-isolation-ready",
        "source": SOURCE,
        "map": MAP,
        "cases": results,
        "hypothesis": (
            "Face-only and Body-only renders reveal whether the persistent dark neck "
            "patch belongs to one mesh or is caused by overlapping neck geometry."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V318_COMPONENT_ISOLATION=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_component_isolation_v318()
