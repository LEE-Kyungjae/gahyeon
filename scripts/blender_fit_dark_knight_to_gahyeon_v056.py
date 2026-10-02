"""Create a non-destructive modular Dark Knight fit proof on the Gahyeon body."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROLE_OBJECTS = {
    "torso": ["Cloth_Upper_Body", "Armor_Upper_Body", "Cloth_Arms"],
    "arms": [
        "Armor_Upper_Arm",
        "Armor_Lower_Arm",
        "Armor_Elbow_Top",
        "Armor_Elbow_Bot",
        "Armor_Shoulder_Bot",
    ],
    "lower": [
        "Cloth_Lower_Body",
        "Cloth_Leg",
        "Armor_Lower_Body",
        "Armor_Upper_Leg",
        "Armor_Lower_Leg",
        "Armor_Knee_Top",
        "Armor_Knee_Bot",
    ],
    "footwear": [
        "Boot",
        "Armor_Feet_Back",
        "Armor_Feet_Front_Bot",
        "Armor_Feet_Front_Mid",
        "Armor_Feet_Front_Top",
    ],
}


def arguments():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-body", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--output-fbx", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world_points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def bounds(objects):
    points = [point for obj in objects for point in world_points(obj)]
    return Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))), Vector(
        (max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))
    )


def select_only(objects):
    for candidate in bpy.data.objects:
        candidate.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


args = arguments()
source_blend = Path(bpy.data.filepath).resolve()
for source in (source_blend, args.target_body):
    if not source.is_file():
        raise RuntimeError(f"missing source: {source}")
for output in (args.output_blend, args.output_fbx, args.preview, args.report):
    if output.exists():
        raise RuntimeError(f"refusing to overwrite v056 output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

selected_names = [name for names in ROLE_OBJECTS.values() for name in names]
missing = [name for name in selected_names if bpy.data.objects.get(name) is None]
if missing:
    raise RuntimeError(f"missing Dark Knight modules: {missing}")
garments = [bpy.data.objects[name] for name in selected_names]

before = set(bpy.data.objects)
bpy.ops.wm.fbx_import(filepath=str(args.target_body.resolve()), use_anim=False)
imported = [obj for obj in bpy.data.objects if obj not in before]
body = next(obj for obj in imported if obj.type == "MESH" and obj.name.endswith("LOD0"))
body.name = "Gahyeon_TargetBody_LOD0"

# The donor is authored at roughly ten Blender units while the exported
# MetaHuman body is in metres. Use complete anatomical anchors instead of
# garment-only bounds so every modular piece receives one coherent transform.
donor_anchors = [bpy.data.objects["Head"], bpy.data.objects["Boot"]]
source_min, source_max = bounds(donor_anchors)
target_min, target_max = bounds([body])
uniform_scale = (target_max.z - target_min.z) / (source_max.z - source_min.z)
source_center = (source_min + source_max) * 0.5
target_center = (target_min + target_max) * 0.5

for garment in garments:
    for vertex in garment.data.vertices:
        source_world = garment.matrix_world @ vertex.co
        fitted_world = target_center + (source_world - source_center) * uniform_scale
        vertex.co = garment.matrix_world.inverted() @ fitted_world
    garment.name = f"DK56_{garment.name}"
    garment.data.name = f"{garment.name}_Mesh"
    garment["gahyeon_iteration"] = "v056"
    garment["source_asset"] = "Female Dark Knight Character"
    garment["fit_state"] = "static-alignment-poc"
    for modifier in list(garment.modifiers):
        if modifier.type == "ARMATURE":
            garment.modifiers.remove(modifier)
    garment.parent = None

keep = set(garments + [body])
for obj in list(bpy.data.objects):
    if obj not in keep and obj.type in {"MESH", "ARMATURE", "EMPTY", "LIGHT", "CAMERA"}:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
select_only(garments)
bpy.ops.export_scene.fbx(
    filepath=str(args.output_fbx.resolve()),
    use_selection=True,
    object_types={"MESH"},
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="COPY",
    embed_textures=True,
)

camera_data = bpy.data.cameras.new("CAM_DarkKnightFitAudit")
camera = bpy.data.objects.new("CAM_DarkKnightFitAudit", camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = (0.0, -4.2, 0.78)
target = Vector((0.0, 0.0, 0.78))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 1.75
bpy.context.scene.camera = camera

world = bpy.context.scene.world or bpy.data.worlds.new("DarkKnightFitAuditWorld")
bpy.context.scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.035, 0.045, 0.065, 1.0)
background.inputs["Strength"].default_value = 0.18
for name, location, energy, size in (
    ("Key", (-2.5, -3.5, 2.7), 700.0, 2.4),
    ("Fill", (2.6, -2.0, 1.7), 420.0, 2.0),
    ("Rim", (0.0, 2.4, 2.5), 650.0, 2.0),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1024
scene.render.resolution_y = 1536
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.filepath = str(args.preview.resolve())
scene.view_settings.look = "Medium High Contrast"
bpy.ops.render.render(write_still=True)

module_report = {}
for role, original_names in ROLE_OBJECTS.items():
    objects = [bpy.data.objects[f"DK56_{name}"] for name in original_names]
    module_report[role] = {
        "objects": [obj.name for obj in objects],
        "vertices": sum(len(obj.data.vertices) for obj in objects),
        "polygons": sum(len(obj.data.polygons) for obj in objects),
        "materials": sorted({slot.material.name for obj in objects for slot in obj.material_slots if slot.material}),
    }

report = {
    "schemaVersion": 1,
    "iteration": "v056",
    "state": "static-alignment-poc",
    "productionReady": False,
    "animationReady": False,
    "hypothesis": "A curated subset of the modular donor armor can preserve its authored detail after one coherent MetaHuman-scale alignment.",
    "inputs": {
        "donorBlend": {"file": str(source_blend), "sha256": sha256(source_blend)},
        "targetBody": {"file": str(args.target_body.resolve()), "sha256": sha256(args.target_body)},
    },
    "normalization": {"uniformScale": uniform_scale, "sourceBounds": [list(source_min), list(source_max)], "targetBounds": [list(target_min), list(target_max)]},
    "excludedForAssistantSilhouette": ["Sword", "Armor_Shoulder_Top", "Armor_Neck_Top", "Armor_Neck_Mid", "Armor_Neck_Bot", "Armor_Hand", "Armor_Fingers"],
    "modules": module_report,
    "outputs": {
        "blend": {"file": str(args.output_blend.resolve()), "sha256": sha256(args.output_blend)},
        "fbx": {"file": str(args.output_fbx.resolve()), "sha256": sha256(args.output_fbx)},
        "preview": {"file": str(args.preview.resolve()), "sha256": sha256(args.preview)},
    },
    "nextGate": "Inspect silhouette and clipping before UE import; retain the separated modules even if the full fantasy styling is rejected.",
}
args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
