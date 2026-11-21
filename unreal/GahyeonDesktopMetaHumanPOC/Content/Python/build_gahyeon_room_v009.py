import json
from pathlib import Path
import unreal

assert '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower(), 'Use scripts/build_gahyeon_room_scene.py'

ROOT = Path(__file__).resolve().parents[4]
SOURCE = '/Game/Gahyeon/Land/Gahyeon/v006/Runtime/L_GahyeonLandMac_v006'
DEST = '/Game/Gahyeon/Land/Gahyeon/v009/Runtime/L_GahyeonRoom_v009'
ASSETS = '/Game/Gahyeon/Land/Gahyeon/v009/Room'
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST), 'Preserve existing iterations'
assert unreal.EditorLoadingAndSavingUtils.load_map(SOURCE)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
original = actors.get_all_level_actors()
character = next(a for a in original if isinstance(a, unreal.SkeletalMeshActor))
mesh = character.get_component_by_class(unreal.SkeletalMeshComponent)
assert 'Gahyeon_Land_Idle_v001' in mesh.get_skeletal_mesh_asset().get_path_name()
mesh.set_editor_property('pause_anims', True)
camera = next(a for a in original if isinstance(a, unreal.CineCameraActor))
camera.camera_component.set_editor_property('current_focal_length', 45.0)
camera.set_actor_rotation(unreal.Rotator(pitch=-1.5, yaw=-90.0, roll=0), False)
fill = actors.spawn_actor_from_class(unreal.RectLight, unreal.Vector(5,100,115), unreal.Rotator(pitch=-20, yaw=-90, roll=0))
fill.set_actor_label('Room_Softbox')
fill.light_component.set_editor_property('intensity', 2500.0)
fill.light_component.set_editor_property('source_width', 120.0)
fill.light_component.set_editor_property('source_height', 100.0)
fill.light_component.set_editor_property('attenuation_radius', 700.0)
fill.light_component.set_editor_property('cast_shadows', False)
tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = {}

def material(name, rgb, emission=0.0):
    m = tools.create_asset(name, ASSETS, unreal.Material, unreal.MaterialFactoryNew())
    assert m
    color = unreal.MaterialEditingLibrary.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', unreal.LinearColor(*rgb, 1))
    unreal.MaterialEditingLibrary.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = unreal.MaterialEditingLibrary.create_material_expression(m, unreal.MaterialExpressionConstant)
    rough.set_editor_property('r', 0.8)
    unreal.MaterialEditingLibrary.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    if emission:
        e = unreal.MaterialEditingLibrary.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
        e.set_editor_property('constant', unreal.LinearColor(*(x*emission for x in rgb), 1))
        unreal.MaterialEditingLibrary.connect_material_property(e, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    materials[name] = m
    return m

wall = material('M_Plaster', (.43,.39,.33), .35)
oak = material('M_Oak', (.25,.13,.065), .08)
oak_light = material('M_OakLight', (.33,.19,.10), .08)
cream = material('M_Cream', (.70,.61,.45), .12)
teal = material('M_Sage', (.09,.23,.21), .12)
dark = material('M_Ink', (.025,.045,.06), .1)
pink = material('M_Clay', (.42,.19,.14), .1)
green = material('M_Leaf', (.06,.20,.10), .12)
sky = material('M_WindowBlue', (.08,.20,.35), .8)
glow = material('M_Lamp', (.9,.6,.28), 2.0)
created = []

def shape(name, xyz, size, mat, primitive='Cube', rotation=None):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(xyz[0],xyz[1],xyz[2]+20))
    a.set_actor_label('Room_' + name)
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/' + primitive))
    c.set_material(0, mat)
    c.set_mobility(unreal.ComponentMobility.STATIC)
    a.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)))
    if rotation:
        a.set_actor_rotation(unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), False)
    created.append(a)
    return a

# Dimensions match the retained character (about 110 cm tall).
# Open front; shallow depth keeps distant surfaces readable in the light field.
shape('Floor', (5,-25,-5), (200,190,5), oak)
for i in range(16):
    shape('FloorBoard%02d'%i, (-89+i*12,-25,-2.4), (11.7,190,.2), oak_light if i%3 else oak)
