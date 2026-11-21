"""Reload saved maps and check that only room material slots/bounds changed."""
import json
import math
from pathlib import Path
import unreal


def transform_values(actor):
    position = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return [position.x, position.y, position.z, rotation.pitch, rotation.yaw, rotation.roll, scale.x, scale.y, scale.z]

root = Path(__file__).resolve().parents[4]
config = json.loads((root/'config/looking-glass-room-v015.json').read_text())
subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.EditorLoadingAndSavingUtils.load_map(config['fallbackMap'])
source = subsystem.get_all_level_actors()
baseline = {a.get_actor_label():transform_values(a) for a in source}
character = next(a for a in source if isinstance(a, unreal.SkeletalMeshActor)).skeletal_mesh_component
identity = character.get_skeletal_mesh_asset().get_path_name()
materials = [m.get_path_name() for m in character.get_materials()]
assert unreal.EditorLoadingAndSavingUtils.load_map(config['map'])
actors = subsystem.get_all_level_actors()
actual = {a.get_actor_label():transform_values(a) for a in actors}
(root/'artifacts/looking-glass-room-v015/transform-comparison.json').write_text(json.dumps(dict(baseline=baseline,actual=actual),indent=2))
assert actual.keys() == baseline.keys()
for label in baseline:
    assert all(math.isclose(a,b,rel_tol=0,abs_tol=1e-6) for a,b in zip(actual[label],baseline[label])), label
character = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor)).skeletal_mesh_component
assert character.get_skeletal_mesh_asset().get_path_name() == identity == config['character']
assert [m.get_path_name() for m in character.get_materials()] == materials
background = [a for a in actors if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith('Room_')]
assert len(background) > 100
for actor in background:
    for material in actor.static_mesh_component.get_materials():
        assert material.get_path_name().startswith('/Game/Gahyeon/Land/Gahyeon/v015/Room/')
        assert unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None
(root/'artifacts/looking-glass-room-v015/scene-validation.json').write_text(json.dumps(dict(
    passed=True, characterIdentityPreserved=True, originalMaterialsPreserved=True,
    allActorTransformsPreserved=True, backgroundActors=len(background), humanApproved=False), indent=2)+'\n')
