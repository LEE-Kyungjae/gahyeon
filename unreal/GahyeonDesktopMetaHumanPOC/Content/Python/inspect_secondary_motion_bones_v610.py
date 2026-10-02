"""Inventory character-local hair and clothing bones before physics authoring."""

import json
from pathlib import Path

import unreal


MESHES = {
    "stella-lily": "/Game/LivingCharacterPOC/v572/Characters/StellaCentimeterNormalized/StellaLily_CentimeterNormalized_v571",
    "ururu": "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584",
}
TOKENS = {
    "hair": ("hair", "bang", "ponytail", "braid", "strand"),
    "clothing": ("cloth", "skirt", "dress", "coat", "sleeve", "cape", "ribbon"),
    "accessory": ("accessory", "earring", "tail", "horn"),
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v610-secondary-motion-bone-inventory/report.json"
)


def inspect_secondary_motion_bones_v610():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    characters = {}
    for character_id, path in MESHES.items():
        mesh = unreal.load_asset(path)
        if mesh is None:
            raise RuntimeError(f"missing skeletal mesh: {path}")
        modifier = unreal.SkeletonModifier()
        if not modifier.set_skeletal_mesh(mesh):
            raise RuntimeError(f"SkeletonModifier rejected {path}")
        names = [str(value) for value in modifier.get_all_bone_names()]
        groups = {}
        for role, tokens in TOKENS.items():
            groups[role] = [name for name in names if any(token in name.lower() for token in tokens)]
        characters[character_id] = {
            "mesh": path,
            "boneCount": len(names),
            "candidateSecondaryBoneCount": sum(len(group) for group in groups.values()),
            "groups": groups,
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v610",
        "status": "read-only-secondary-motion-bone-inventory",
        "characters": characters,
        "decisionRule": "Use local bone physics only when explicit weighted secondary chains exist; otherwise author Groom or Chaos assets separately.",
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("SECONDARY_MOTION_BONES_V610=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_secondary_motion_bones_v610()
