"""Shallow architectural room; original procedural textures, no third-party assets."""
import hashlib
import json
from pathlib import Path
import unreal

assert '-run=pythonscript' in unreal.SystemLibrary.get_command_line().lower()
ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'artifacts/looking-glass-room-v012'
SOURCE = '/Game/Gahyeon/Land/Gahyeon/v011/Runtime/L_GahyeonRoom_v011'
DEST = '/Game/Gahyeon/Land/Gahyeon/v012/Runtime/L_GahyeonRoom_v012'
ASSETS = '/Game/Gahyeon/Land/Gahyeon/v012/Room'
assert not unreal.EditorAssetLibrary.does_asset_exist(DEST), 'Preserve existing iteration'
assert unreal.EditorLoadingAndSavingUtils.load_map(SOURCE)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
original = actors.get_all_level_actors()
character = next(a for a in original if isinstance(a, unreal.SkeletalMeshActor))
mesh = character.get_component_by_class(unreal.SkeletalMeshComponent)
camera = next(a for a in original if isinstance(a, unreal.CineCameraActor))
origin = camera.get_actor_location()
anchor = mesh.get_socket_location('head').y
tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = {}
textures = {}
for name in ('oak', 'plaster', 'linen', 'sky'):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(OUT / 'textures' / (name + '.png')))
    task.set_editor_property('destination_path', ASSETS)
    task.set_editor_property('destination_name', 'T_' + name)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', True)
    tools.import_asset_tasks([task])
    textures[name] = unreal.load_asset(task.get_editor_property('imported_object_paths')[0])


def material(name, rgb, roughness=.8, texture=None, emission=0):
    m = tools.create_asset('M_' + name, ASSETS, unreal.Material, unreal.MaterialFactoryNew())
    assert m
    edit = unreal.MaterialEditingLibrary
    color = edit.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', unreal.LinearColor(*rgb, 1))
    output = color
    if texture:
        tex = edit.create_material_expression(m, unreal.MaterialExpressionTextureSample)
        tex.set_editor_property('texture', textures[texture])
        mult = edit.create_material_expression(m, unreal.MaterialExpressionMultiply)
        edit.connect_material_expressions(tex, 'RGB', mult, 'A')
        edit.connect_material_expressions(color, '', mult, 'B')
        output = mult
    edit.connect_material_property(output, '', unreal.MaterialProperty.MP_BASE_COLOR)
    value = edit.create_material_expression(m, unreal.MaterialExpressionConstant)
    value.set_editor_property('r', roughness)
    edit.connect_material_property(value, '', unreal.MaterialProperty.MP_ROUGHNESS)
    if emission:
        gain = edit.create_material_expression(m, unreal.MaterialExpressionMultiply)
        gain.set_editor_property('const_b', emission)
        edit.connect_material_expressions(output, '', gain, 'A')
        edit.connect_material_property(gain, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    edit.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    materials[name] = m
    return m


oak = material('Oak', (.75,.65,.52), .62, 'oak', .06)
wall = material('Plaster', (.82,.84,.83), .95, 'plaster', .22)
linen = material('Linen', (.85,.83,.75), .98, 'linen', .12)
trim = material('Ivory', (.65,.60,.49), .65, emission=.1)
ink = material('Ink', (.035,.048,.045), .5)
brass = material('Brass', (.35,.23,.09), .32)
sky = material('Sky', (.8,.85,.9), 1, 'sky', .65)
far = material('FarBuildings', (.17,.23,.27), 1, emission=.28)
near = material('NearBuildings', (.25,.29,.29), 1, emission=.2)
leaf = material('AutumnLeaf', (.36,.20,.065), .9, emission=.15)
leaf_gold = material('AutumnGold', (.52,.34,.10), .9, emission=.18)
window = material('DistantWindow', (.50,.52,.43), 1, emission=.3)
created = []


def shape(name, xyz, size, mat, primitive='Cube', rotation=None):
    # Same projective depth compression as v011: retain the baseline front composition.
    x,y,z = xyz
    z += 20
    new_y = anchor + (y-anchor)*.35
    ratio = (origin.y-new_y)/(origin.y-y)
    loc = unreal.Vector(origin.x+(x-origin.x)*ratio, new_y, origin.z+(z-origin.z)*ratio)
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, loc)
    a.set_actor_label('Room_Detail_' + name)
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/' + primitive))
    c.set_material(0, mat)
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_editor_property('cast_shadow', False)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    a.set_actor_scale3d(unreal.Vector(size[0]*ratio/100, size[1]*.35/100, size[2]*ratio/100))
    if rotation:
        a.set_actor_rotation(unreal.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]), False)
    created.append(a)
    return a


for actor in original:
    if not isinstance(actor, unreal.StaticMeshActor):
        continue
    label = actor.get_actor_label()
    replacement = None
    if label.startswith(('Room_BackWall','Room_LeftWall','Room_RightWall')):
        replacement = wall
    elif label.startswith(('Room_Floor', 'Room_DeskTop','Room_DeskLeg','Room_Shelf','Room_WindowJamb','Room_WindowRail')):
        replacement = oak
    elif label.startswith(('Room_RugInner','Room_LampShade')):
        replacement = linen
    elif label == 'Room_Window':
        replacement = sky
    if replacement:
        actor.static_mesh_component.set_material(0, replacement)

