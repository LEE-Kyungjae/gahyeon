"""Read-only inspection of Gahyeon presentation and Diana retarget assets."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v293-character-runtime-inspection/report.json"
)
GAHYEON_MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
DIANA_TARGET_RIG = "/Game/Gahyeon/Character2/Diana/v038/Retarget/IK_Diana_PrimaryLegs_v038"
DIANA_SOURCE_RIG = "/Game/Gahyeon/Character2/Diana/v008/Retarget/IK_Gahyeon_Source_v008"
DIANA_RETARGETER = "/Game/Gahyeon/Character2/Diana/v039/Retarget/RTG_GahyeonToDiana_PrimaryLegs_v039"
DIANA_ANIMATION = (
    "/Game/Gahyeon/Character2/Diana/v040/Animation/"
    "AS_Diana_RunForward_v244_PrimaryLegs_v040"
)


def object_path(value):
    if value is None:
        return None
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def safe_property(value, name):
    try:
        return value.get_editor_property(name)
    except Exception:
        return None


def inspect_component(component):
    mesh = safe_property(component, "skeletal_mesh_asset")
    if mesh is None:
        mesh = safe_property(component, "skeletal_mesh")
    materials = []
    try:
        materials = [object_path(item) for item in component.get_materials()]
    except Exception:
        pass
    return {
        "name": str(component.get_name()),
        "path": object_path(component),
        "visible": bool(component.is_visible()),
        "hiddenInGame": bool(safe_property(component, "hidden_in_game") or False),
        "castShadow": bool(safe_property(component, "cast_shadow") or False),
        "skeletalMesh": object_path(mesh),
        "materials": materials,
        "bounds": str(component.bounds),
    }


def inspect_rig(path):
    rig = unreal.EditorAssetLibrary.load_asset(path)
    if rig is None:
        raise RuntimeError(f"missing IK Rig: {path}")
    controller = unreal.IKRigController.get_controller(rig)
    chain_methods = sorted(name for name in dir(controller) if "chain" in name.lower())
    chains = []
    if hasattr(controller, "get_retarget_chains"):
        for chain in controller.get_retarget_chains():
            chains.append(
                {
                    "name": str(safe_property(chain, "chain_name")),
                    "startBone": str(safe_property(chain, "start_bone")),
                    "endBone": str(safe_property(chain, "end_bone")),
                    "ikGoal": str(safe_property(chain, "ik_goal_name")),
                }
            )
    return {
        "path": path,
        "controllerChainMethods": chain_methods,
        "retargetRoot": str(controller.get_retarget_root()),
        "chains": chains,
    }


if unreal.EditorLoadingAndSavingUtils.load_map(GAHYEON_MAP) is None:
    raise RuntimeError(f"failed to load map: {GAHYEON_MAP}")
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gahyeon_actors = []
for actor in actor_subsystem.get_all_level_actors():
    components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
    if not components:
        continue
    gahyeon_actors.append(
        {
            "label": actor.get_actor_label(),
            "class": str(actor.get_class().get_name()),
            "path": object_path(actor),
            "skeletalComponents": [inspect_component(item) for item in components],
        }
    )

retargeter = unreal.EditorAssetLibrary.load_asset(DIANA_RETARGETER)
animation = unreal.EditorAssetLibrary.load_asset(DIANA_ANIMATION)
if retargeter is None or animation is None:
    raise RuntimeError("Diana retargeter or animation is missing")
retarget_controller = unreal.IKRetargeterController.get_controller(retargeter)
retarget_methods = sorted(
    name for name in dir(retarget_controller) if "chain" in name.lower()
)

report = {
    "schemaVersion": 1,
    "iteration": "v293",
    "status": "read-only-inspection-complete",
    "gahyeon": {
        "map": GAHYEON_MAP,
        "skeletalActors": gahyeon_actors,
    },
    "diana": {
        "sourceRig": inspect_rig(DIANA_SOURCE_RIG),
        "targetRig": inspect_rig(DIANA_TARGET_RIG),
        "retargeter": DIANA_RETARGETER,
        "retargetControllerChainMethods": retarget_methods,
        "animation": DIANA_ANIMATION,
        "animationSkeleton": object_path(safe_property(animation, "skeleton")),
        "animationFrameCount": int(safe_property(animation, "number_of_sampled_keys") or 0),
    },
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("CHARACTER_V293_INSPECTION=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
