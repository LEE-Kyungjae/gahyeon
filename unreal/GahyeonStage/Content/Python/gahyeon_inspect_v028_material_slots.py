"""Log actual material slots from the already-open v028 preview map."""

import unreal


actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.MeshComponent):
        for slot in range(component.get_num_materials()):
            material = component.get_material(slot)
            unreal.log(
                "GAHYEON_SLOT "
                f"actor={actor.get_actor_label()} component={component.get_name()} "
                f"slot={slot} material={material.get_path_name() if material else 'None'}"
            )
