"""Build a persistent side-by-side QA map for original and recomputed Gahyeon bodies."""

import json
from pathlib import Path

import unreal


ORIGINAL = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
RECOMPUTED = (
    "/Game/Gahyeon/CharacterPipeline/v310/Body/"
    "SKM_Gahyeon_Body_RecomputedNormals_v310"
)
MAP = "/Game/Gahyeon/CharacterPipeline/v323/QA/L_GahyeonBodyNormalsCompare_v323"
SEQUENCE_ROOT = "/Game/Gahyeon/CharacterPipeline/v324/Sequence"
SEQUENCE_NAME = "LS_GahyeonBodyNormalsCompare_v324"
SEQUENCE = f"{SEQUENCE_ROOT}/{SEQUENCE_NAME}"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v323-gahyeon-body-comparison-build/report.json"
)


def require_asset(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return asset


def add_rect_light(actors, label, location, target, intensity):
    light = actors.spawn_actor_from_class(
        unreal.RectLight,
        location,
        unreal.MathLibrary.find_look_at_rotation(location, target),
    )
    if light is None:
        raise RuntimeError(f"failed to spawn {label}")
    light.set_actor_label(label)
    component = light.get_component_by_class(unreal.RectLightComponent)
    component.set_editor_property("intensity", intensity)
    component.set_editor_property("source_width", 100.0)
    component.set_editor_property("source_height", 100.0)


def build_gahyeon_body_comparison_qa_v323():
    for path in (MAP, SEQUENCE):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            raise RuntimeError(f"refusing to overwrite immutable asset: {path}")
    original = require_asset(ORIGINAL)
    recomputed = require_asset(RECOMPUTED)
    if not unreal.EditorLevelLibrary.new_level(MAP):
        raise RuntimeError("failed to create body comparison map")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    bodies = []
    for label, mesh, x in (
        ("Gahyeon_OriginalBody_v323", original, -55.0),
        ("Gahyeon_RecomputedBody_v323", recomputed, 55.0),
    ):
        actor = actors.spawn_actor_from_class(
            unreal.SkeletalMeshActor, unreal.Vector(x, 0.0, 0.0)
        )
        if actor is None:
            raise RuntimeError(f"failed to spawn {label}")
        actor.set_actor_label(label)
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        bodies.append((actor, component))
    origins_extents = [actor.get_actor_bounds(False, True) for actor, _ in bodies]
    heights = [extent.z * 2.0 for _, extent in origins_extents]
    if any(height < 120.0 or height > 220.0 for height in heights):
        raise RuntimeError(f"unexpected body heights: {heights}")
    average_origin_z = sum(origin.z for origin, _ in origins_extents) / 2.0
    average_extent_z = sum(extent.z for _, extent in origins_extents) / 2.0
    target = unreal.Vector(0.0, 0.0, average_origin_z + average_extent_z * 0.55)
    camera_location = target + unreal.Vector(0.0, 390.0, 0.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, target),
    )
    if camera is None:
        raise RuntimeError("failed to spawn comparison camera")
    camera.set_actor_label("CAM_GahyeonBodyNormalsCompare_v323")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 70.0)
    camera.camera_component.set_editor_property("current_aperture", 8.0)
    add_rect_light(
        actors, "KEY_GahyeonBodyCompare_v323", target + unreal.Vector(-130, 180, 70), target, 4800.0
    )
    add_rect_light(
        actors, "FILL_GahyeonBodyCompare_v323", target + unreal.Vector(130, 160, 30), target, 2600.0
    )
    add_rect_light(
        actors, "RIM_GahyeonBodyCompare_v323", target + unreal.Vector(0, -120, 60), target, 3200.0
    )
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 0.7)
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
        raise RuntimeError("failed to save body comparison map")
    sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        SEQUENCE_NAME, SEQUENCE_ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    if sequence is None:
        raise RuntimeError("failed to create comparison sequence")
    sequence.set_display_rate(unreal.FrameRate(30, 1))
    sequence.set_tick_resolution(unreal.FrameRate(24000, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(5)
    if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to open comparison sequence")
    sequencer = unreal.get_editor_subsystem(unreal.LevelSequenceEditorSubsystem)
    camera_binding = sequencer.add_actors([camera])[0]
    camera_cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    camera_cut.set_range(0, 5)
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", camera_binding.get_id())
    camera_cut.set_camera_binding_id(binding_id)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save comparison sequence")
    report = {
        "schemaVersion": 1,
        "iterations": ["v323", "v324"],
        "status": "draft-persistent-body-comparison-ready",
        "map": MAP,
        "sequence": SEQUENCE,
        "actors": [
            {"label": bodies[0][0].get_actor_label(), "mesh": ORIGINAL},
            {"label": bodies[1][0].get_actor_label(), "mesh": RECOMPUTED},
        ],
        "heightsCm": heights,
        "hypothesis": (
            "A persistent-map side-by-side render avoids spawnable override loss and "
            "reveals whether coherent normal recomputation changes the neck shading."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V323_COMPARE=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_body_comparison_qa_v323()
