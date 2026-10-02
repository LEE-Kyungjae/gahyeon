"""Render Diana NeoBelt connected components with stable diagnostic colors."""

import colorsys
import json
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


ROOT = Path("/Users/ze/work/gahyeonbot")
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/SK_Diana_ShoulderOccluded_v417.fbx"
OUTPUT = ROOT / "artifacts/gahyeon-ch/iterations/v439-diana-belt-component-diagnostic"


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable diagnostic: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    mesh_object = max(
        (obj for obj in bpy.data.objects if obj.type == "MESH"),
        key=lambda obj: len(obj.data.polygons),
    )
    mesh = mesh_object.data
    original_material_count = len(mesh_object.material_slots)
    belt_index = next(
        index for index, slot in enumerate(mesh_object.material_slots)
        if slot.material and slot.material.name.startswith("ch0100_40_NeoBelt")
    )
    belt_polygons = {polygon.index for polygon in mesh.polygons if polygon.material_index == belt_index}
    vertex_to_polygons = {}
    for polygon_index in belt_polygons:
        for vertex in mesh.polygons[polygon_index].vertices:
            vertex_to_polygons.setdefault(vertex, set()).add(polygon_index)
    components = []
    remaining = set(belt_polygons)
    while remaining:
        seed = remaining.pop()
        component = {seed}
        stack = [seed]
        while stack:
            polygon_index = stack.pop()
            for vertex in mesh.polygons[polygon_index].vertices:
                for neighbor in vertex_to_polygons.get(vertex, ()):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        component.add(neighbor)
                        stack.append(neighbor)
        components.append(component)
    components.sort(key=lambda item: (-len(item), min(item)))
    records = []
    for index, component in enumerate(components):
        hue = (index * 0.61803398875) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
        material = bpy.data.materials.new(f"BeltComponent_{index:03d}")
        material.diffuse_color = (*rgb, 1.0)
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        principled.inputs["Base Color"].default_value = (*rgb, 1.0)
        principled.inputs["Roughness"].default_value = 0.7
        mesh_object.data.materials.append(material)
        material_index = len(mesh_object.data.materials) - 1
        vertices = set()
        for polygon_index in component:
            polygon = mesh.polygons[polygon_index]
            polygon.material_index = material_index
            vertices.update(polygon.vertices)
        coords = [mesh.vertices[vertex].co for vertex in vertices]
        lower = [min(value[axis] for value in coords) for axis in range(3)]
        upper = [max(value[axis] for value in coords) for axis in range(3)]
        records.append({
            "id": index,
            "color": [round(value, 5) for value in rgb],
            "faceCount": len(component),
            "vertexCount": len(vertices),
            "boundsMin": [round(value, 5) for value in lower],
            "boundsMax": [round(value, 5) for value in upper],
        })
    diagnostic_mesh = bmesh.new()
    diagnostic_mesh.from_mesh(mesh)
    bmesh.ops.delete(
        diagnostic_mesh,
        geom=[face for face in diagnostic_mesh.faces if face.material_index < original_material_count],
        context="FACES",
    )
    diagnostic_mesh.to_mesh(mesh)
    diagnostic_mesh.free()
    mesh_object.hide_render = False
    mesh_object.hide_set(False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("DianaBeltDiagnosticWorld_v438")
    scene.world.color = (0.015, 0.015, 0.015)
    camera_data = bpy.data.cameras.new("CAM_BeltComponents_v434")
    camera = bpy.data.objects.new("CAM_BeltComponents_v434", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0.0, -3.0, 0.62)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.75
    look_at(camera, (0.0, 0.0, 0.58))
    scene.camera = camera
    light_data = bpy.data.lights.new("Key", "AREA")
    light_data.energy = 1800
    light_data.shape = "DISK"
    light_data.size = 120
    light = bpy.data.objects.new("Key", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (0.0, -1.0, 1.0)
    look_at(light, (0.0, 0.0, 0.55))
    scene.render.filepath = str(OUTPUT / "belt-components-front.png")
    bpy.ops.render.render(write_still=True)
    (OUTPUT / "report.json").write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v439",
        "status": "read-only-colored-component-diagnostic",
        "source": str(SOURCE),
        "materialIndex": belt_index,
        "materialName": "ch0100_40_NeoBelt",
        "componentCount": len(records),
        "components": records,
        "humanApproved": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")


main()
