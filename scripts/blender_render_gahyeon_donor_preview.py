"""Render a deterministic full-body donor preview without modifying the source file."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector


argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if len(argv) != 1:
    raise SystemExit("usage: blender source.blend --python script.py -- output.png")
output = Path(argv[0])
if output.exists():
    raise RuntimeError(f"refusing to overwrite donor preview: {output}")
output.parent.mkdir(parents=True, exist_ok=True)

for obj in bpy.data.objects:
    if obj.type == "MESH" and (obj.name.startswith("WGT-") or obj.name == "Sword"):
        obj.hide_render = True

camera_data = bpy.data.cameras.new("CAM_DonorAudit")
camera = bpy.data.objects.new("CAM_DonorAudit", camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = (0.0, -21.0, 4.8)
target = Vector((0.0, -0.2, 4.8))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 10.8
bpy.context.scene.camera = camera

world = bpy.context.scene.world or bpy.data.worlds.new("DonorAuditWorld")
bpy.context.scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.055, 0.065, 0.085, 1.0)
background.inputs["Strength"].default_value = 0.35

for name, location, energy, size in (
    ("Key", (-5.0, -8.0, 9.0), 1500.0, 5.0),
    ("Fill", (5.0, -5.0, 6.0), 900.0, 4.0),
    ("Rim", (0.0, 4.0, 8.0), 1200.0, 4.0),
):
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
scene.render.filepath = str(output.resolve())
scene.view_settings.look = "Medium High Contrast"
scene.render.image_settings.color_mode = "RGBA"
bpy.ops.render.render(write_still=True)
if not output.is_file() or output.stat().st_size < 1024:
    raise RuntimeError(f"donor preview render failed: {output}")
print(f"rendered donor preview: {output}")
