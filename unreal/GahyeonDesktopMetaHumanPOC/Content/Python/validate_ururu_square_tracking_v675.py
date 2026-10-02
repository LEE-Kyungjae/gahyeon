"""Validate UE 5.8 face tracking on the immutable square Ururu portrait."""

import hashlib
import json
from pathlib import Path

import unreal


IMAGE = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v675-ururu-square-tracking-preflight/"
    "ururu-neutral-square.png"
)
EXPECTED_SHA256 = "a5de44b98b3b4857bcb79b27a4c9936a6533f72c489252845930f27a4fe89940"
REPORT = IMAGE.parent / "tracking-report.json"


def validate_ururu_square_tracking_v675():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v675 tracking report")
    actual_sha = hashlib.sha256(IMAGE.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_SHA256:
        raise RuntimeError("v675 square portrait checksum differs")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(
        str(IMAGE)
    )
    tracked = subsystem.track_face_landmarks_from_image(pixels, size.x, size.y)
    if isinstance(tracked, tuple) and len(tracked) == 1:
        tracked = tracked[0]
    count = len(tracked) if tracked and hasattr(tracked, "items") else 0
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v675",
        "state": "face-tracking-validated" if count else "face-tracking-failed",
        "image": str(IMAGE),
        "sha256": actual_sha,
        "size": [size.x, size.y],
        "trackedCurveCount": count,
        "suitableForConformTracking": count >= 16,
        "automaticApproval": False,
    }, indent=2) + "\n", encoding="utf-8")
    if count < 16:
        raise RuntimeError(f"v675 Ururu portrait tracked only {count} curves")
    unreal.SystemLibrary.quit_editor()


validate_ururu_square_tracking_v675()
