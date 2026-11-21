"""Reduce background-only horizontal disparity without moving the character."""
import json
from pathlib import Path
import unreal


def transform_values(actor):
    position = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return [position.x, position.y, position.z, rotation.pitch, rotation.yaw, rotation.roll, scale.x, scale.y, scale.z]

assert '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
ROOT = Path(__file__).resolve().parents[4]
CONFIG = json.loads((ROOT/'config/looking-glass-room-v015.json').read_text())
DEST = CONFIG['map']
OUT = ROOT/'artifacts/looking-glass-room-v015'
OUT.mkdir(parents=True, exist_ok=True)
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST), 'Preserve prior iterations'
assert unreal.EditorLoadingAndSavingUtils.load_map(CONFIG['fallbackMap'])
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next(a for a in actors if isinstance(a, unreal.SkeletalMeshActor))
mesh = character.skeletal_mesh_component
camera = next(a for a in actors if isinstance(a, unreal.CineCameraActor))
origin = camera.get_actor_location()
forward = camera.get_actor_forward_vector()
right = camera.get_actor_right_vector()
focus = mesh.get_socket_location('head')
distance = (focus-origin).dot(forward)
assert distance > 1
retained = float(CONFIG['backgroundParallaxScale'])
assert 0 <= retained <= 1
character_state = (transform_values(character), [m.get_path_name() for m in mesh.get_materials()])
camera_state = transform_values(camera)
edit = unreal.MaterialEditingLibrary
materials = {}
records = []


def node(material, cls, **props):
    expression = edit.create_material_expression(material, cls)
    assert expression
    for name, value in props.items():
        expression.set_editor_property(name, value)
    return expression


def vector(material, value):
    return node(material, unreal.MaterialExpressionConstant3Vector,
                constant=unreal.LinearColor(value.x, value.y, value.z, 1))


def binary(material, cls, a, b):
    result = node(material, cls)
    assert edit.connect_material_expressions(a, '', result, 'A')
    assert edit.connect_material_expressions(b, '', result, 'B')
    return result


def background_material(source):
    source_path = source.get_path_name()
    if source_path in materials:
        return materials[source_path]
    assert isinstance(source, unreal.Material), source_path
    assert edit.get_material_property_input_node(source, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None, source_path
    destination = '/Game/Gahyeon/Land/Gahyeon/v015/Room/M_Background_%03d' % len(materials)
    material = unreal.EditorAssetLibrary.duplicate_asset(source_path, destination)
    assert material
    # Off-axis projection: x' = x + lateral * (1 - depth/focus) * (1 - retained).
    # The main camera's pitch/yaw are fixed during quilt capture.
    wp = node(material, unreal.MaterialExpressionWorldPosition,
              world_position_shader_offset=unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    cp = node(material, unreal.MaterialExpressionCameraPositionWS)
    center = vector(material, origin)
    fwd = vector(material, forward)
    side = vector(material, right)
    delta = binary(material, unreal.MaterialExpressionSubtract, cp, center)
    lateral = binary(material, unreal.MaterialExpressionDotProduct, delta, side)
    relative = binary(material, unreal.MaterialExpressionSubtract, wp, center)
    depth = binary(material, unreal.MaterialExpressionDotProduct, relative, fwd)
    inv_focus = node(material, unreal.MaterialExpressionConstant, r=1.0/distance)
    ratio = binary(material, unreal.MaterialExpressionMultiply, depth, inv_focus)
    one = node(material, unreal.MaterialExpressionConstant, r=1.0)
    correction = binary(material, unreal.MaterialExpressionSubtract, one, ratio)
    gain = node(material, unreal.MaterialExpressionConstant, r=1-retained)
    amount = binary(material, unreal.MaterialExpressionMultiply, lateral, correction)
    amount = binary(material, unreal.MaterialExpressionMultiply, amount, gain)
    offset = binary(material, unreal.MaterialExpressionMultiply, side, amount)
    assert edit.connect_material_property(offset, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    edit.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    assert edit.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None
    materials[source_path] = material
    return material


for actor in actors:
    if not isinstance(actor, unreal.StaticMeshActor) or not actor.get_actor_label().startswith('Room_'):
        continue
    component = actor.static_mesh_component
    before = transform_values(actor)
    for index, source in enumerate(component.get_materials()):
        if source:
            component.set_material(index, background_material(source))
    # WPO can move vertices beyond the original bounds at side views.
    component.set_editor_property('bounds_scale', 2.0)
    assert transform_values(actor) == before
    records.append(actor.get_actor_label())
assert len(records) > 100
assert (transform_values(character), [m.get_path_name() for m in mesh.get_materials()]) == character_state
assert transform_values(camera) == camera_state
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, DEST)
report = dict(status='candidate', humanApproved=False, source=CONFIG['fallbackMap'], map=DEST,
              character=mesh.get_skeletal_mesh_asset().get_path_name(), characterMaterials=character_state[1],
              characterUnchanged=True, cameraUnchanged=True, actorTransformsUnchanged=True,
              backgroundActors=len(records), backgroundParallaxScale=retained,
              focusDistance=distance, cameraOrigin=[origin.x, origin.y, origin.z],
              cameraForward=[forward.x,forward.y,forward.z], cameraRight=[right.x,right.y,right.z],
              materials={key:value.get_path_name() for key,value in materials.items()}, actors=records)
(OUT/'scene.json').write_text(json.dumps(report, indent=2)+'\n')
