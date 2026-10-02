"""Create a lightweight fixed-camera desktop preview level for assembled v024."""

import unreal


MAP_PATH = "/Game/Gahyeon/CharacterPipeline/v027/Preview/L_Skotukeda_Medium_v027"
BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/"
    "Skotukeda_Medium_v027/BP_Skotukeda_Medium_v027"
)


def create_preview_level_v024():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        raise RuntimeError(f"refusing to overwrite existing preview level: {MAP_PATH}")
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"assembled MetaHuman Blueprint is unavailable: {BLUEPRINT_PATH}")
    if not unreal.EditorLevelLibrary.new_level(MAP_PATH):
        raise RuntimeError(f"failed to create preview level: {MAP_PATH}")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(
        blueprint.generated_class(), unreal.Vector(0.0, 0.0, 0.0)
    )
    if character is None:
        raise RuntimeError("failed to spawn assembled MetaHuman Blueprint")
    character.set_actor_label("Skotukeda_Medium_v027")

    camera_location = unreal.Vector(0.0, 360.0, 150.0)
    camera_target = unreal.Vector(0.0, 0.0, 145.0)
    camera = actors.spawn_actor_from_class(
        unreal.CineCameraActor,
        camera_location,
        unreal.MathLibrary.find_look_at_rotation(camera_location, camera_target),
    )
    camera.set_actor_label("CAM_Gahyeon_Desktop_v025b")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("current_focal_length", 50.0)
    camera.camera_component.set_editor_property("current_aperture", 5.6)

    key = actors.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 220.0),
        unreal.Rotator(-32.0, -38.0, 0.0),
    )
    key.set_actor_label("KEY_Gahyeon_v025b")
    key.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property(
        "intensity", 0.0
    )

    fill = actors.spawn_actor_from_class(
        unreal.RectLight,
        unreal.Vector(110.0, 260.0, 185.0),
        unreal.MathLibrary.find_look_at_rotation(
            unreal.Vector(110.0, 260.0, 185.0), camera_target
        ),
    )
    fill.set_actor_label("FILL_Gahyeon_v025b")
    fill_component = fill.get_component_by_class(unreal.RectLightComponent)
    fill_component.set_editor_property("intensity", 5000.0)
    fill_component.set_editor_property("source_width", 120.0)
    fill_component.set_editor_property("source_height", 120.0)

    rim = actors.spawn_actor_from_class(
        unreal.RectLight,
        unreal.Vector(-130.0, 240.0, 180.0),
        unreal.MathLibrary.find_look_at_rotation(
            unreal.Vector(-130.0, 240.0, 180.0), camera_target
        ),
    )
    rim.set_actor_label("RIM_Gahyeon_v025b")
    rim_component = rim.get_component_by_class(unreal.RectLightComponent)
    rim_component.set_editor_property("intensity", 3500.0)
    rim_component.set_editor_property("source_width", 80.0)
    rim_component.set_editor_property("source_height", 100.0)

    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector())
    sky.set_actor_label("SKY_Gahyeon_v025b")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property(
        "intensity", 0.5
    )

    post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    post.set_actor_label("PPV_Gahyeon_v025b")
    post.set_editor_property("unbound", True)
    settings = post.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property(
        "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL
    )
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", 4.0)
    post.set_editor_property("settings", settings)

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError(f"failed to save preview level: {MAP_PATH}")
    unreal.log(f"Gahyeon desktop preview level saved: {MAP_PATH}")


create_preview_level_v024()
