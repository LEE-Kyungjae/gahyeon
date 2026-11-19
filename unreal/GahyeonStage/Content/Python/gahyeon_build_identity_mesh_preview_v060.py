"""Build a fixed-light geometry preview of the v060 conformed Identity mesh."""

import unreal


TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v060/Preview/L_Gahyeon_IdentityMeshNeutral_v060d"
MESH = "/Game/Gahyeon/CharacterPipeline/v060/Identity/SK_MHI_Gahyeon_HeadOnly_v060"
NEUTRAL_MATERIAL = "/Engine/EngineMaterials/DefaultMaterial"


def build_identity_mesh_preview_v060():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError(f"refusing to overwrite v060 preview: {TARGET_MAP}")
    mesh = unreal.EditorAssetLibrary.load_asset(MESH)
    if mesh is None or mesh.get_class().get_name() != "SkeletalMesh":
        raise RuntimeError(f"v060 conformed Identity mesh is unavailable: {MESH}")
    if not unreal.EditorLevelLibrary.new_level(TARGET_MAP):
        raise RuntimeError(f"failed to create empty v060 geometry map: {TARGET_MAP}")
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world is None:
        raise RuntimeError("empty v060 geometry world is unavailable")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    preview = actors.spawn_actor_from_class(
        unreal.SkeletalMeshActor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator()
    )
    if preview is None:
        raise RuntimeError("failed to spawn v060 Identity mesh preview")
    preview.set_actor_label("Gahyeon_IdentityMesh_v060")
    preview.skeletal_mesh_component.set_editor_property("skeletal_mesh_asset", mesh)
    neutral = unreal.EditorAssetLibrary.load_asset(NEUTRAL_MATERIAL)
    if neutral is None:
        raise RuntimeError(f"neutral QA material is unavailable: {NEUTRAL_MATERIAL}")
    for index in range(len(mesh.materials)):
        preview.skeletal_mesh_component.set_material(index, neutral)
    key = actors.spawn_actor_from_class(
        unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 250.0), unreal.Rotator(-35.0, -35.0, 0.0)
    )
    key.set_actor_label("KEY_Gahyeon_IdentityMesh_v060c")
    key.light_component.set_editor_property("intensity", 4.0)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(), unreal.Rotator())
    sky.set_actor_label("SKY_Gahyeon_IdentityMesh_v060c")
    sky.light_component.set_editor_property("intensity", 1.0)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v060 Identity preview: {TARGET_MAP}")
    unreal.log(f"Gahyeon v060 Identity geometry preview saved: {TARGET_MAP}")


build_identity_mesh_preview_v060()
