"""Keep Diana's waist NeoBelt/weapon islands world-stable under the skeleton Root."""

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path("/Users/ze/work/gahyeonbot")
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/SK_Diana_ShoulderOccluded_v417.fbx"
OUTPUT_ROOT = ROOT / "artifacts/gahyeon-ch/iterations/v446-diana-belt-attachment-world-stable"
OUTPUT_FBX = OUTPUT_ROOT / "SK_Diana_BeltAttachmentWorldStable_v446.fbx"
REPORT = OUTPUT_ROOT / "report.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connected_components(mesh, polygon_indices):
    vertex_to_polygons = {}
    for polygon_index in polygon_indices:
        for vertex in mesh.polygons[polygon_index].vertices:
            vertex_to_polygons.setdefault(vertex, set()).add(polygon_index)
    remaining = set(polygon_indices)
    result = []
    while remaining:
        seed = remaining.pop(); component = {seed}; stack = [seed]
        while stack:
            for vertex in mesh.polygons[stack.pop()].vertices:
                for neighbor in vertex_to_polygons.get(vertex, ()):
                    if neighbor in remaining:
                        remaining.remove(neighbor); component.add(neighbor); stack.append(neighbor)
        result.append(component)
    return result


def main():
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v446 output: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    mesh_object = max((obj for obj in bpy.data.objects if obj.type == "MESH"), key=lambda obj: len(obj.data.polygons))
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    mesh = mesh_object.data
    belt_index = next(index for index, slot in enumerate(mesh_object.material_slots)
                      if slot.material and slot.material.name.startswith("ch0100_40_NeoBelt"))
    components = connected_components(mesh, [p.index for p in mesh.polygons if p.material_index == belt_index])
    selected_components, selected_vertices = [], set()
    for component_index, component in enumerate(components):
        vertices = {v for polygon_index in component for v in mesh.polygons[polygon_index].vertices}
        maximum_z = max(mesh.vertices[v].co.z for v in vertices)
        if maximum_z < 60.0:
            selected_vertices.update(vertices)
            selected_components.append({"componentIndex": component_index, "faceCount": len(component),
                                        "vertexCount": len(vertices), "maximumZCentimeters": round(maximum_z, 5)})
    if not selected_vertices:
        raise RuntimeError("no waist NeoBelt vertices qualified for Root anchoring")
    root_group = mesh_object.vertex_groups.get("Root")
    if root_group is None:
        root_group = mesh_object.vertex_groups.get("root")
    if root_group is None:
        root_group = mesh_object.vertex_groups.new(name="root")
    selected = sorted(selected_vertices)
    for group in mesh_object.vertex_groups:
        group.remove(selected)
    root_group.add(selected, 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT"); armature.select_set(True); mesh_object.select_set(True)
    bpy.context.view_layer.objects.active = mesh_object
    bpy.ops.export_scene.fbx(filepath=str(OUTPUT_FBX), use_selection=True, object_types={"ARMATURE", "MESH"},
                             apply_unit_scale=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE")
    report = {
        "schemaVersion": 1, "iteration": "v446", "status": "draft-world-stable-belt-attachment-reweight",
        "source": {"path": str(SOURCE), "sha256": sha256(SOURCE)},
        "output": {"path": str(OUTPUT_FBX), "sha256": sha256(OUTPUT_FBX)},
        "materialIndex": belt_index, "selectionRule": "connected NeoBelt components with reference maximum Z below 60 cm",
        "selectedComponentCount": len(selected_components), "selectedVertexCount": len(selected_vertices),
        "selectedComponents": selected_components, "replacementInfluence": {"bone": root_group.name, "weight": 1.0},
        "expectedResult": "waist weapons keep their authored hanging orientation instead of inheriting the retargeted Hip rotation",
        "tradeoff": "root anchor is an orientation repair candidate; dedicated secondary dynamics remain a later deformation stage",
        "visualValidationPending": True, "humanApproved": False, "productionReady": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


main()
