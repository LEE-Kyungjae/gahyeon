"""Inspect UE 5.8 MetaHuman preset keypoints without conforming a character."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v212-metahuman-keypoint-preflight.json"
)
CHARACTER_PATH = "/Game/Gahyeon/CharacterPipeline/v212/Diagnostics/MHC_KeypointProbe_v212"
TARGET_MESH_PATH = "/Game/Gahyeon/CharacterPipeline/v194/Input/SM_Gahyeon_KeenTools_Cm_v194"

if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(CHARACTER_PATH):
    raise RuntimeError("refusing to overwrite immutable v212 keypoint preflight")

subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
package, asset_name = CHARACTER_PATH.rsplit("/", 1)
character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    asset_name=asset_name,
    package_path=package,
    asset_class=unreal.MetaHumanCharacter,
    factory=unreal.new_object(type=unreal.MetaHumanCharacterFactoryNew),
)
if character is None or not subsystem.try_add_object_to_edit(character):
    if character is not None:
        unreal.EditorAssetLibrary.delete_asset(CHARACTER_PATH)
    raise RuntimeError("failed to create v212 keypoint probe")

try:
    transient = {}
    for mesh in unreal.ObjectIterator(unreal.SkeletalMesh):
        path = mesh.get_path_name()
        if "MetaHumanCharacterEditorSubsystem" not in path:
            continue
        if mesh.get_name().startswith("FaceMesh"):
            transient["face"] = mesh
        elif mesh.get_name().startswith("BodyMesh"):
            transient["body"] = mesh
    if set(transient) != {"face", "body"}:
        raise RuntimeError(f"missing transient template meshes: {transient}")

    result = subsystem.get_mesh_for_body_conforming_from_template(
        character,
        transient["body"],
        transient["face"],
        match_vertices_by_u_vs=False,
    )
    if not isinstance(result, tuple) or len(result) != 2:
        raise RuntimeError(f"unexpected template extraction result: {type(result)} {result}")
    status, template_vertices = result
    presets = subsystem.get_preset_body_key_points(character)
    target_mesh = unreal.load_asset(TARGET_MESH_PATH)
    target_vertices, target_indices, *_ = subsystem.get_mesh_data_for_conforming(target_mesh)
    records = []
    for name, index in sorted(presets.items(), key=lambda item: str(item[0])):
        if 0 <= index < len(template_vertices):
            vertex = template_vertices[index]
            records.append({
                "name": str(name),
                "index": index,
                "position": [vertex.x, vertex.y, vertex.z],
            })
    payload = {
        "schemaVersion": 1,
        "iteration": "v212",
        "state": "metahuman-preset-keypoints-inspected",
        "templateExtractionStatus": str(status),
        "templateVertexCount": len(template_vertices),
        "presetCount": len(presets),
        "resolvedPresetCount": len(records),
        "presets": records,
        "targetVertexCount": len(target_vertices),
        "targetTriangleCount": len(target_indices) // 3,
        "claims": {"conformed": False, "identityApproved": False},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    unreal.log(json.dumps(payload))
finally:
    if subsystem.is_object_added_for_editing(character):
        subsystem.remove_object_to_edit(character)
    unreal.EditorAssetLibrary.delete_asset(CHARACTER_PATH)

unreal.SystemLibrary.quit_editor()