shape('BackWall', (5,-89,75), (200,4,160), wall)
shape('LeftWall', (-94,-34,75), (4,110,160), wall)
shape('RightWall', (104,-34,75), (4,110,160), wall)
shape('Skirting', (5,-86,1), (196,2,7), cream)
shape('Rug', (5,-5,-1.8), (77,62,.6), teal)
shape('RugInner', (5,-5,-1.4), (71,56,.3), cream)

# A recessed blue window with simple architectural framing.
shape('Window', (-37,-86,87), (51,1,59), sky)
for x in (-64,-10):
    shape('WindowJamb', (x,-84,87), (3,4,65), oak_light)
for z in (55,119):
    shape('WindowRail', (-37,-84,z), (57,4,3), oak_light)
shape('WindowMullion', (-37,-83,87), (2,3,61), cream)
shape('WindowCrossbar', (-37,-83,87), (53,3,2), cream)
shape('WindowSill', (-37,-81,54), (61,10,3), cream)

# Compact desk and stool, kept outside the character silhouette.
shape('DeskTop', (48,-60,36), (54,30,3), oak_light)
for x in (26,70):
    for y in (-71,-49):
        shape('DeskLeg', (x,y,16), (3,3,36), oak)
shape('DeskDrawer', (48,-60,30), (47,25,8), cream)
shape('DrawerHandle', (48,-46,30), (9,1,1), dark)
shape('StoolSeat', (54,-31,21), (22,22,5), teal, 'Cylinder')
for x in (47,61):
    for y in (-38,-24):
        shape('StoolLeg', (x,y,8), (2.5,2.5,23), oak)
shape('Notebook', (45,-56,38), (13,10,1), pink)
shape('Mug', (64,-57,40), (5,5,7), cream, 'Cylinder')

# Two shelves and irregular book heights break up the background without text.
for shelf,z in enumerate((70,98)):
    shape('Shelf', (49,-82,z), (57,12,2), oak_light)
    for i in range(6):
        h = (12,16,13,18,14,11)[i]
        shape('Book%d_%d'%(shelf,i), (28+i*4.5,-81,z+1+h/2), (3.5,6,h), (teal,cream,pink,dark)[(i+shelf)%4])
shape('Frame', (69,-83,82), (11,2,16), cream)
shape('FrameArt', (69,-81.8,82), (8,.3,12), teal)

# Warm floor lamp and a small potted plant.
shape('LampBase', (-47,-39,0), (16,16,3), dark, 'Cylinder')
shape('LampStem', (-47,-39,31), (1.5,1.5,62), oak, 'Cylinder')
shape('LampShade', (-47,-39,66), (23,23,15), cream, 'Cylinder')
shape('LampDiffuser', (-47,-39,58), (19,19,.6), glow, 'Cylinder')
shape('PlantPot', (-68,-65,7), (16,16,18), pink, 'Cylinder')
for i,(dx,dy,dz) in enumerate(((-6,0,25),(5,2,29),(0,-3,36),(-3,4,33))):
    shape('PlantStem%d'%i, (-68+dx/2,-65+dy/2,16+dz/4), (1,1,dz/2), oak, 'Cylinder')
    shape('PlantLeaf%d'%i, (-68+dx,-65+dy,dz), (12,5,19), green, 'Sphere', (0, i*35, i*12-18))

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, DEST)
out = ROOT / 'artifacts/looking-glass-room-v003'
out.mkdir(parents=True, exist_ok=True)
(out/'scene.json').write_text(json.dumps(dict(status='candidate',humanApproved=False,source=SOURCE,map=DEST,
    roomActors=len(created),materialPaths=[m.get_path_name() for m in materials.values()],
    character=mesh.get_skeletal_mesh_asset().get_path_name(), characterMaterials=[m.get_path_name() for m in mesh.get_materials()],
    cameraLocation=str(camera.get_actor_location()), cameraRotation=str(camera.get_actor_rotation()), sockets={str(n):str(mesh.get_socket_location(n)) for n in mesh.get_all_socket_names() if 'foot' in str(n).lower()}),indent=2))
