"""Render readable fixed-camera clay evidence for the v178 Cloud head."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np


VIEWS = {
    "face-front": "face-neutral-front",
    "face-left-45": "face-neutral-three-quarter-left",
    "face-right-45": "face-neutral-three-quarter-right",
    "face-left-profile": "face-neutral-left-profile",
    "face-right-profile": "face-neutral-right-profile",
}


def digest_clay_v178(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material_v178(name: str, color: tuple[float, float, float, float], roughness: float):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = 0.0
    return material


def create_clay_material_v178() -> list:
    return [
        material_v178("M_v178_SkinClay", (0.55, 0.27, 0.19, 1.0), 0.58),
        material_v178("M_v178_EyeLeft", (0.72, 0.74, 0.76, 1.0), 0.34),
        material_v178("M_v178_EyeRight", (0.72, 0.74, 0.76, 1.0), 0.34),
        material_v178("M_v178_TeethClay", (0.68, 0.66, 0.62, 1.0), 0.45),
    ]


def render_identity_clay_v178() -> dict:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(values)
    output = args.output_dir.resolve()
    if output.exists():
        raise RuntimeError(f"refusing to overwrite immutable clay renders: {output}")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1 or len(meshes[0].data.materials) != 4:
        raise RuntimeError("v178 four-primitive head mesh contract differs")
    original_materials = [material.name if material else None
                          for material in meshes[0].data.materials]
    replacements = create_clay_material_v178()
    for index, material in enumerate(replacements):
        meshes[0].data.materials[index] = material

    scene = bpy.context.scene
    # Workbench is deliberate here: the Cloud GLB's imported normals/material
    # stack should not be allowed to hide the reconstruction geometry during
    # the identity gate.  Studio light + cavity gives a stable, fast clay pass.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.4
    scene.display.shading.curvature_valley_factor = 1.1
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 2560
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.35
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.16, 0.17, 0.19, 1.0)
    background.inputs["Strength"].default_value = 0.5
    for light in (obj for obj in scene.objects if obj.type == "LIGHT"):
        light.data.energy *= 1.35

    output.mkdir(parents=True, exist_ok=False)
    records = []
    for label, evidence_view in VIEWS.items():
        cameras = [obj for obj in scene.objects
                   if obj.type == "CAMERA" and obj.get("evidence_view") == evidence_view]
        if len(cameras) != 1:
            raise RuntimeError(f"expected one sealed camera for {evidence_view}")
        scene.camera = cameras[0]
        path = output / f"{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        mean_channel = float(pixels.reshape((-1, 4))[::16, :3].mean())
        bpy.data.images.remove(image)
        if mean_channel < 0.12:
            raise RuntimeError(f"unreadable underlit clay render: {label}={mean_channel}")
        records.append({
            "view": label,
            "evidenceView": evidence_view,
            "uri": path.name,
            "bytes": path.stat().st_size,
            "sha256": digest_clay_v178(path),
            "meanRgbChannel": round(mean_channel, 6),
        })
    payload = {
        "schemaVersion": 1,
        "iteration": "v178",
        "renderer": "identity-clay-v178",
        "sourceBlend": bpy.data.filepath,
        "resolution": [1440, 2560],
        "displayProfile": "looking-glass-go-single-view",
        "materialOverride": {
            "temporary": True,
            "originalMaterials": original_materials,
            "replacementMaterials": [material.name for material in replacements],
        },
        "views": records,
        "identityApproved": False,
        "automaticApproval": False,
    }
    (output / "render-manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "iteration": "v178",
        "views": len(records),
        "meanRgbRange": [min(item["meanRgbChannel"] for item in records),
                         max(item["meanRgbChannel"] for item in records)],
    }))
    return payload


if __name__ == "__main__":
    try:
        render_identity_clay_v178()
    except RuntimeError as error:
        raise SystemExit(f"ERROR: {error}")