# Architectural edges and lower wall panels are large enough to survive the Go's tiles.
for z,width,depth in ((6,196,2),(47,196,2.2),(49,196,1.2),(145,196,3),(149,199,5)):
    shape('WallRail_%s'%z,(5,-85,z),(width,depth,2),trim)
for i,x in enumerate((-79,-55,-31,-7,17,41,65,89)):
    shape('Wainscot_%d'%i,(x,-85,26),(1.4,1.5,38),trim)
# Recess shadow, layered casing and a projecting sill.
for side,x in enumerate((-66,-8)):
    shape('WindowShadow%d'%side,(x,-83.5,87),(5,1,68),ink)
    shape('WindowCasing%d'%side,(x,-81.5,87),(3.5,3,68),trim)
for z in (53,121):
    shape('WindowCasingHorizontal%s'%z,(-37,-81.5,z),(62,3,3),trim)
shape('WindowSillLip',(-37,-75.5,53),(65,2,2),oak)
shape('WindowApron',(-37,-82,49),(54,2,5),trim)
# Opaque exterior layers remain inside the existing window; no distant deep geometry.
for i,(x,w,h) in enumerate(((-59,6,15),(-50,10,22),(-38,9,17),(-25,12,25),(-15,5,19))):
    shape('SkylineFar%d'%i,(x,-85.5,58+h/2),(w,.3,h),far)
for i,(x,w,h) in enumerate(((-57,10,9),(-43,11,13),(-27,12,10),(-16,6,7))):
    shape('SkylineNear%d'%i,(x,-85,58+h/2),(w,.3,h),near)
    for row in range(max(1,int(h/4))):
        for col in (-1,1):
            shape('CityWindow%d_%d_%d'%(i,row,col),(x+col*w*.23,-84.7,60+row*3.4),(1,.12,1.5),window)
# Autumn branch on the side of the window, away from the face silhouette.
shape('Branch',(-57,-84.4,91),(1,.4,40),oak,'Cylinder', (0,0,-8))
for i,(x,z,s) in enumerate(((-60,109,6),(-54,105,7),(-60,99,5),(-52,97,6),(-56,91,5),(-61,87,4))):
    shape('Leaf%d'%i,(x,-84.2,z),(s,.4,s*.65),leaf if i%2 else leaf_gold,'Sphere')
# Curtain folds and rod create depth without a simulation or translucent overdraw.
shape('CurtainRod',(-37,-77,125),(69,1.3,1.3),brass)
for side,x in enumerate((-69,-5)):
    for fold in range(4):
        shape('Curtain%d_%d'%(side,fold),(x+fold*1.5,-78+(fold%2)*.9,88),(2.2,2.2,68),linen,'Cylinder')
    shape('CurtainTie%d'%side,(x+2.3,-76,77),(7,1.6,1.8),brass)
# Split drawer front, shadow seams, readable pulls and a desk edge.
shape('DeskEdge',(48,-44.5,35.5),(55,1.3,2.2),oak)
shape('DrawerShadow',(48,-47.1,30),(47,.5,8.2),ink)
for i,x in enumerate((36,60)):
    shape('DrawerFace%d'%i,(x,-46.4,30),(22.7,1,7.2),trim)
    shape('DrawerPull%d'%i,(x,-45.4,30),(6,1,1.2),brass)
for x in (27,69):
    shape('DeskApron%s'%x,(x,-60,28),(2,24,9),oak)
for shelf,z in enumerate((70,98)):
    for x in (28,70):
        shape('ShelfBracket%s_%s'%(z,x),(x,-80,z-5),(1.8,6,9),brass)
    shape('ShelfLip%s'%z,(49,-75.8,z),(57,1,2.5),oak)
shape('NotebookPages',(45,-56,38.6),(12.4,9.5,.5),trim)
shape('MugCoffee',(64,-57,43.6),(3.8,3.8,.15),ink,'Cylinder')
# Rug binding and subtle broad bands retain legibility at low per-view resolution.
for x in (-29,39):
    shape('RugBinding%s'%x,(x,-5,-1),(1,54,.25),oak)
for y in (-26,16):
    shape('RugBand%s'%y,(5,y,-1),(67,1.5,.25),oak)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, DEST)
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'scene.json').write_text(json.dumps(dict(status='candidate',humanApproved=False,source=SOURCE,map=DEST,
    character=mesh.get_skeletal_mesh_asset().get_path_name(),characterMaterials=[m.get_path_name() for m in mesh.get_materials()],
    addedActors=len(created),actorLabels=[a.get_actor_label() for a in created],
    textureHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'textures').glob('*.png')},
    environmentMode='static-autumn-daylight-art-direction',liveWeather=False,roomDepthScale=.35),indent=2)+'\n')
