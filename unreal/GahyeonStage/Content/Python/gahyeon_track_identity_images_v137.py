"""Extract Epic's named 2D face contours from canonical and MetaHuman images."""

import hashlib
import json
from pathlib import Path

import unreal


IMAGES = {
    "canonical03": Path(
        "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/"
        "ChatGPT Image 2026년 8월 10일 오후 10_57_38.png"
    ),
    "metahumanV134": Path(
        "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
        "v134-metahuman-joint-identity-multiview/face-front.png"
    ),
}
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v137-epic-face-contour-tracking/tracking-report.json"
)


def sha256_v137(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def track_canonical_and_metahuman_v137():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v137 report")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    results = {}
    for label, path in IMAGES.items():
        if not path.is_file():
            raise RuntimeError(f"identity image unavailable: {path}")
        size, pixels = unreal.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(str(path))
        if size.x <= 0 or size.y <= 0:
            raise RuntimeError(f"failed to load identity image: {path}")
        tracked = subsystem.track_face_landmarks_from_image(pixels, size.x, size.y)
        if isinstance(tracked, tuple) and len(tracked) == 1:
            tracked = tracked[0]
        if not tracked or not hasattr(tracked, "items"):
            raise RuntimeError(f"Epic tracker found no face: {path}")
        contours = {}
        for name, tracking in sorted(tracked.items()):
            points = tracking.get_editor_property("tracking_points")
            contours[str(name)] = [[point.x, point.y] for point in points]
        results[label] = {
            "path": str(path),
            "sha256": sha256_v137(path),
            "dimensions": [size.x, size.y],
            "contourCount": len(contours),
            "pointCount": sum(len(points) for points in contours.values()),
            "contours": contours,
        }
    shared = sorted(set(results["canonical03"]["contours"]) & set(results["metahumanV134"]["contours"]))
    if len(shared) < 16:
        raise RuntimeError(f"too few shared Epic contour names: {len(shared)}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v137",
        "state": "epic-tracked-canonical-and-metahuman-front",
        "engine": "5.8",
        "tracker": "MetaHumanCharacterEditorSubsystem.track_face_landmarks_from_image",
        "images": results,
        "sharedContourCount": len(shared),
        "sharedContours": shared,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v137 Epic contour report written: {REPORT}")
    unreal.SystemLibrary.quit_editor()


track_canonical_and_metahuman_v137()
