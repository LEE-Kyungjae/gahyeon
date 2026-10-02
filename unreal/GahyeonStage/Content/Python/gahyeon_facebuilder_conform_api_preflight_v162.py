"""Fail-closed UE 5.8 API preflight for the v161 MetaHuman conform runner."""

import json
from pathlib import Path
import traceback

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v162-ue58-facebuilder-conform-api-preflight/preflight.json"
)


def require_callable_v162(owner, name):
    value = getattr(owner, name, None)
    if not callable(value):
        raise RuntimeError(f"required UE 5.8 callable is unavailable: {name}")
    return name


def run_facebuilder_conform_api_preflight_v162():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable preflight: {OUTPUT}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if subsystem is None:
        raise RuntimeError("MetaHumanCharacterEditorSubsystem is unavailable")
    required_subsystem_calls = [
        require_callable_v162(subsystem, name)
        for name in (
            "track_face_landmarks_from_image",
            "get_mesh_data_for_conforming",
            "conform_to_target_meshes",
            "commit_posed_state_as_a_pose",
            "try_add_object_to_edit",
            "is_object_added_for_editing",
            "remove_object_to_edit",
        )
    ]
    required_editor_calls = [
        require_callable_v162(unreal.AutomationLibrary, "take_high_res_screenshot"),
        require_callable_v162(unreal.PromotedFrameUtils, "get_promoted_frame_as_pixel_array_from_disk"),
        require_callable_v162(unreal.AssetToolsHelpers.get_asset_tools(), "import_asset_tasks"),
    ]

    conform = unreal.ConformTargetParams()
    conform.conform_target_mesh.target_parts_type = unreal.TargetPartsType.HEAD_ONLY
    conform.auto_solve = True
    view = unreal.MinimalViewInfo()
    view.location = unreal.Vector(1.0, 2.0, 3.0)
    view.rotation = unreal.Rotator(0.0, 90.0, 0.0)
    view.fov = 35.0
    view.aspect_ratio = 1.0
    view.projection_mode = unreal.CameraProjectionMode.PERSPECTIVE
    conform.camera_view_info = view
    conform.image_size = unreal.IntPoint(1200, 1200)
    target_key = unreal.MetaHumanCharacterTargetMeshKey()

    task = unreal.AssetImportTask()
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.convert_scene = True
    options.static_mesh_import_data.convert_scene_unit = True
    task.options = options

    payload = {
        "schemaVersion": 1,
        "iteration": "v162",
        "state": "ue58-facebuilder-conform-api-compatible",
        "engineVersion": unreal.SystemLibrary.get_engine_version(),
        "requiredSubsystemCalls": required_subsystem_calls,
        "requiredEditorCalls": required_editor_calls,
        "constructedTypes": [
            type(conform).__name__,
            type(view).__name__,
            type(target_key).__name__,
            type(task).__name__,
            type(options).__name__,
        ],
        "targetPartsType": "HEAD_ONLY",
        "productionReady": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(json.dumps(payload))
    unreal.SystemLibrary.quit_editor()


try:
    run_facebuilder_conform_api_preflight_v162()
except Exception:
    unreal.log_error(traceback.format_exc())
    unreal.SystemLibrary.quit_editor()
    raise
