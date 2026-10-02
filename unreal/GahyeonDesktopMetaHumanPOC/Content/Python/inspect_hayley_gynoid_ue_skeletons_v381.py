"""Read the actual post-import UE bone names for Hayley and Gynoid."""

import json
from pathlib import Path

import unreal


MESHES = {
    "hayley": "/Game/LivingCharacterPOC/v371/Characters/Hayley/Hayley2",
    "gynoid": "/Game/LivingCharacterPOC/v371/Donors/GynoidWalk/FemBot_1000",
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v381-ue-skeleton-inspection/report.json"
)


def inspect_hayley_gynoid_ue_skeletons_v381():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite inspection: {OUTPUT}")
    records = {}
    for key, path in MESHES.items():
        mesh = unreal.load_asset(path)
        if mesh is None:
            raise RuntimeError(f"mesh unavailable: {path}")
        modifier = unreal.SkeletonModifier()
        if not modifier.set_skeletal_mesh(mesh):
            raise RuntimeError(f"SkeletonModifier failed: {path}")
        names = [str(value) for value in modifier.get_all_bone_names()]
        records[key] = {
            "mesh": path,
            "boneCount": len(names),
            "roots": [
                name for name in names
                if not str(modifier.get_parent_name(name))
                or str(modifier.get_parent_name(name)).lower() == "none"
            ],
            "bones": [
                {
                    "name": name,
                    "parent": str(modifier.get_parent_name(name)),
                }
                for name in names
            ],
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v381",
        "status": "read-only-post-import-skeleton-inspection",
        "characters": records,
        "mutatedAssets": [],
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_GYNOID_V381_SKELETONS=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_hayley_gynoid_ue_skeletons_v381()
