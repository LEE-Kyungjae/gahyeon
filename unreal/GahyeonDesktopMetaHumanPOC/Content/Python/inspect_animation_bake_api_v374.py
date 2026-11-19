"""Inspect UE 5.8 animation data authoring APIs and reloaded Diana motion tracks."""

import json
from pathlib import Path

import unreal


ANIMATION = "/Game/Gahyeon/Character2/Diana/v372/Animation/AS_Diana_RunForward_v244_NeckHead_v372"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v374-animation-bake-api/report.json"
)


animation = unreal.load_asset(ANIMATION)
if animation is None:
    raise RuntimeError(f"animation unavailable: {ANIMATION}")
track_names = [str(value) for value in unreal.AnimationLibrary.get_animation_track_names(animation)]
selected = [name for name in track_names if name.lower() in {
    "neck_0", "neck_1_001", "head_002", "neck_1", "facialdef_neck", "head", "head_001"
}]
report = {
    "schemaVersion": 1,
    "iteration": "v374",
    "status": "read-only-animation-bake-api-inspection",
    "animation": ANIMATION,
    "animationMethods": sorted(name for name in dir(animation) if not name.startswith("_")),
    "apiClasses": {
        name: {
            "available": getattr(unreal, name, None) is not None,
            "methods": sorted(
                method for method in dir(getattr(unreal, name)) if not method.startswith("_")
            ) if getattr(unreal, name, None) is not None else [],
        }
        for name in (
            "AnimationDataController",
            "AnimationDataControllerLibrary",
            "AnimationBlueprintLibrary",
            "AnimationLibrary",
        )
    },
    "selectedTracks": selected,
    "selectedMotion": {
        name: {
            "rotationKeys": len(unreal.AnimationLibrary.get_raw_track_rotation_data(animation, name)),
            "translationKeys": len(unreal.AnimationLibrary.get_raw_track_position_data(animation, name)),
        }
        for name in selected
    },
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
unreal.log("DIANA_V374_ANIMATION_BAKE_API=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
