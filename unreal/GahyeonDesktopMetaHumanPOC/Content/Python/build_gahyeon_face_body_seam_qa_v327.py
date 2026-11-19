"""Build a persistent face/body seam comparison for original and v310 bodies."""

import json
from pathlib import Path

import unreal


FACE = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Face/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_FaceMesh"
)
ORIGINAL_BODY = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
RECOMPUTED_BODY = (
    "/Game/Gahyeon/CharacterPipeline/v310/Body/"
    "SKM_Gahyeon_Body_RecomputedNormals_v310"
)
MAP = "/Game/Gahyeon/CharacterPipeline/v327/QA/L_GahyeonFaceBodySeam_v327"
SEQUENCE_ROOT = "/Game/Gahyeon/CharacterPipeline/v328/Sequence"
SEQUENCE_NAME = "LS_GahyeonFaceBodySeam_v328"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v327-gahyeon-face-body-seam-build/report.json"
)


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def spawn_mesh(actors, label, mesh, location):
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, location)
    if actor is None:
        raise RuntimeError(f"failed to spawn {label}")
    actor.set_actor_label(label)
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)
    return actor, component


def add_rect_light(actors, label, location, target, intensity):
    actor = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if actor is None:
        raise RuntimeError(f"failed to spawn {label}")
    actor.set_actor_label(label)
    component = actor.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 90.0)
    component.set_editor_property("source_height", 100.0)


def build_gahyeon_face_body_seam_qa_v327():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    face_asset = require_asset(FACE)
    original_body = require_asset(ORIGINAL_BODY)
    recomputed_body = require_asset(RECOMPUTED_BODY)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create face/body seam map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    groups = []
    for prefix, body_asset, x in (
        ("Original", original_body, -38.0),
        ("Recomputed", recomputed_body, 38.0),
    ):
        location = unreal.Vector(x, 0.0, 0.0)
        face_actor, face_component = spawn_mesh(
            actors, f"Gahyeon_{prefix}_Face_v327", face_asset, location
        )
        body_actor, body_component = spawn_mesh(
            actors, f"Gahyeon_{prefix}_Body_v327", body_asset, location
        )
        groups.append((prefix, face_actor, face_component, body_actor, body_component))
    face_bounds = [face_actor.get_actor_bounds(False, True) for _, face_actor, _, _, _ in groups]
    face_heights = [extent.z * 2.0 for _, extent in face_bounds]
    if any(height < 15.0 or height > 80.0 for height in face_heights):
        raise RuntimeError(f"unexpected face heights: {face_heights}")
    face_center_z = sum(origin.z for origin, _ in face_bounds) / len(face_bounds)
    target = unreal.Vector(0.0, 0.0, face_center_z - 3.0)
    camera_location = target + unreal.Vector(0.0, 300.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    if camera is None:
        raise RuntimeError("failed to spawn seam camera")
    camera.set_actor_label("CAM_GahyeonFaceBodySeam_v327")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 85.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_rect_light(
        actors, "KEY_GahyeonSeam_v327", target + unreal.Vector(-100, 150, 60), target, 4200.0
    )
    add_rect_light(
        actors, "FILL_GahyeonSeam_v327", target + unreal.Vector(110, 140, 20), target, 2600.0
    )
    add_rect_light(
        actors, "RIM_GahyeonSeam_v327", target + unreal.Vector(0, -100, 45), target, 2800.0
    )
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.8)
    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 0.0)
    settings.set_editor_property("override_motion_blur_amount", True)
    settings.set_editor_property("motion_blur_amount", 0.0)
    post.set_editor_property("settings", settings)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("failed to save face/body seam map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create face/body seam sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(5)
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to open seam sequence")
    camera_binding = unreal.get_editor_subsystem(
        unreal.LevelSequenceEditorSubsystem
    ).add_actors([camera])[0]
    camera_cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    camera_cut.set_range(0, 5)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    camera_cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save seam sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v327", "v328"],
        "status": "draft-persistent-seam-comparison-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "face": FACE,
        "originalBody": ORIGINAL_BODY,
        "recomputedBody": RECOMPUTED_BODY,
        "faceHeightsCm": face_heights,
        "cameraTargetZ": face_center_z - 3.0,
        "hypothesis": (
            "Persistent Face+Body pairs reveal whether v310 body normals change the "
            "visible neck seam under identical face, material, camera, and lighting."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V327_SEAM=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_face_body_seam_qa_v327()
