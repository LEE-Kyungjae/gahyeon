"""Read-only inventory of the retained v088 MetaHuman talking-animation surface."""

import json
from pathlib import Path

import unreal


BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/"
    "Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088"
)
MAP = "/Game/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091"


def _name(value):
    if value is None:
        return None
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _property(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def inspect():
    generated_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if generated_class is None:
        raise RuntimeError(f"v088 Blueprint unavailable: {BLUEPRINT}")
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    if world is None:
        raise RuntimeError(f"v091 Desktop map unavailable: {MAP}")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matching = [actor for actor in actor_subsystem.get_all_level_actors()
                if actor.get_class() == generated_class]
    actor = matching[0] if len(matching) == 1 else None
    spawned_for_inspection = actor is None
    if actor is None:
        actor = actor_subsystem.spawn_actor_from_class(
            generated_class, unreal.Vector(), unreal.Rotator())
    if actor is None:
        raise RuntimeError("failed to resolve v088 inspection actor")
    components = []
    try:
        scene_components = list(actor.get_components_by_class(unreal.SceneComponent))
        skeletal_components = list(actor.get_components_by_class(unreal.SkeletalMeshComponent))
        unique_components = {component.get_path_name(): component
                             for component in scene_components + skeletal_components}
        for component in unique_components.values():
            record = {
                "name": component.get_name(),
                "class": component.get_class().get_name(),
                "tags": [str(tag) for tag in _property(component, "component_tags") or []],
            }
            if isinstance(component, unreal.SkeletalMeshComponent):
                mesh = _property(component, "skeletal_mesh_asset") or _property(component, "skeletal_mesh")
                morph_names = component.get_morph_target_names()
                record.update({
                    "skeletalMesh": _name(mesh),
                    "animationMode": str(_property(component, "animation_mode")),
                    "animClass": _name(_property(component, "anim_class")),
                    "leaderPoseComponent": _name(_property(component, "leader_pose_component")),
                    "morphTargetCount": len(morph_names),
                    "morphTargets": sorted(str(item) for item in morph_names),
                })
            components.append(record)
    finally:
        if spawned_for_inspection:
            actor_subsystem.destroy_actor(actor)

    repo = Path(unreal.Paths.project_dir()).resolve().parents[1]
    output = repo / "artifacts/desktop-looking-glass-runtime-poc-v092/talking-surface.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "iteration": "v092",
        "status": "read-only-inspection",
        "blueprint": BLUEPRINT,
        "map": MAP,
        "generatedClass": _name(generated_class),
        "componentCount": len(components),
        "components": sorted(components, key=lambda item: item["name"]),
        "assetModified": False,
        "automaticApproval": False,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking runtime v092 inspection: {output}")


inspect()
