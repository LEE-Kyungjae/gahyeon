"""Fit only real armor modules with a shared anatomical height mapping."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROLES = {
    "torso": ["Armor_Upper_Body"],
    "arms": ["Armor_Upper_Arm", "Armor_Lower_Arm", "Armor_Elbow_Top", "Armor_Elbow_Bot", "Armor_Shoulder_Bot"],
    "lower": ["Armor_Lower_Body", "Armor_Upper_Leg", "Armor_Lower_Leg", "Armor_Knee_Top", "Armor_Knee_Bot"],
    "footwear": ["Armor_Feet_Back", "Armor_Feet_Front_Bot", "Armor_Feet_Front_Mid", "Armor_Feet_Front_Top"],
}


def arguments():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-body", required=True, type=Path)
    parser.add_argument("--output-blend", required=True, type=Path)
    parser.add_argument("--front-preview", required=True, type=Path)
    parser.add_argument("--side-preview", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args(values)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def points(objects):
    return [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]


def bounds(values):
    return (
        Vector(tuple(min(getattr(point, axis) for point in values) for axis in "xyz")),
        Vector(tuple(max(getattr(point, axis) for point in values) for axis in "xyz")),
    )


def map_piecewise(value, source_nodes, target_nodes):
    for index in range(len(source_nodes) - 1):
        low, high = source_nodes[index], source_nodes[index + 1]
        if value <= high or index == len(source_nodes) - 2:
            ratio = (value - low) / max(high - low, 1e-6)
            return target_nodes[index] + ratio * (target_nodes[index + 1] - target_nodes[index])
    return target_nodes[-1]


def render(scene, camera, output):
    scene.camera = camera
    scene.render.filepath = str(output.resolve())
    bpy.ops.render.render(write_still=True)
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"render failed: {output}")


args = arguments()
source = Path(bpy.data.filepath).resolve()
for output in (args.output_blend, args.front_preview, args.side_preview, args.report):
    if output.exists():
        raise RuntimeError(f"refusing to overwrite v059 output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

before = set(bpy.data.objects)
bpy.ops.wm.fbx_import(filepath=str(args.target_body.resolve()), use_anim=False)
body = next(obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH" and obj.name.endswith("LOD0"))
body.name = "Gahyeon_TargetBody_LOD0"
body_points = points([body])
body_min, body_max = bounds(body_points)
height = body_max.z - body_min.z
target_regions = {
    "footwear": [p for p in body_points if p.z <= body_min.z + height * 0.15],
    "lower": [p for p in body_points if body_min.z + height * 0.10 <= p.z <= body_min.z + height * 0.66 and abs(p.x) < 0.27],
    "torso": [p for p in body_points if body_min.z + height * 0.58 <= p.z <= body_max.z and abs(p.x) < 0.28],
    "arms": [p for p in body_points if body_min.z + height * 0.54 <= p.z <= body_min.z + height * 0.90 and abs(p.x) > 0.18],
}

# Shared landmarks keep overlaps continuous across modular role boundaries.
source_z = [-0.0044425484, 1.17799008, 7.05526733, 8.31233406]
target_z = [body_min.z, body_min.z + height * 0.15, body_min.z + height * 0.66, body_max.z]
fit = {}
armor = []
for role, names in ROLES.items():
    objects = [bpy.data.objects.get(name) for name in names]
    if any(obj is None for obj in objects):
        raise RuntimeError(f"missing armor objects for {role}")
    armor.extend(objects)
    source_min, source_max = bounds(points(objects))
    target_min, target_max = bounds(target_regions[role])
    source_center = (source_min + source_max) * 0.5
    target_center = (target_min + target_max) * 0.5
    source_size = source_max - source_min
    target_size = target_max - target_min
    scale_x = target_size.x / source_size.x * {"torso": 1.035, "arms": 1.04, "lower": 1.04, "footwear": 1.06}[role]
    raw_y = target_size.y / source_size.y * {"torso": 1.055, "arms": 1.04, "lower": 1.055, "footwear": 1.06}[role]
    scale_y = max(0.16, min(raw_y, 0.27))
    for obj in objects:
        inverse = obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            fitted = Vector((
                target_center.x + (world.x - source_center.x) * scale_x,
                target_center.y + (world.y - source_center.y) * scale_y,
                map_piecewise(world.z, source_z, target_z),
            ))
            vertex.co = inverse @ fitted
        obj.name = f"DK59_{obj.name}"
        obj.data.name = f"{obj.name}_Mesh"
        obj["gahyeon_iteration"] = "v059"
        obj["fit_role"] = role
        for modifier in list(obj.modifiers):
            if modifier.type == "ARMATURE":
                obj.modifiers.remove(modifier)
        obj.parent = None
    fit[role] = {"objects": [obj.name for obj in objects], "scaleX": scale_x, "scaleY": scale_y}

keep = set(armor + [body])
for obj in list(bpy.data.objects):
    if obj not in keep and obj.type in {"MESH", "ARMATURE", "EMPTY", "CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

body_material = bpy.data.materials.new("MAT_MetaHumanFitOverlay")
body_material.diffuse_color = (0.12, 0.34, 0.55, 1.0)
body.data.materials.clear()
body.data.materials.append(body_material)
target = Vector((0.0, -0.04, body_min.z + height * 0.51))
camera_data = bpy.data.cameras.new("CAM_DK59_FitAudit")
camera = bpy.data.objects.new("CAM_DK59_FitAudit", camera_data)
bpy.context.scene.collection.objects.link(camera)
camera_data.type = "ORTHO"
camera_data.ortho_scale = height * 1.13
world = bpy.context.scene.world or bpy.data.worlds.new("DK59World")
bpy.context.scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.025, 0.03, 0.045, 1.0)
background.inputs["Strength"].default_value = 0.15
for name, location, energy, size in (("Key", (-2.2, -3.0, 2.4), 520.0, 2.2), ("Fill", (2.1, -2.0, 1.5), 360.0, 1.8), ("Rim", (0.0, 2.2, 2.2), 540.0, 1.8)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1024
scene.render.resolution_y = 1536
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.look = "Medium High Contrast"
camera.location = (0.0, -4.2, target.z)
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
render(scene, camera, args.front_preview)
camera.location = (4.2, 0.0, target.z)
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
render(scene, camera, args.side_preview)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
report = {
    "schemaVersion": 1,
    "iteration": "v059",
    "state": "armor-only-piecewise-static-poc",
    "productionReady": False,
    "animationReady": False,
    "replaces": "v058 rejected before UE import because donor skin chunks were misclassified as garments and independent Z fits broke seams",
    "excludedDonorSkinObjects": ["Cloth_Upper_Body", "Cloth_Arms", "Cloth_Lower_Body", "Cloth_Leg", "Boot"],
    "sharedHeightMapping": {"source": source_z, "target": target_z},
    "roles": fit,
    "inputs": {"donorBlend": {"file": str(source), "sha256": sha256(source)}, "targetBody": {"file": str(args.target_body.resolve()), "sha256": sha256(args.target_body)}},
    "outputs": {"blend": {"file": str(args.output_blend.resolve()), "sha256": sha256(args.output_blend)}, "frontPreview": {"file": str(args.front_preview.resolve()), "sha256": sha256(args.front_preview)}, "sidePreview": {"file": str(args.side_preview.resolve()), "sha256": sha256(args.side_preview)}},
    "nextGate": "Reject unless the MetaHuman body fills intentional armor openings and all armor bands align in both views.",
}
args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
