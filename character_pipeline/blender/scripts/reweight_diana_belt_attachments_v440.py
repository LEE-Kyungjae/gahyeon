"""Rigidly anchor Diana's waist NeoBelt/weapon islands to Hip."""

import hashlib
import json
from pathlib import Path

import bpy


ROOT = Path("/Users/ze/work/gahyeonbot")
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v417-diana-shoulder-shell-clearance/SK_Diana_ShoulderOccluded_v417.fbx"
OUTPUT_ROOT = ROOT / "artifacts/gahyeon-ch/iterations/v440-diana-belt-attachment-rigid-hip"
OUTPUT_FBX = OUTPUT_ROOT / "SK_Diana_BeltAttachmentRigidHip_v440.fbx"
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
        seed = remaining.pop()
        component = {seed}
        stack = [seed]
        while stack:
            for vertex in mesh.polygons[stack.pop()].vertices:
                for neighbor in vertex_to_polygons.get(vertex, ()):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        component.add(neighbor)
                        stack.append(neighbor)
        result.append(component)
    return result


def main():
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v440 output: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    mesh_object = max(
        (obj for obj in bpy.data.objects if obj.type == "MESH"),
        key=lambda obj: len(obj.data.polygons),
    )
    armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    mesh = mesh_object.data
    belt_index = next(
        index for index, slot in enumerate(mesh_object.material_slots)
        if slot.material and slot.material.name.startswith("ch0100_40_NeoBelt")
    )
    belt_polygons = [polygon.index for polygon in mesh.polygons if polygon.material_index == belt_index]
    components = connected_components(mesh, belt_polygons)
    selected_components = []
    selected_vertices = set()
    for component_index, component in enumerate(components):
        vertices = {vertex for polygon_index in component for vertex in mesh.polygons[polygon_index].vertices}
        maximum_z = max(mesh.vertices[vertex].co.z for vertex in vertices)
        if maximum_z < 60.0:
            selected_vertices.update(vertices)
            selected_components.append({
                "componentIndex": component_index,
                "faceCount": len(component),
                "vertexCount": len(vertices),
                "maximumZCentimeters": round(maximum_z, 5),
            })
    if not selected_vertices:
        raise RuntimeError("no waist NeoBelt vertices qualified for rigid Hip anchoring")
    hip = mesh_object.vertex_groups.get("Hip")
    if hip is None:
        raise RuntimeError("Diana Hip vertex group is missing")
    selected_list = sorted(selected_vertices)
    for group in mesh_object.vertex_groups:
        group.remove(selected_list)
    hip.add(selected_list, 1.0, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    armature.select_set(True)
    mesh_object.select_set(True)
    bpy.context.view_layer.objects.active = mesh_object
    bpy.ops.export_scene.fbx(
        filepath=str(OUTPUT_FBX),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True,
        add_leaf_bones=False,
        bake_anim=False,
        mesh_smooth_type="FACE",
    )
    report = {
        "schemaVersion": 1,
        "iteration": "v440",
        "status": "draft-rigid-hip-belt-attachment-reweight",
        "source": {"path": str(SOURCE), "sha256": sha256(SOURCE)},
        "output": {"path": str(OUTPUT_FBX), "sha256": sha256(OUTPUT_FBX)},
        "mesh": mesh_object.name,
        "materialIndex": belt_index,
        "materialName": "ch0100_40_NeoBelt",
        "selectionRule": "connected NeoBelt components with reference maximum Z below 60 cm",
        "selectedComponentCount": len(selected_components),
        "selectedVertexCount": len(selected_vertices),
        "selectedComponents": selected_components,
        "removedInfluences": "all prior hip/thigh/twist/muscle influences on selected vertices",
        "replacementInfluence": {"bone": "Hip", "weight": 1.0},
        "expectedResult": "waist weapons retain their hanging bind orientation instead of following thigh rotation into a rigid horizontal pose",
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


main()
