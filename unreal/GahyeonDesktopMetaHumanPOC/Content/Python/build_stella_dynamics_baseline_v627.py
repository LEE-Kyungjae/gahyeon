"""Create a v627 baseline by removing only the layered Control Rig from v624."""

import json
from pathlib import Path

import unreal


SOURCE = "/Game/LivingCharacterPOC/v624/Sequence/LS_StellaDynamics_v624"
TARGET = "/Game/LivingCharacterPOC/v627/Sequence/LS_StellaDynamicsBaseline_v627"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v627-stella-dynamics-baseline/report.json"
)


def build_stella_dynamics_baseline_v627():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError("refusing to overwrite immutable v627 output")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate v624 sequence")
    sequence = unreal.load_asset(TARGET)
    removed = []
    for binding in sequence.get_bindings():
        for track in list(binding.get_tracks()):
            if isinstance(track, unreal.MovieSceneControlRigParameterTrack):
                removed.append({"binding": str(binding.get_name()), "track": str(track.get_name())})
                binding.remove_track(track)
    if len(removed) != 1:
        raise RuntimeError(f"expected one Control Rig track, removed {len(removed)}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v627 baseline")
    report = {
        "schemaVersion": 1,
        "iteration": "v627",
        "status": "draft-control-rig-free-baseline-ready",
        "sourceSequence": SOURCE,
        "sequence": TARGET,
        "removedTracks": removed,
        "remainingControlRigProxyCount": len(unreal.ControlRigSequencerLibrary.get_control_rigs(sequence)),
        "comparisonMap": "/Game/LivingCharacterPOC/v624/QA/L_StellaDynamics_v624",
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


build_stella_dynamics_baseline_v627()
