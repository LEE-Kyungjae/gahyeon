"""List jaw-like track aliases in the imported Hayley calibration animation."""

import json
from pathlib import Path

import unreal


ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v395-hayley-jaw-track-aliases/report.json"
)


def inspect_hayley_jaw_track_aliases_v395():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v395 report: {OUTPUT}")
    animation = unreal.EditorAssetLibrary.load_asset(ANIMATION)
    if animation is None:
        raise RuntimeError(f"animation unavailable: {ANIMATION}")
    tracks = sorted(
        str(name) for name in unreal.AnimationLibrary.get_animation_track_names(animation)
    )
    jaw_tracks = [name for name in tracks if "jaw" in name.lower()]
    report = {
        "schemaVersion": 1,
        "iteration": "v395",
        "status": "read-only-jaw-track-alias-inspection",
        "animation": ANIMATION,
        "trackCount": len(tracks),
        "jawLikeTracks": jaw_tracks,
        "allTracks": tracks,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V395_JAW_ALIASES=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_hayley_jaw_track_aliases_v395()
