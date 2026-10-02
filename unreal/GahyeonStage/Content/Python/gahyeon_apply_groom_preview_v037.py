"""Attach an engine MetaHuman groom and tune exposure for the v037 runtime POC."""

import unreal


GROOM_PATH = (
    "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/"
    "Hair_L_StraightBangs/Hair_L_StraightBangs"
)
POST_LABEL = "PPV_Gahyeon_v025b"

groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
if groom is None:
    raise RuntimeError(f"MetaHuman groom is unavailable: {GROOM_PATH}")

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level_actors = actors.get_all_level_actors()
hair_components = []
for actor in level_actors:
    for component in actor.get_components_by_class(unreal.GroomComponent):
        if component.get_name() == "Hair":
            hair_components.append(component)
if len(hair_components) != 1:
    raise RuntimeError(f"expected one Hair groom component, got {len(hair_components)}")

hair = hair_components[0]
hair.set_editor_property("groom_asset", groom)
hair.set_editor_property("visible", True)

post = next((a for a in level_actors if a.get_actor_label() == POST_LABEL), None)
if post is None:
    raise RuntimeError(f"post-process volume is unavailable: {POST_LABEL}")
settings = post.get_editor_property("settings")
settings.set_editor_property("override_auto_exposure_bias", True)
settings.set_editor_property("auto_exposure_bias", 2.0)
post.set_editor_property("settings", settings)

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v037 groom POC")
unreal.log(f"Gahyeon v037 groom POC saved: groom={GROOM_PATH}, exposure=2.0")
