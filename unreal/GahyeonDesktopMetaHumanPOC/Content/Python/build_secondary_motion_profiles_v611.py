"""Build reusable secondary-motion chain profiles from actual UE skeletons."""

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
}
TUNING = {
    "hair": {"stiffness": 0.34, "damping": 0.72, "gravityScale": 0.55, "maxAngleDegrees": 18.0},
    "clothing": {"stiffness": 0.46, "damping": 0.78, "gravityScale": 0.8, "maxAngleDegrees": 14.0},
}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/character_pipeline/config/"
    "secondary-motion-profiles-v611.json"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v611-secondary-motion-profiles/report.json"
)


def build_secondary_motion_profiles_v611():
    if OUTPUT.exists() or REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v611 outputs")
    characters = {}
    for character_id, mesh_path in MESHES.items():
        mesh = unreal.load_asset(mesh_path)
        if mesh is None:
            raise RuntimeError(f"missing skeletal mesh: {mesh_path}")
        modifier = unreal.SkeletonModifier()
        if not modifier.set_skeletal_mesh(mesh):
            raise RuntimeError(f"SkeletonModifier rejected {mesh_path}")
        names = [str(value) for value in modifier.get_all_bone_names()]
        parents = {name: str(modifier.get_parent_name(name)) for name in names}
        groups = {}
        for role, tokens in TOKENS.items():
            selected = {name for name in names if any(token in name.lower() for token in tokens)}
            roots = sorted(name for name in selected if parents[name] not in selected and not name.lower().endswith("_end"))
            chains = []
            for root in roots:
                members = []
                frontier = [root]
                while frontier:
                    current = frontier.pop(0)
                    if current in members:
                        continue
                    members.append(current)
                    frontier.extend(sorted(name for name in selected if parents[name] == current))
                members = [name for name in members if not name.lower().endswith("_end")]
                if members:
                    chains.append({"root": root, "bones": members, "boneCount": len(members)})
            groups[role] = {"tuning": TUNING[role], "chainCount": len(chains), "chains": chains}
        characters[character_id] = {
            "skeletalMesh": mesh_path,
            "evaluationOrder": ["baseAnimation", "ikRetarget", "secondaryMotion", "postPhysicsCollision"],
            "groups": groups,
        }
    profile = {
        "schemaVersion": 1,
        "iteration": "v611",
        "status": "draft-secondary-motion-chain-profiles",
        "characters": characters,
        "runtime": {
            "preferredSolver": "PhysicsControl-or-AnimDynamics",
            "fixedTimestepRecommended": True,
            "teleportResetRequired": True,
            "lodDisableDistanceCm": 600.0,
            "collisionPrimitivesRequired": ["head", "neck", "shoulders", "chest", "pelvis", "thighs"],
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    report = {
        "schemaVersion": 1,
        "iteration": "v611",
        "status": "passed-chain-profile-generation",
        "profile": str(OUTPUT),
        "characters": {
            key: {
                role: value["groups"][role]["chainCount"]
                for role in TOKENS
            }
            for key, value in characters.items()
        },
        "humanApproved": False,
        "releaseEligible": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("SECONDARY_MOTION_PROFILES_V611=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_secondary_motion_profiles_v611()
